import hashlib
import json

from django.db import connection, transaction
from django.db.migrations.loader import MigrationLoader

from server.watershed.fingerprint_contract import canonical_sha256
from server.watershed.models import ActiveDataRelease, DataRunState
from server.watershed.release_validation import compute_serving_fingerprints


class PlanningError(RuntimeError):
    pass


CHANGE_CHANNELS = ("identity", "metadata", "geometry", "children", "capability")
MAX_UNREVIEWED_REMOVALS = 5
MAX_UNREVIEWED_REMOVAL_RATIO = 0.10


def _require(condition, message):
    if not condition:
        raise PlanningError(message)


def _current_migration():
    loader = MigrationLoader(connection)
    leaves = loader.graph.leaf_nodes("watershed")
    _require(len(leaves) == 1, "Watershed migration leaf is ambiguous.")
    leaf = leaves[0]
    _require(leaf in loader.applied_migrations, "Current watershed migration is not applied.")
    return f"{leaf[0]}.{leaf[1]}"


def _assert_release_compatible(release):
    _require(
        (
            release.schema_version,
            release.data_contract,
            release.identity_contract,
            release.artifact_contract,
            release.fingerprint_version,
        )
        == (1, 1, 1, 1, 1),
        "Release contracts are unsupported.",
    )
    _require(
        release.supported_migration == _current_migration(),
        "Release migration differs from the applied schema.",
    )
    _require(
        not release.run_states.exclude(
            validation_status=DataRunState.ValidationStatus.VALIDATED
        ).exists(),
        "Release contains an unvalidated run state.",
    )


def _assert_pair_compatible(base, target):
    _assert_release_compatible(base)
    _assert_release_compatible(target)
    coordinates = (
        "schema_version",
        "data_contract",
        "identity_contract",
        "artifact_contract",
        "fingerprint_version",
        "supported_migration",
        "materializer_image_digest",
        "materializer_git_commit",
    )
    _require(
        all(getattr(base, field) == getattr(target, field) for field in coordinates),
        "Base and target compatibility coordinates differ.",
    )


def _release_state(release):
    return {
        "kind": "RELEASE",
        "release_id": release.release_id,
        "manifest_sha256": release.manifest_sha256,
        "release_fingerprint": release.release_fingerprint,
        "domain_fingerprint": release.domain_fingerprint,
    }


def _run_state(run_state):
    return {
        "runid": run_state.runid,
        "run_fingerprint": run_state.run_fingerprint,
        "capability_fingerprint": run_state.capability_fingerprint,
    }


def _row_counts(run_state):
    if run_state is None:
        return {"watersheds": 0, "subcatchments": 0, "channels": 0}
    return {
        "watersheds": run_state.actual_watersheds,
        "subcatchments": run_state.actual_subcatchments,
        "channels": run_state.actual_channels,
    }


def _row_delta(before, after):
    before_counts = _row_counts(before)
    after_counts = _row_counts(after)
    return {
        key: after_counts[key] - before_counts[key]
        for key in ("watersheds", "subcatchments", "channels")
    }


def _change_channels(before, after):
    if before is None or after is None:
        state = after or before
        channels = ["identity", "metadata", "geometry", "children"]
        if state.capability_fingerprint is not None:
            channels.append("capability")
        return channels
    channels = []
    if before.collection_id != after.collection_id or before.runid != after.runid:
        channels.append("identity")
    if before.metadata_fingerprint != after.metadata_fingerprint:
        channels.append("metadata")
    if before.geometry_fingerprint != after.geometry_fingerprint:
        channels.append("geometry")
    if any(
        getattr(before, field) != getattr(after, field)
        for field in (
            "subcatchment_fingerprint",
            "channel_fingerprint",
            "hillslope_fingerprint",
            "soil_fingerprint",
            "landuse_fingerprint",
            "actual_subcatchments",
            "actual_channels",
        )
    ):
        channels.append("children")
    if before.capability_fingerprint != after.capability_fingerprint:
        channels.append("capability")
    return [channel for channel in CHANGE_CHANNELS if channel in channels]


def _action(watershed_key, before, after):
    if before is None:
        operation = "add"
    elif after is None:
        operation = "remove"
    else:
        channels = _change_channels(before, after)
        if before.run_fingerprint != after.run_fingerprint and not channels:
            channels = ["identity"]
        _require(
            bool(channels) == (before.run_fingerprint != after.run_fingerprint),
            "Run fingerprint and classified changes disagree.",
        )
        operation = "change" if channels else "retain"
    if before is None or after is None:
        channels = _change_channels(before, after)
    return {
        "watershed_key": watershed_key,
        "operation": operation,
        "before": _run_state(before) if before else None,
        "after": _run_state(after) if after else None,
        "change_channels": channels,
        "row_delta": _row_delta(before, after),
    }


def _run_states(release):
    states = {}
    rows = release.run_states.select_related(
        "collection", "watershed_identity"
    ).order_by("watershed_identity__watershed_key")
    for row in rows:
        key = row.watershed_identity.watershed_key
        _require(key and key not in states, "Release watershed membership is ambiguous.")
        states[key] = row
    return states


def _sum_deltas(actions):
    return {
        key: sum(action["row_delta"][key] for action in actions)
        for key in ("watersheds", "subcatchments", "channels")
    }


def _plan_id(kind, base, target):
    digest = hashlib.sha256(
        f"{kind}:{base}:{target}".encode()
    ).hexdigest()[:20]
    return f"{kind}-{digest}"


def _plan_document(kind, base_state, target, actions):
    return {
        "schema_version": 1,
        "plan_kind": kind,
        "plan_id": _plan_id(kind, base_state.get("release_id", "empty"), target.release_id),
        "fingerprint_version": 1,
        "data_contract": 1,
        "identity_contract": 1,
        "supported_migration": target.supported_migration,
        "materializer": {
            "image_digest": target.materializer_image_digest,
            "git_commit": target.materializer_git_commit,
        },
        "base": base_state,
        "target": _release_state(target),
        "actions": actions,
        "expected_row_delta": _sum_deltas(actions),
    }


@transaction.atomic
def plan_forward(base, target, *, allow_large_removals=False):
    active = ActiveDataRelease.objects.select_for_update().get(singleton_id=1)
    _require(
        active.state == ActiveDataRelease.State.ACTIVE
        and active.release_id == base.release_id
        and active.manifest_sha256 == base.manifest_sha256,
        "Active base differs from the reviewed base.",
    )
    _assert_pair_compatible(base, target)
    observed = compute_serving_fingerprints(base)
    _require(
        observed.domain == base.domain_fingerprint,
        "Observed active domain fingerprint differs from the reviewed base.",
    )
    before = _run_states(base)
    after = _run_states(target)
    keys = sorted(set(before) | set(after))
    actions = [_action(key, before.get(key), after.get(key)) for key in keys]
    removals = sum(action["operation"] == "remove" for action in actions)
    ratio = removals / len(before) if before else 0
    _require(
        allow_large_removals
        or (
            removals <= MAX_UNREVIEWED_REMOVALS
            and ratio <= MAX_UNREVIEWED_REMOVAL_RATIO
        ),
        "Removal threshold requires explicit reviewed authorization.",
    )
    return _plan_document("forward", _release_state(base), target, actions)


def plan_empty_build(target):
    _assert_release_compatible(target)
    actions = [
        _action(key, None, state)
        for key, state in sorted(_run_states(target).items())
    ]
    return _plan_document("empty-build", {"kind": "EMPTY"}, target, actions)


def plan_exact_inverse(forward_plan):
    _require(forward_plan.get("plan_kind") == "forward", "Inverse requires a forward plan.")
    inverse_operations = {
        "add": "remove",
        "remove": "add",
        "change": "change",
        "retain": "retain",
    }
    actions = []
    for action in forward_plan["actions"]:
        actions.append(
            {
                "watershed_key": action["watershed_key"],
                "operation": inverse_operations[action["operation"]],
                "before": action["after"],
                "after": action["before"],
                "change_channels": list(action["change_channels"]),
                "row_delta": {
                    key: -action["row_delta"][key]
                    for key in ("watersheds", "subcatchments", "channels")
                },
            }
        )
    document = {
        **forward_plan,
        "plan_kind": "exact-inverse",
        "plan_id": _plan_id(
            "exact-inverse",
            forward_plan["target"]["release_id"],
            forward_plan["base"]["release_id"],
        ),
        "base": forward_plan["target"],
        "target": forward_plan["base"],
        "actions": actions,
        "expected_row_delta": _sum_deltas(actions),
        "inverse_of_plan_sha256": canonical_sha256(forward_plan),
    }
    return document


def plan_bytes(plan):
    return (
        json.dumps(
            plan,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()
