import json
import os
import time

import django
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


WATERSHED_COUNT = 126
SUBCATCHMENT_COUNT = 195_457
CHANNEL_COUNT = 86_895
MIGRATE_FROM = [("watershed", "0006_watershed_utility_metadata")]
MIGRATE_TO = [("watershed", "0007_stable_watershed_identity")]


def migrate(target):
    executor = MigrationExecutor(connection)
    executor.migrate(target)
    return executor.loader.project_state(target).apps


def seed_production_shape():
    polygon = "MULTIPOLYGON(((0 0,1 0,1 1,0 1,0 0)))"
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO watershed_watershed (runid, geom)
            SELECT 'fixture-' || series,
                   ST_Multi(ST_GeomFromText(%s, 4326))
            FROM generate_series(1, %s) AS series
            """,
            [polygon, WATERSHED_COUNT],
        )
        cursor.execute(
            """
            WITH watershed_ids AS (
                SELECT runid, row_number() OVER (ORDER BY runid) AS ordinal
                FROM watershed_watershed
            )
            INSERT INTO watershed_subcatchment
                (watershed_id, topazid, weppid, geom)
            SELECT watershed_ids.runid,
                   series,
                   series,
                   ST_Multi(ST_GeomFromText(%s, 4326))
            FROM generate_series(1, %s) AS series
            JOIN watershed_ids
              ON watershed_ids.ordinal = 1 + ((series - 1) %% %s)
            """,
            [polygon, SUBCATCHMENT_COUNT, WATERSHED_COUNT],
        )
        cursor.execute(
            """
            WITH watershed_ids AS (
                SELECT runid, row_number() OVER (ORDER BY runid) AS ordinal
                FROM watershed_watershed
            )
            INSERT INTO watershed_channel
                (watershed_id, topazid, weppid, "order", geom)
            SELECT watershed_ids.runid,
                   series,
                   series,
                   1,
                   ST_Multi(ST_GeomFromText(%s, 4326))
            FROM generate_series(1, %s) AS series
            JOIN watershed_ids
              ON watershed_ids.ordinal = 1 + ((series - 1) %% %s)
            """,
            [polygon, CHANNEL_COUNT, WATERSHED_COUNT],
        )


def table_counts():
    with connection.cursor() as cursor:
        counts = {}
        for label, table in (
            ("watersheds", "watershed_watershed"),
            ("subcatchments", "watershed_subcatchment"),
            ("channels", "watershed_channel"),
        ):
            cursor.execute(f"SELECT count(*) FROM {table}")
            counts[label] = cursor.fetchone()[0]
        return counts


def child_id_samples():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT min(id), max(id) FROM watershed_subcatchment"
        )
        subcatchments = cursor.fetchone()
        cursor.execute("SELECT min(id), max(id) FROM watershed_channel")
        channels = cursor.fetchone()
    return {"subcatchments": subcatchments, "channels": channels}


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")
    django.setup()
    database_name = connection.settings_dict["NAME"]
    if os.environ.get("APP_ENVIRONMENT") != "test" or not database_name.startswith(
        "db13_"
    ):
        raise SystemExit("DB13 acceptance requires APP_ENVIRONMENT=test and db13_* DB")

    migrate(MIGRATE_FROM)
    seed_production_shape()
    before_counts = table_counts()
    before_ids = child_id_samples()

    started = time.monotonic()
    migrate(MIGRATE_TO)
    forward_seconds = round(time.monotonic() - started, 3)

    from server.watershed.identity_validation import build_stable_identity_report

    report = build_stable_identity_report()
    after_ids = child_id_samples()
    old_apps = MigrationExecutor(connection).loader.project_state(MIGRATE_FROM).apps
    old_code_count = old_apps.get_model("watershed", "Watershed").objects.count()

    started = time.monotonic()
    migrate(MIGRATE_FROM)
    rollback_seconds = round(time.monotonic() - started, 3)
    rollback_counts = table_counts()
    rollback_ids = child_id_samples()

    expected_counts = {
        "watersheds": WATERSHED_COUNT,
        "subcatchments": SUBCATCHMENT_COUNT,
        "channels": CHANNEL_COUNT,
    }
    checks = {
        "seed_counts_match": before_counts == expected_counts,
        "identity_validation_passed": report["status"] == "passed",
        "old_code_reads_expanded_schema": old_code_count == WATERSHED_COUNT,
        "forward_preserved_child_ids": before_ids == after_ids,
        "rollback_preserved_counts": rollback_counts == expected_counts,
        "rollback_preserved_child_ids": rollback_ids == before_ids,
    }
    result = {
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "counts": before_counts,
        "forward_seconds": forward_seconds,
        "rollback_seconds": rollback_seconds,
        "identity_counts": report["counts"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
