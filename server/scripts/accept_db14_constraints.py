import json
import os
import threading
import time
from datetime import timedelta

import django
import psycopg
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone


WATERSHED_COUNT = 126
SUBCATCHMENT_COUNT = 195_457
CHANNEL_COUNT = 86_895
MIGRATE_FROM = ("watershed", "0007_stable_watershed_identity")
MIGRATE_TO = ("watershed", "0008_domain_integrity_constraints")
OBSERVED_RELATIONS = (
    "watershed_watershedcollection",
    "watershed_watershedidentity",
    "watershed_subcatchment",
    "watershed_channel",
)


def migration_targets(watershed_target):
    executor = MigrationExecutor(connection)
    return [
        watershed_target if app == "watershed" else (app, name)
        for app, name in executor.loader.graph.leaf_nodes()
    ]


def migrate(watershed_target):
    executor = MigrationExecutor(connection)
    executor.migrate(migration_targets(watershed_target))


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
            SELECT 'fixture-' || series,
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
            SELECT 'fixture-' || series, TRUE, md5(series::text)::uuid
            FROM generate_series(1, %s) AS series
            """,
            [WATERSHED_COUNT],
        )
        cursor.execute(
            """
            WITH watershed_ids AS (
                SELECT runid, logical_watershed_id,
                       row_number() OVER (ORDER BY runid) AS ordinal
                FROM watershed_watershed
            )
            INSERT INTO watershed_subcatchment
                (watershed_id, logical_watershed_id, topazid, weppid, geom)
            SELECT watershed_ids.runid,
                   watershed_ids.logical_watershed_id,
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
                SELECT runid, logical_watershed_id,
                       row_number() OVER (ORDER BY runid) AS ordinal
                FROM watershed_watershed
            )
            INSERT INTO watershed_channel
                (watershed_id, logical_watershed_id, topazid, weppid, "order", geom)
            SELECT watershed_ids.runid,
                   watershed_ids.logical_watershed_id,
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


def domain_counts():
    with connection.cursor() as cursor:
        result = {}
        for label, table in (
            ("watersheds", "watershed_watershed"),
            ("subcatchments", "watershed_subcatchment"),
            ("channels", "watershed_channel"),
        ):
            cursor.execute(f"SELECT count(*) FROM {table}")
            result[label] = int(cursor.fetchone()[0])
    return result


def child_id_samples():
    with connection.cursor() as cursor:
        cursor.execute("SELECT min(id), max(id) FROM watershed_subcatchment")
        subcatchments = cursor.fetchone()
        cursor.execute("SELECT min(id), max(id) FROM watershed_channel")
        channels = cursor.fetchone()
    return {"subcatchments": subcatchments, "channels": channels}


def non_domain_counts():
    with connection.cursor() as cursor:
        result = {}
        for label, table in (
            ("auth_users", "auth_user"),
            ("sessions", "django_session"),
            ("content_types", "django_content_type"),
            ("identity_rows", "watershed_watershedidentity"),
            ("aliases", "watershed_watershedrunalias"),
        ):
            cursor.execute(f"SELECT count(*) FROM {table}")
            result[label] = int(cursor.fetchone()[0])
    return result


def observe_locks(stop_event, started_event, result):
    settings = connection.settings_dict
    try:
        with psycopg.connect(
            host=settings["HOST"],
            port=settings["PORT"],
            dbname=settings["NAME"],
            user=settings["USER"],
            password=settings["PASSWORD"],
            autocommit=True,
        ) as observer:
            started_event.set()
            while not stop_event.is_set():
                with observer.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT relation.relname, locks.mode
                        FROM pg_locks locks
                        JOIN pg_class relation ON relation.oid = locks.relation
                        WHERE relation.relname = ANY(%s)
                          AND locks.pid <> pg_backend_pid()
                          AND locks.granted
                        """,
                        [list(OBSERVED_RELATIONS)],
                    )
                    rows = cursor.fetchall()
                if rows:
                    result["samples"] += 1
                    for relation, mode in rows:
                        result["modes"].add(f"{relation}:{mode}")
                time.sleep(0.002)
    except Exception as exc:
        result["error"] = type(exc).__name__
        started_event.set()


def rejected(statement, params=()):
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(statement, params)
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    except IntegrityError:
        return True
    return False


def constraint_names():
    names = set()
    with connection.cursor() as cursor:
        for table in OBSERVED_RELATIONS:
            names.update(connection.introspection.get_constraints(cursor, table))
    return names


def rebuild_probe(expected_non_domain):
    preserved = False
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM watershed_channel")
                cursor.execute("DELETE FROM watershed_subcatchment")
                cursor.execute("DELETE FROM watershed_watershed")
            preserved = non_domain_counts() == expected_non_domain
            raise RuntimeError("rollback rebuild probe")
    except RuntimeError as exc:
        if str(exc) != "rollback rebuild probe":
            raise
    return preserved


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")
    django.setup()
    from django.contrib.sessions.models import Session

    database_name = connection.settings_dict["NAME"]
    if os.environ.get("APP_ENVIRONMENT") != "test" or not database_name.startswith(
        "db14_"
    ):
        raise SystemExit("DB14 acceptance requires APP_ENVIRONMENT=test and db14_* DB")

    migrate(MIGRATE_FROM)
    get_user_model().objects.create_user(username="db14-acceptance")
    Session.objects.create(
        session_key="db14-acceptance",
        session_data="e30:synthetic",
        expire_date=timezone.now() + timedelta(hours=1),
    )
    seed_production_shape()
    before_counts = domain_counts()
    before_ids = child_id_samples()
    before_non_domain = non_domain_counts()

    lock_result = {"samples": 0, "modes": set(), "error": None}
    stop_event = threading.Event()
    started_event = threading.Event()
    observer = threading.Thread(
        target=observe_locks,
        args=(stop_event, started_event, lock_result),
        daemon=True,
    )
    observer.start()
    started_event.wait(timeout=5)
    started = time.monotonic()
    migrate(MIGRATE_TO)
    forward_seconds = round(time.monotonic() - started, 3)
    stop_event.set()
    observer.join(timeout=5)

    required_constraints = {
        "collection_key_format",
        "watershed_key_format",
        "watershed_identity_status_valid",
        "subcatchment_run_topaz_uniq",
        "subcatchment_logical_topaz_uniq",
        "channel_run_topaz_wepp_order_uniq",
        "channel_logical_topaz_wepp_order_uniq",
    }
    installed_constraints = constraint_names()
    duplicate_subcatchment_rejected = rejected(
        """
        INSERT INTO watershed_subcatchment
            (watershed_id, logical_watershed_id, topazid, weppid, geom)
        SELECT watershed_id, logical_watershed_id, topazid, weppid + 1, geom
        FROM watershed_subcatchment ORDER BY id LIMIT 1
        """
    )
    orphan_channel_rejected = rejected(
        """
        INSERT INTO watershed_channel
            (watershed_id, logical_watershed_id, topazid, weppid, "order", geom)
        SELECT 'missing-run', logical_watershed_id, -1, -1, 1, geom
        FROM watershed_channel ORDER BY id LIMIT 1
        """
    )
    invalid_collection_rejected = rejected(
        "INSERT INTO watershed_watershedcollection (key) VALUES (%s)",
        ["Invalid Collection"],
    )
    rebuild_preserved_non_domain = rebuild_probe(before_non_domain)

    started = time.monotonic()
    migrate(MIGRATE_FROM)
    rollback_seconds = round(time.monotonic() - started, 3)
    after_counts = domain_counts()
    after_ids = child_id_samples()
    after_non_domain = non_domain_counts()

    expected_counts = {
        "watersheds": WATERSHED_COUNT,
        "subcatchments": SUBCATCHMENT_COUNT,
        "channels": CHANNEL_COUNT,
    }
    checks = {
        "seed_counts_match": before_counts == expected_counts,
        "constraints_installed": required_constraints <= installed_constraints,
        "duplicate_subcatchment_rejected": duplicate_subcatchment_rejected,
        "orphan_channel_rejected": orphan_channel_rejected,
        "invalid_collection_rejected": invalid_collection_rejected,
        "rebuild_preserved_non_domain": rebuild_preserved_non_domain,
        "forward_preserved_counts": after_counts == before_counts,
        "forward_preserved_child_ids": after_ids == before_ids,
        "rollback_preserved_non_domain": after_non_domain == before_non_domain,
        "locks_observed": lock_result["samples"] > 0 and not lock_result["error"],
    }
    result = {
        "status": "passed" if all(checks.values()) else "failed",
        "checks": checks,
        "counts": before_counts,
        "forward_seconds": forward_seconds,
        "rollback_seconds": rollback_seconds,
        "lock_samples": lock_result["samples"],
        "lock_modes": sorted(lock_result["modes"]),
        "lock_observer_error": lock_result["error"],
        "non_domain_counts": before_non_domain,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
