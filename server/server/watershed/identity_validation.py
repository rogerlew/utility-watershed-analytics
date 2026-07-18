from django.db.models import Count, F, Q

from server.watershed.models import (
    Channel,
    Subcatchment,
    Watershed,
    WatershedIdentity,
    WatershedRunAlias,
)


def build_stable_identity_report():
    active_identities = WatershedIdentity.objects.filter(
        status=WatershedIdentity.Status.ACTIVE
    ).annotate(
        current_alias_count=Count(
            "run_aliases",
            filter=Q(run_aliases__is_current=True),
            distinct=True,
        ),
        current_watershed_count=Count("current_watershed", distinct=True),
    )
    retired_identities = WatershedIdentity.objects.filter(
        status=WatershedIdentity.Status.RETIRED
    ).annotate(
        current_alias_count=Count(
            "run_aliases",
            filter=Q(run_aliases__is_current=True),
            distinct=True,
        )
    )

    violations = {
        "watersheds_without_logical_identity": Watershed.objects.filter(
            logical_watershed=None
        ).count(),
        "subcatchments_without_logical_identity": Subcatchment.objects.filter(
            logical_watershed=None
        ).count(),
        "channels_without_logical_identity": Channel.objects.filter(
            logical_watershed=None
        ).count(),
        "subcatchment_identity_mismatches": Subcatchment.objects.exclude(
            logical_watershed_id=F("watershed__logical_watershed_id")
        ).count(),
        "channel_identity_mismatches": Channel.objects.exclude(
            logical_watershed_id=F("watershed__logical_watershed_id")
        ).count(),
        "active_identities_without_one_watershed": active_identities.exclude(
            current_watershed_count=1
        ).count(),
        "active_identities_without_one_current_alias": active_identities.exclude(
            current_alias_count=1
        ).count(),
        "retired_identities_with_current_alias": retired_identities.exclude(
            current_alias_count=0
        ).count(),
    }
    counts = {
        "watersheds": Watershed.objects.count(),
        "identities": WatershedIdentity.objects.count(),
        "assigned_watershed_keys": WatershedIdentity.objects.exclude(
            watershed_key=None
        ).count(),
        "run_aliases": WatershedRunAlias.objects.count(),
        "subcatchments": Subcatchment.objects.count(),
        "channels": Channel.objects.count(),
    }
    return {
        "status": "passed" if not any(violations.values()) else "failed",
        "counts": counts,
        "violations": violations,
    }
