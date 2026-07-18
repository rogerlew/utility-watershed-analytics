from django.db import migrations, models


def assert_existing_integrity(apps, schema_editor):
    checks = (
        (
            "subcatchment_run_key",
            """
            SELECT count(*) FROM (
                SELECT 1 FROM watershed_subcatchment
                GROUP BY watershed_id, topazid HAVING count(*) > 1
            ) duplicate_groups
            """,
        ),
        (
            "subcatchment_logical_key",
            """
            SELECT count(*) FROM (
                SELECT 1 FROM watershed_subcatchment
                WHERE logical_watershed_id IS NOT NULL
                GROUP BY logical_watershed_id, topazid HAVING count(*) > 1
            ) duplicate_groups
            """,
        ),
        (
            "channel_run_key",
            """
            SELECT count(*) FROM (
                SELECT 1 FROM watershed_channel
                GROUP BY watershed_id, topazid, weppid, "order"
                HAVING count(*) > 1
            ) duplicate_groups
            """,
        ),
        (
            "channel_logical_key",
            """
            SELECT count(*) FROM (
                SELECT 1 FROM watershed_channel
                WHERE logical_watershed_id IS NOT NULL
                GROUP BY logical_watershed_id, topazid, weppid, "order"
                HAVING count(*) > 1
            ) duplicate_groups
            """,
        ),
        (
            "subcatchment_logical_mismatch",
            """
            SELECT count(*)
            FROM watershed_subcatchment child
            JOIN watershed_watershed parent ON parent.runid = child.watershed_id
            WHERE child.logical_watershed_id IS NOT NULL
              AND child.logical_watershed_id IS DISTINCT FROM parent.logical_watershed_id
            """,
        ),
        (
            "channel_logical_mismatch",
            """
            SELECT count(*)
            FROM watershed_channel child
            JOIN watershed_watershed parent ON parent.runid = child.watershed_id
            WHERE child.logical_watershed_id IS NOT NULL
              AND child.logical_watershed_id IS DISTINCT FROM parent.logical_watershed_id
            """,
        ),
        (
            "collection_key_format",
            """
            SELECT count(*) FROM watershed_watershedcollection
            WHERE key !~ '^[a-z0-9]+(-[a-z0-9]+)*$'
            """,
        ),
        (
            "watershed_key_format",
            """
            SELECT count(*) FROM watershed_watershedidentity
            WHERE watershed_key IS NOT NULL
              AND watershed_key !~ '^[a-z0-9]+(-[a-z0-9]+)*$'
            """,
        ),
        (
            "watershed_identity_status",
            """
            SELECT count(*) FROM watershed_watershedidentity
            WHERE status NOT IN ('active', 'retired')
            """,
        ),
    )
    violations = []
    with schema_editor.connection.cursor() as cursor:
        for code, query in checks:
            cursor.execute(query)
            count = int(cursor.fetchone()[0])
            if count:
                violations.append(f"{code}={count}")
    if violations:
        raise RuntimeError(
            "DB14 integrity preflight failed: " + ", ".join(violations)
        )


class Migration(migrations.Migration):
    dependencies = [
        ("watershed", "0007_stable_watershed_identity"),
    ]

    operations = [
        migrations.RunPython(assert_existing_integrity, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="watershedcollection",
            constraint=models.CheckConstraint(
                condition=models.Q(("key__regex", "^[a-z0-9]+(?:-[a-z0-9]+)*$")),
                name="collection_key_format",
            ),
        ),
        migrations.AddConstraint(
            model_name="watershedidentity",
            constraint=models.CheckConstraint(
                condition=models.Q(watershed_key__isnull=True)
                | models.Q(
                    watershed_key__regex="^[a-z0-9]+(?:-[a-z0-9]+)*$"
                ),
                name="watershed_key_format",
            ),
        ),
        migrations.AddConstraint(
            model_name="watershedidentity",
            constraint=models.CheckConstraint(
                condition=models.Q(("status__in", ("active", "retired"))),
                name="watershed_identity_status_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="subcatchment",
            constraint=models.UniqueConstraint(
                fields=("watershed", "topazid"),
                name="subcatchment_run_topaz_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="subcatchment",
            constraint=models.UniqueConstraint(
                condition=models.Q(("logical_watershed__isnull", False)),
                fields=("logical_watershed", "topazid"),
                name="subcatchment_logical_topaz_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="channel",
            constraint=models.UniqueConstraint(
                fields=("watershed", "topazid", "weppid", "order"),
                name="channel_run_topaz_wepp_order_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="channel",
            constraint=models.UniqueConstraint(
                condition=models.Q(("logical_watershed__isnull", False)),
                fields=("logical_watershed", "topazid", "weppid", "order"),
                name="channel_logical_topaz_wepp_order_uniq",
            ),
        ),
    ]
