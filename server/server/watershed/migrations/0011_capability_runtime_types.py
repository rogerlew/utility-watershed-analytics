from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("watershed", "0010_attempt_scoped_staging")]

    operations = [
        migrations.RemoveConstraint(
            model_name="runcapability",
            name="capability_type_valid",
        ),
        migrations.AlterField(
            model_name="runcapability",
            name="capability_type",
            field=models.CharField(
                choices=[("rhessys", "RHESSys"), ("sbs", "Soil burn severity")],
                default="rhessys",
                max_length=32,
            ),
        ),
        migrations.AddConstraint(
            model_name="runcapability",
            constraint=models.CheckConstraint(
                condition=models.Q(capability_type__in=("rhessys", "sbs")),
                name="capability_type_valid",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="stagedruncapability",
            name="stage_cap_type_valid",
        ),
        migrations.AlterField(
            model_name="stagedruncapability",
            name="capability_type",
            field=models.CharField(
                choices=[("rhessys", "RHESSys"), ("sbs", "Soil burn severity")],
                default="rhessys",
                max_length=32,
            ),
        ),
        migrations.AddConstraint(
            model_name="stagedruncapability",
            constraint=models.CheckConstraint(
                condition=models.Q(capability_type__in=("rhessys", "sbs")),
                name="stage_cap_type_valid",
            ),
        ),
    ]
