from django.db import transaction
from rest_framework.exceptions import APIException, NotFound

from server.watershed.models import Watershed, WatershedIdentity, WatershedRunAlias


class Gone(APIException):
    status_code = 410
    default_detail = "Watershed was retired."
    default_code = "gone"


class IdentityConflict(ValueError):
    pass


def _current_watershed(identity: WatershedIdentity) -> Watershed:
    if identity.status == WatershedIdentity.Status.RETIRED:
        raise Gone()
    try:
        return identity.current_watershed
    except Watershed.DoesNotExist as exc:
        raise NotFound("Watershed has no current serving revision.") from exc


def resolve_runid(runid: str) -> Watershed:
    try:
        alias = WatershedRunAlias.objects.select_related(
            "watershed_identity"
        ).get(runid=runid)
    except WatershedRunAlias.DoesNotExist:
        try:
            return Watershed.objects.get(pk=runid)
        except Watershed.DoesNotExist as exc:
            raise NotFound() from exc
    return _current_watershed(alias.watershed_identity)


def resolve_watershed_key(watershed_key: str) -> Watershed:
    try:
        identity = WatershedIdentity.objects.get(watershed_key=watershed_key)
    except WatershedIdentity.DoesNotExist as exc:
        raise NotFound() from exc
    return _current_watershed(identity)


@transaction.atomic
def activate_run_alias(identity: WatershedIdentity, runid: str) -> WatershedRunAlias:
    locked_identity = WatershedIdentity.objects.select_for_update().get(pk=identity.pk)
    existing_alias = WatershedRunAlias.objects.select_for_update().filter(
        runid=runid
    ).first()
    if (
        existing_alias is not None
        and existing_alias.watershed_identity_id != locked_identity.pk
    ):
        raise IdentityConflict(f"run ID {runid!r} is permanently bound to another watershed")
    WatershedRunAlias.objects.filter(
        watershed_identity=locked_identity,
        is_current=True,
    ).update(is_current=False)
    if existing_alias is None:
        alias = WatershedRunAlias.objects.create(
            runid=runid,
            watershed_identity=locked_identity,
            is_current=True,
        )
    else:
        existing_alias.is_current = True
        existing_alias.save(update_fields=("is_current",))
        alias = existing_alias
    return alias
