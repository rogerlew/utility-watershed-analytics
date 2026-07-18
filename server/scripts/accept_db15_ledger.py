import json
import os
import time

import django
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


WATERSHED_COUNT = 126
SUBCATCHMENT_COUNT = 195_457
CHANNEL_COUNT = 86_895
MIGRATE_FROM = ("watershed", "0008_domain_integrity_constraints")
MIGRATE_TO = ("watershed", "0009_release_ledger_capabilities")


def migration_targets(watershed_target):
    executor = MigrationExecutor(connection)
    return [
        watershed_target if app == "watershed" else (app, name)
        for app, name in executor.loader.graph.leaf_nodes()
    ]


def migrate(watershed_target):
    MigrationExecutor(connection).migrate(migration_targets(watershed_target))


def seed_production_shape():
    polygon = "MULTIPOLYGON(((0 0,1 0,1 1,0 1,0 0)))"
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO watershed_watershedidentity
                (id, watershed_key, status, collection_id)
            SELECT md5(series::text)::uuid, NULL, 'active', 'gate-creek'
            FROM generate_series(1, %s) AS series
            """,
            [WATERSHED_COUNT],
        )
        cursor.execute(
            """
            INSERT INTO watershed_watershed (runid, logical_watershed_id, geom)
            SELECT 'db15-fixture-' || series,
                   md5(series::text)::uuid,
                   ST_Multi(ST_GeomFromText(%s, 4326))
            FROM generate_series(1, %s) AS series
            """,
            [polygon, WATERSHED_COUNT],
        )
        cursor.execute(
            """
            INSERT INTO watershed_watershedrunalias
                (runid, is_current, watershed_identity_id)
            SELECT 'db15-fixture-' || series, TRUE, md5(series::text)::uuid
            FROM generate_series(1, %s) AS series
            """,
            [WATERSHED_COUNT],
        )
        for table, count, columns, values in (
            (
                "watershed_subcatchment",
                SUBCATCHMENT_COUNT,
                "topazid, weppid",
                "series, series",
            ),
            (
                "watershed_channel",
                CHANNEL_COUNT,
                'topazid, weppid, "order"',
                "series, series, 1",
            ),
        ):
            cursor.execute(
                f"""
                WITH watershed_ids AS (
                    SELECT runid, logical_watershed_id,
                           row_number() OVER (ORDER BY runid) AS ordinal
                    FROM watershed_watershed
                )
                INSERT INTO {table}
                    (watershed_id, logical_watershed_id, {columns}, geom)
                SELECT watershed_ids.runid,
                       watershed_ids.logical_watershed_id,
                       {values},
                       ST_Multi(ST_GeomFromText(%s, 4326))
                FROM generate_series(1, %s) AS series
                JOIN watershed_ids
                  ON watershed_ids.ordinal = 1 + ((series - 1) %% %s)
                """,
                [polygon, count, WATERSHED_COUNT],
            )


def domain_state():
    state = {}
    with connection.cursor() as cursor:
        for label, table in (
            ("watersheds", "watershed_watershed"),
            ("subcatchments", "watershed_subcatchment"),
            ("channels", "watershed_channel"),
        ):
            cursor.execute(f"SELECT count(*) FROM {table}")
            state[label] = int(cursor.fetchone()[0])
        cursor.execute("SELECT min(id), max(id) FROM watershed_subcatchment")
        state["subcatchment_ids"] = cursor.fetchone()
        cursor.execute("SELECT min(id), max(id) FROM watershed_channel")
        state["channel_ids"] = cursor.fetchone()
    return state


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")
    django.setup()
    database_name = connection.settings_dict["NAME"]
    if os.environ.get("APP_ENVIRONMENT") != "test" or not database_name.startswith(
        "db15_"
    ):
        raise SystemExit("DB15 acceptance requires APP_ENVIRONMENT=test and db15_* DB")

    migrate(MIGRATE_FROM)
    seed_production_shape()
    before = domain_state()
    started = time.monotonic()
    migrate(MIGRATE_TO)
    forward_seconds = round(time.monotonic() - started, 3)

    from server.watershed.models import ActiveDataRelease

    active = ActiveDataRelease.objects.get(singleton_id=1)
    singleton_empty = (
        ActiveDataRelease.objects.count() == 1
        and active.state == ActiveDataRelease.State.EMPTY
        and active.release_id is None
    )
    started = time.monotonic()
    migrate(MIGRATE_FROM)
    rollback_seconds = round(time.monotonic() - started, 3)
    after = domain_state()
    expected = {
        "watersheds": WATERSHED_COUNT,
        "subcatchments": SUBCATCHMENT_COUNT,
        "channels": CHANNEL_COUNT,
    }
    checks = {
        "seed_counts_match": all(before[key] == value for key, value in expected.items()),
        "empty_singleton_bootstrapped": singleton_empty,
        "forward_reverse_preserved_domain": after == before,
    }
    result = {
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "counts": expected,
        "forward_seconds": forward_seconds,
        "rollback_seconds": rollback_seconds,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
