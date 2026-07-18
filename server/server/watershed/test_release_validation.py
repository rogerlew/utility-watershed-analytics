import hashlib
import json
import os
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pyarrow as arrow
import pyarrow.parquet as parquet
from django.test import TestCase

from server.watershed.fingerprint_contract import canonical_bytes
from server.watershed.materializer import CapabilityDeclaration
from server.watershed.models import (
    ActiveDataRelease,
    DataArtifactLineage,
    DataReleaseAttempt,
    RunCapability,
    Subcatchment,
    Watershed,
)
from server.watershed.release_validation import (
    ReleaseValidationError,
    ValidationCheck,
    compute_serving_fingerprints,
    validated_empty_build,
    validation_report,
    write_validation_report,
)
from server.watershed.test_materializer import MaterializerFixtureMixin
from server.watershed.test_runtime_capabilities import rhessys_configuration


def digest_bytes(content):
    return hashlib.sha256(content).hexdigest()


class ArtifactResponse:
    def __init__(self, content):
        self.content = content
        self.status_code = 200

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        del chunk_size
        yield self.content

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class CleanBuildValidationTests(MaterializerFixtureMixin, TestCase):
    def _rewrite_lineage(self, member, role, content):
        path = member.artifact_paths[role]
        path.write_bytes(content)
        DataArtifactLineage.objects.filter(
            run_state=member.run_state,
            role=role,
        ).update(
            sha256=digest_bytes(content),
            byte_size=len(content),
        )

    def _reviewed_boundary(self, member):
        document = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[0, 0], [5, 0], [5, 1], [0, 1], [0, 0]]
                        ],
                    },
                }
            ],
        }
        self._rewrite_lineage(
            member,
            "boundary",
            json.dumps(document, sort_keys=True, separators=(",", ":")).encode(),
        )

    def _rhessys_member(self, member):
        declaration = member.capability
        base_uri = declaration.durable_base_uri
        index_lineage = DataArtifactLineage.objects.get(
            run_state=member.run_state,
            role=declaration.index_role,
        )
        sink = arrow.BufferOutputStream()
        parquet.write_table(
            arrow.table(
                {
                    "year": [2000, 2000],
                    "flow": [2.0, 4.0],
                    "hillID": [1, 2],
                }
            ),
            sink,
        )
        query_content = sink.getvalue().to_pybytes()
        configuration = rhessys_configuration(
            base_uri,
            index_lineage.uri,
            index_lineage.sha256,
        )
        hillslope = next(
            item for item in configuration["parquets"] if item["role"] == "hillslope"
        )
        hillslope["artifact"] = {
            "uri": f"{base_uri}hillslope.parquet",
            "sha256": digest_bytes(query_content),
            "bytes": len(query_content),
            "media_type": "application/vnd.apache.parquet",
            "verified": True,
        }
        capability = CapabilityDeclaration(
            capability_type=RunCapability.CapabilityType.RHESSYS,
            mode=RunCapability.Mode.DYNAMIC,
            durable_base_uri=base_uri,
            index_role=declaration.index_role,
            runtime_configuration=configuration,
        )
        return replace(member, capability=capability), {
            hillslope["artifact"]["uri"]: query_content
        }

    def _validated_fixture(self):
        release, members = self._release(runid_format="{source}-run-{index}")
        for member in members:
            self._reviewed_boundary(member)
        members[1], remote_artifacts = self._rhessys_member(members[1])
        return release, members, remote_artifacts

    def _run_build(self):
        release, members, remote_artifacts = self._validated_fixture()
        attempt = self._attempt(release)
        budget = self._budget(members)

        def fetch(uri, **_kwargs):
            if uri not in remote_artifacts:
                raise AssertionError(f"unexpected artifact fetch: {uri}")
            return ArtifactResponse(remote_artifacts[uri])

        probe = {
            "runid": members[1].run_state.runid,
            "request": {
                "kind": "choropleth",
                "scenario": "S1",
                "variable": "flow",
                "spatial_scale": "hillslope",
                "year": 2000,
            },
            "expected_rows": [
                {"spatialId": 1, "value": 2.0},
                {"spatialId": 2, "value": 4.0},
            ],
        }
        with patch(
            "server.watershed.runtime_capabilities.requests.get",
            side_effect=fetch,
        ):
            result = validated_empty_build(
                attempt,
                members,
                budget=budget,
                observed_available_bytes=budget.required_bytes,
                actual_plan_sha256=attempt.reviewed_plan_sha256,
                validator_git_commit="1" * 40,
                validator_image_digest=f"sha256:{'2' * 64}",
                reviewed_bounds={member.run_state.runid: (0, 0, 5, 1) for member in members},
                removed_runids=("removed-run",),
                rhessys_probe=probe,
                batch_size=1,
            )
        return release, attempt, result

    def test_clean_build_acceptance(self):
        release, attempt, result = self._run_build()
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, DataReleaseAttempt.Status.SUCCEEDED)
        self.assertEqual(
            ActiveDataRelease.objects.get(singleton_id=1).release,
            release,
        )
        self.assertEqual(result.report["status"], "passed")
        self.assertEqual(len(result.fingerprints.domain), 64)
        self.assertEqual(len(result.fingerprints.capabilities), 64)
        self.assertEqual(result.fingerprints.as_document()["counts"], {
            "watersheds": 2,
            "subcatchments": 4,
            "channels": 2,
            "capabilities": 1,
        })
        report_path = os.environ.get("DB21_REPORT_PATH")
        if report_path:
            Path(report_path).write_bytes(
                canonical_bytes(result.fingerprints.as_document())
            )

    def test_serving_fingerprint_is_stable_and_semantic(self):
        release, _, result = self._run_build()
        repeated = compute_serving_fingerprints(release)
        self.assertEqual(repeated, result.fingerprints)
        child = Subcatchment.objects.order_by("watershed_id", "topazid").first()
        child.slope_scalar = 0.3
        child.save(update_fields=("slope_scalar",))
        changed = compute_serving_fingerprints(release)
        self.assertNotEqual(changed.domain, repeated.domain)
        self.assertEqual(changed.capabilities, repeated.capabilities)

    def test_html_artifact_fails_before_staging_or_acceptance(self):
        release, members = self._release()
        self._rewrite_lineage(
            members[0],
            "metadata",
            b"<!doctype html><html><body>upstream error</body></html>",
        )
        attempt = self._attempt(release)
        budget = self._budget(members)
        with self.assertRaisesRegex(ReleaseValidationError, "HTML response"):
            validated_empty_build(
                attempt,
                members,
                budget=budget,
                observed_available_bytes=budget.required_bytes,
                actual_plan_sha256=attempt.reviewed_plan_sha256,
                validator_git_commit="1" * 40,
                validator_image_digest=f"sha256:{'2' * 64}",
            )
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, DataReleaseAttempt.Status.FAILED)
        self.assertFalse(hasattr(attempt, "staging_state"))
        self.assertEqual(Watershed.objects.count(), 0)

    def test_credential_bearing_artifact_uri_fails_before_staging(self):
        release, members = self._release()
        DataArtifactLineage.objects.filter(
            run_state=members[0].run_state,
            role="metadata",
        ).update(
            uri="https://user:password@artifacts.example.test/metadata.json"
        )
        attempt = self._attempt(release)
        budget = self._budget(members)
        with self.assertRaisesRegex(ReleaseValidationError, "credential-free"):
            validated_empty_build(
                attempt,
                members,
                budget=budget,
                observed_available_bytes=budget.required_bytes,
                actual_plan_sha256=attempt.reviewed_plan_sha256,
                validator_git_commit="1" * 40,
                validator_image_digest=f"sha256:{'2' * 64}",
            )
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, DataReleaseAttempt.Status.FAILED)
        self.assertEqual(Watershed.objects.count(), 0)

    def test_uncovered_geometry_fails_before_activation(self):
        release, members, _ = self._validated_fixture()
        document = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"TopazID": 1, "WeppID": 101},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[20, 0], [21, 0], [21, 1], [20, 1], [20, 0]]
                        ],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {"TopazID": 2, "WeppID": 102},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[2, 0], [2.8, 0], [2.8, 0.8], [2, 0.8], [2, 0]]
                        ],
                    },
                },
            ],
        }
        self._rewrite_lineage(
            members[0],
            "subcatchments",
            json.dumps(document, sort_keys=True, separators=(",", ":")).encode(),
        )
        attempt = self._attempt(release)
        budget = self._budget(members)
        with self.assertRaisesRegex(ReleaseValidationError, "uncovered"):
            validated_empty_build(
                attempt,
                members,
                budget=budget,
                observed_available_bytes=budget.required_bytes,
                actual_plan_sha256=attempt.reviewed_plan_sha256,
                validator_git_commit="1" * 40,
                validator_image_digest=f"sha256:{'2' * 64}",
                reviewed_bounds={member.run_state.runid: (0, 0, 5, 1) for member in members},
                batch_size=1,
            )
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, DataReleaseAttempt.Status.FAILED)
        self.assertEqual(
            ActiveDataRelease.objects.get(singleton_id=1).state,
            ActiveDataRelease.State.EMPTY,
        )
        self.assertEqual(Watershed.objects.count(), 0)

    def test_report_is_sanitized_canonical_and_write_once(self):
        report = validation_report(
            report_id="db21-report",
            subject_type="release",
            subject_id="2026-07-18.21",
            validator_git_commit="1" * 40,
            validator_image_digest=f"sha256:{'2' * 64}",
            checks=(ValidationCheck("synthetic-check"),),
            started_at=datetime.now(timezone.utc),
            summary="password=not-safe https://user:pass@example.test/path",
        )
        self.assertNotIn("not-safe", report["summary"])
        self.assertNotIn("user:pass", report["summary"])
        output = self.root / "report.json"
        first_digest = write_validation_report(output, report)
        self.assertEqual(first_digest, digest_bytes(output.read_bytes()))
        with self.assertRaisesRegex(ReleaseValidationError, "already exists"):
            write_validation_report(output, report)
