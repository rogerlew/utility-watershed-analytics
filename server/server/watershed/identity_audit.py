from __future__ import annotations

from typing import Any

from django.db import connection, transaction
from django.db.migrations.recorder import MigrationRecorder
from django.db.models import Count

from server.watershed.models import Channel, Subcatchment, Watershed


AUDIT_CONTRACT_VERSION = 1

IDENTITY_SPECS = (
    {
        "name": "watershed",
        "model": Watershed,
        "business_key": ("runid",),
        "source_key": ("runid",),
        "public_identity": "GeoJSON feature.id and /api/watershed/<runid>/",
    },
    {
        "name": "subcatchment",
        "model": Subcatchment,
        "business_key": ("watershed_id", "topazid"),
        "source_key": ("watershed_id", "topazid", "weppid"),
        "public_identity": (
            "GeoJSON feature.id is a volatile database id; topazid is the "
            "run-scoped client join and selection key"
        ),
    },
    {
        "name": "channel",
        "model": Channel,
        "business_key": ("watershed_id", "topazid", "weppid", "order"),
        "source_key": ("watershed_id", "topazid", "weppid", "order"),
        "public_identity": (
            "GeoJSON feature.id is a volatile database id; topazid, weppid, "
            "and order are run-scoped properties"
        ),
    },
)


def _model_field_signature(model) -> list[dict[str, Any]]:
    return [
        {
            "column": field.column,
            "null": field.null,
            "primary_key": field.primary_key,
            "type": field.get_internal_type(),
            "unique": field.unique,
        }
        for field in model._meta.concrete_fields
    ]


def _database_constraints(model) -> dict[str, dict[str, Any]]:
    with connection.cursor() as cursor:
        return connection.introspection.get_constraints(cursor, model._meta.db_table)


def _key_is_enforced(
    constraints: dict[str, dict[str, Any]],
    columns: tuple[str, ...],
) -> bool:
    expected = list(columns)
    return any(
        constraint["columns"] == expected
        and (constraint["primary_key"] or constraint["unique"])
        for constraint in constraints.values()
    )


def _duplicate_summary(model, key: tuple[str, ...]) -> dict[str, int]:
    duplicate_counts = list(
        model.objects.values(*key)
        .annotate(rows=Count("pk"))
        .filter(rows__gt=1)
        .values_list("rows", flat=True)
    )
    return {
        "groups": len(duplicate_counts),
        "rows": sum(duplicate_counts),
    }


def _orphan_count(model) -> int:
    watershed_field = model._meta.get_field("watershed")
    child_table = connection.ops.quote_name(model._meta.db_table)
    parent_table = connection.ops.quote_name(Watershed._meta.db_table)
    child_column = connection.ops.quote_name(watershed_field.column)
    parent_column = connection.ops.quote_name(Watershed._meta.pk.column)
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT count(*)
            FROM {child_table} AS child
            LEFT JOIN {parent_table} AS parent
              ON child.{child_column} = parent.{parent_column}
            WHERE parent.{parent_column} IS NULL
            """
        )
        return int(cursor.fetchone()[0])


def _foreign_key_report(model) -> dict[str, Any] | None:
    if model is Watershed:
        return None

    watershed_field = model._meta.get_field("watershed")
    constraints = _database_constraints(model)
    expected_target = (Watershed._meta.db_table, Watershed._meta.pk.column)
    enforced = any(
        constraint["columns"] == [watershed_field.column]
        and constraint["foreign_key"] == expected_target
        for constraint in constraints.values()
    )
    return {
        "column": watershed_field.column,
        "database_enforced": enforced,
        "on_delete": watershed_field.remote_field.on_delete.__name__,
        "orphan_rows": _orphan_count(model),
        "target_column": Watershed._meta.pk.column,
        "target_table": Watershed._meta.db_table,
    }


def _table_report(spec: dict[str, Any]) -> dict[str, Any]:
    model = spec["model"]
    business_key = spec["business_key"]
    constraints = _database_constraints(model)
    return {
        "business_key": list(business_key),
        "business_key_database_enforced": _key_is_enforced(
            constraints,
            business_key,
        ),
        "database_primary_key": [model._meta.pk.column],
        "duplicate_business_key": _duplicate_summary(model, business_key),
        "field_signature": _model_field_signature(model),
        "foreign_key": _foreign_key_report(model),
        "public_identity": spec["public_identity"],
        "row_count": model.objects.count(),
        "source_key": list(spec["source_key"]),
        "table": model._meta.db_table,
    }


def build_identity_audit_report() -> dict[str, Any]:
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")

        tables = {spec["name"]: _table_report(spec) for spec in IDENTITY_SPECS}
        applied_migrations = list(
            MigrationRecorder.Migration.objects.filter(app="watershed")
            .order_by("name")
            .values_list("name", flat=True)
        )

    violations = []
    for name, table in tables.items():
        duplicate_groups = table["duplicate_business_key"]["groups"]
        if duplicate_groups:
            violations.append(
                f"{name}: {duplicate_groups} duplicate business-key group(s)"
            )
        foreign_key = table["foreign_key"]
        if foreign_key and foreign_key["orphan_rows"]:
            violations.append(
                f"{name}: {foreign_key['orphan_rows']} orphan row(s)"
            )

    warnings = [
        f"{name}: business key is not enforced by a database constraint"
        for name, table in tables.items()
        if not table["business_key_database_enforced"]
    ]
    if all(table["row_count"] == 0 for table in tables.values()):
        warnings.append(
            "watershed-domain tables are empty; absence of dirty data is not established"
        )

    return {
        "audit_contract_version": AUDIT_CONTRACT_VERSION,
        "read_only_transaction": True,
        "status": "failed" if violations else "passed",
        "tables": tables,
        "violations": violations,
        "warnings": warnings,
        "watershed_migrations": applied_migrations,
    }
