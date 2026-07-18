from server.watershed.models import (
    Channel,
    Subcatchment,
    Watershed,
    WatershedCollection,
    WatershedIdentity,
    WatershedRunAlias,
)


RECONCILED_MODELS = (Watershed, Subcatchment, Channel)
REBUILD_DELETE_ORDER = (Channel, Subcatchment, Watershed)
PERSISTENT_IDENTITY_MODELS = (
    WatershedCollection,
    WatershedIdentity,
    WatershedRunAlias,
)


def reconciled_table_names():
    return frozenset(model._meta.db_table for model in RECONCILED_MODELS)


def rebuild_delete_order():
    return tuple(model._meta.db_table for model in REBUILD_DELETE_ORDER)


def persistent_identity_table_names():
    return frozenset(model._meta.db_table for model in PERSISTENT_IDENTITY_MODELS)
