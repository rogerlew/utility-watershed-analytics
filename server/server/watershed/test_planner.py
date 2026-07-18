import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.gis.geos import MultiPolygon, Polygon
from django.core.management import call_command
from django.test import TestCase

from server.watershed.fingerprint_contract import canonical_sha256
from server.watershed.models import (
    ActiveDataRelease,
    Channel,
    DataRelease,
    DataRunState,
    Subcatchment,
    Watershed,
    WatershedCollection,
    WatershedIdentity,
    WatershedRunAlias,
)
from server.watershed.planner import (
    PlanningError,
    plan_bytes,
    plan_empty_build,
    plan_exact_inverse,
    plan_forward,
)
from server.watershed.release_validation import compute_serving_fingerprints


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def geometry(offset):
    polygon = Polygon(
        (
            (offset, 0),
            (offset + 1, 0),
            (offset + 1, 1),
            (offset, 1),
            (offset, 0),
        ),
        srid=4326,
    )
    return MultiPolygon(polygon, srid=4326)


def load_plan_contract():
    for root in Path(__file__).resolve().parents:
        script_path = root / "scripts" / "validate_fingerprint_plan_contract.py"
        if script_path.exists():
            sys.path.insert(0, str(script_path.parent))
            spec = importlib.util.spec_from_file_location("db09_plan_contract", script_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    return None


class BaseAwarePlannerTests(TestCase):
    migration = "watershed.0011_capability_runtime_types"

    def release(self, release_id, suffix, *, materializer="shared", migration=None):
        return DataRelease.objects.create(
            release_id=release_id,
            manifest_sha256=digest(f"manifest-{suffix}"),
            release_fingerprint=digest(f"release-{suffix}"),
            domain_fingerprint=digest(f"domain-{suffix}"),
            supported_migration=migration or self.migration,
            materializer_image_digest=f"sha256:{digest(f'image-{materializer}')}",
            materializer_git_commit=digest(f"git-{materializer}")[:40],
            expected_watersheds=0,
            expected_subcatchments=0,
            expected_channels=0,
            actual_watersheds=0,
            actual_subcatchments=0,
            actual_channels=0,
            validation_summary={"synthetic": True},
            created_at=datetime.now(timezone.utc),
        )

    def identity(self, key, collection_key="collection"):
        collection, _ = WatershedCollection.objects.get_or_create(key=collection_key)
        identity, _ = WatershedIdentity.objects.get_or_create(
            watershed_key=key,
            defaults={"collection": collection},
        )
        return identity

    def run_state(
        self,
        release,
        key,
        runid,
        *,
        metadata="same",
        geometry_value="same",
        children="same",
        capability=None,
        subcatchments=1,
        collection_key="collection",
    ):
        identity = self.identity(key, collection_key)
        return DataRunState.objects.create(
            release=release,
            collection=identity.collection,
            watershed_identity=identity,
            runid=runid,
            run_fingerprint=digest(
                f"{runid}:{metadata}:{geometry_value}:{children}:{capability}"
            ),
            metadata_fingerprint=digest(f"metadata-{metadata}"),
            geometry_fingerprint=digest(f"geometry-{geometry_value}"),
            subcatchment_fingerprint=digest(f"subcatchment-{children}"),
            channel_fingerprint=digest(f"channel-{children}"),
            hillslope_fingerprint=digest(f"hillslope-{children}"),
            soil_fingerprint=digest(f"soil-{children}"),
            landuse_fingerprint=digest(f"landuse-{children}"),
            capability_fingerprint=digest(capability) if capability else None,
            actual_subcatchments=subcatchments,
            actual_channels=1,
        )

    def finalize_counts(self, release):
        states = list(release.run_states.all())
        values = {
            "expected_watersheds": len(states),
            "actual_watersheds": len(states),
            "expected_subcatchments": sum(row.actual_subcatchments for row in states),
            "actual_subcatchments": sum(row.actual_subcatchments for row in states),
            "expected_channels": sum(row.actual_channels for row in states),
            "actual_channels": sum(row.actual_channels for row in states),
        }
        DataRelease.objects.filter(pk=release.pk).update(**values)
        release.refresh_from_db()

    def serve_base(self, release):
        for index, state in enumerate(release.run_states.select_related("watershed_identity"), start=1):
            identity = state.watershed_identity
            WatershedRunAlias.objects.get_or_create(
                runid=state.runid,
                defaults={"watershed_identity": identity, "is_current": True},
            )
            watershed = Watershed.objects.create(
                runid=state.runid,
                logical_watershed=identity,
                srcname=state.runid,
                geom=geometry(index * 3),
            )
            for topazid in range(1, state.actual_subcatchments + 1):
                Subcatchment.objects.create(
                    watershed=watershed,
                    logical_watershed=identity,
                    topazid=topazid,
                    weppid=100 + topazid,
                    geom=geometry(index * 3 + topazid / 10),
                )
            Channel.objects.create(
                watershed=watershed,
                logical_watershed=identity,
                topazid=1,
                weppid=201,
                order=1,
                geom=geometry(index * 3 + 0.5),
            )
        observed = compute_serving_fingerprints(release)
        DataRelease.objects.filter(pk=release.pk).update(
            domain_fingerprint=observed.domain,
            status=DataRelease.Status.ACTIVE,
        )
        release.refresh_from_db()
        active = ActiveDataRelease.objects.get(singleton_id=1)
        active.state = ActiveDataRelease.State.ACTIVE
        active.release = release
        active.manifest_sha256 = release.manifest_sha256
        active.data_contract = 1
        active.activated_at = datetime.now(timezone.utc)
        active._allow_activation_change = True
        active.save()

    def base_and_target(self):
        base = self.release("2026-07-18.220", "base")
        self.run_state(base, "alpha", "alpha-v1")
        self.run_state(base, "beta", "beta-v1")
        self.finalize_counts(base)
        self.serve_base(base)

        target = self.release("2026-07-18.221", "target")
        self.run_state(target, "alpha", "alpha-v1", metadata="changed")
        self.run_state(
            target,
            "beta",
            "beta-v2",
            geometry_value="changed",
            capability="new-capability",
        )
        self.run_state(target, "gamma", "gamma-v1", collection_key="expanded")
        self.finalize_counts(target)
        return base, target

    def test_forward_classifies_changes_replacement_and_expansion_deterministically(self):
        base, target = self.base_and_target()
        before_counts = (
            DataRelease.objects.count(),
            Watershed.objects.count(),
            Subcatchment.objects.count(),
        )
        first = plan_forward(base, target)
        second = plan_forward(base, target)
        self.assertEqual(plan_bytes(first), plan_bytes(second))
        actions = {action["watershed_key"]: action for action in first["actions"]}
        self.assertEqual(actions["alpha"]["change_channels"], ["metadata"])
        self.assertEqual(
            actions["beta"]["change_channels"],
            ["identity", "geometry", "capability"],
        )
        self.assertEqual(actions["gamma"]["operation"], "add")
        self.assertEqual(first["expected_row_delta"]["watersheds"], 1)
        self.assertEqual(
            before_counts,
            (
                DataRelease.objects.count(),
                Watershed.objects.count(),
                Subcatchment.objects.count(),
            ),
        )

    def test_exact_inverse_is_mechanical_and_bound_to_forward(self):
        base, target = self.base_and_target()
        forward = plan_forward(base, target)
        inverse = plan_exact_inverse(forward)
        self.assertEqual(inverse["base"], forward["target"])
        self.assertEqual(inverse["target"], forward["base"])
        self.assertEqual(inverse["inverse_of_plan_sha256"], canonical_sha256(forward))
        for forward_action, inverse_action in zip(
            forward["actions"], inverse["actions"], strict=True
        ):
            self.assertEqual(inverse_action["before"], forward_action["after"])
            self.assertEqual(inverse_action["after"], forward_action["before"])
            self.assertEqual(
                inverse_action["row_delta"],
                {key: -value for key, value in forward_action["row_delta"].items()},
            )

    def test_empty_build_is_independent_and_all_adds(self):
        _, target = self.base_and_target()
        empty = plan_empty_build(target)
        self.assertEqual(empty["base"], {"kind": "EMPTY"})
        self.assertTrue(all(action["operation"] == "add" for action in empty["actions"]))
        self.assertEqual(empty["expected_row_delta"]["watersheds"], 3)
        self.assertNotIn("inverse_of_plan_sha256", empty)

    def test_generated_bundle_passes_db09_plan_contract(self):
        base, target = self.base_and_target()
        with TemporaryDirectory() as directory:
            call_command(
                "generate_release_plans",
                base_release_id=base.release_id,
                target_release_id=target.release_id,
                output_directory=directory,
            )
            plans = {
                kind: json.loads((Path(directory) / f"{kind}.json").read_text())
                for kind in ("forward", "exact-inverse", "empty-build")
            }
        contract = load_plan_contract()
        if contract is None:
            self.skipTest("DB09 schemas are outside the production server image")
        validators = contract.build_plan_validators()
        for kind, plan in plans.items():
            errors = list(
                validators[contract.PLAN_SCHEMAS[kind]].iter_errors(plan)
            )
            self.assertEqual(
                errors,
                [],
                "\n".join(
                    f"{kind}:{'/'.join(map(str, error.absolute_path))}: {error.message}"
                    for error in errors
                ),
            )
            contract.validate_plan_semantics(plan)
        contract.validate_exact_inverse(plans["forward"], plans["exact-inverse"])
        contract.validate_empty_build(plans["empty-build"])

    def test_large_shrink_requires_explicit_review(self):
        base, _ = self.base_and_target()
        shrink = self.release("2026-07-18.222", "shrink")
        self.run_state(shrink, "alpha", "alpha-v1")
        self.finalize_counts(shrink)
        with self.assertRaisesRegex(PlanningError, "Removal threshold"):
            plan_forward(base, shrink)
        accepted = plan_forward(base, shrink, allow_large_removals=True)
        self.assertEqual(
            [action["operation"] for action in accepted["actions"]],
            ["retain", "remove"],
        )

    def test_unknown_or_drifted_base_and_compatibility_changes_fail(self):
        base, target = self.base_and_target()
        active = ActiveDataRelease.objects.get(singleton_id=1)
        active.state = ActiveDataRelease.State.EMPTY
        active.release = None
        active.manifest_sha256 = None
        active.data_contract = None
        active.activated_at = None
        active._allow_activation_change = True
        active.save()
        with self.assertRaisesRegex(PlanningError, "Active base differs"):
            plan_forward(base, target)

        active.state = ActiveDataRelease.State.ACTIVE
        active.release = base
        active.manifest_sha256 = base.manifest_sha256
        active.data_contract = 1
        active.activated_at = datetime.now(timezone.utc)
        active._allow_activation_change = True
        active.save()
        watershed = Watershed.objects.order_by("runid").first()
        watershed.srcname = "drifted"
        watershed.save(update_fields=("srcname",))
        with self.assertRaisesRegex(PlanningError, "fingerprint differs"):
            plan_forward(base, target)

        watershed.srcname = watershed.runid
        watershed.save(update_fields=("srcname",))
        incompatible = self.release(
            "2026-07-18.223", "incompatible", materializer="changed"
        )
        self.run_state(incompatible, "alpha", "alpha-v1")
        self.finalize_counts(incompatible)
        with self.assertRaisesRegex(PlanningError, "compatibility coordinates"):
            plan_forward(base, incompatible)

        wrong_schema = self.release(
            "2026-07-18.224",
            "wrong-schema",
            migration="watershed.0010_attempt_scoped_staging",
        )
        self.run_state(wrong_schema, "alpha", "alpha-v1")
        self.finalize_counts(wrong_schema)
        with self.assertRaisesRegex(PlanningError, "migration differs"):
            plan_forward(base, wrong_schema)
