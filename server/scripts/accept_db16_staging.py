import json
import os
import time

import django
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from scripts.accept_db15_ledger import (
    CHANNEL_COUNT,
    SUBCATCHMENT_COUNT,
    WATERSHED_COUNT,
    domain_state,
    seed_production_shape,
)


MIGRATE_FROM = ("watershed", "0009_release_ledger_capabilities")
MIGRATE_TO = ("watershed", "0010_attempt_scoped_staging")
STAGING_TABLES = (
    "watershed_datareleasestagingstate",
    "watershed_stagedwatershed",
    "watershed_stagedsubcatchment",
    "watershed_stagedchannel",
    "watershed_stagedruncapability",
)


def migration_targets(watershed_target):
    executor = MigrationExecutor(connection)
    return [
        watershed_target if app == "watershed" else (app, name)
        for app, name in executor.loader.graph.leaf_nodes()
    ]


def migrate(watershed_target):
    MigrationExecutor(connection).migrate(migration_targets(watershed_target))


def logged_staging_tables():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT relname, relpersistence FROM pg_class WHERE relname = ANY(%s)",
            [list(STAGING_TABLES)],
        )
        return dict(cursor.fetchall())


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")
    django.setup()
    database_name = connection.settings_dict["NAME"]
    if os.environ.get("APP_ENVIRONMENT") != "test" or not database_name.startswith(
        "db16_"
    ):
        raise SystemExit("DB16 acceptance requires APP_ENVIRONMENT=test and db16_* DB")

    migrate(MIGRATE_FROM)
    seed_production_shape()
    before = domain_state()
    started = time.monotonic()
    migrate(MIGRATE_TO)
    forward_seconds = round(time.monotonic() - started, 3)
    persistence = logged_staging_tables()

    from server.watershed.models import ActiveDataRelease

    singleton_preserved = ActiveDataRelease.objects.filter(
        singleton_id=1,
        state=ActiveDataRelease.State.EMPTY,
        release__isnull=True,
    ).count() == 1

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
        "five_logged_tables_created": persistence
        == {table: "p" for table in STAGING_TABLES},
        "empty_singleton_preserved": singleton_preserved,
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
