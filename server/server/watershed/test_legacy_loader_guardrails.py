import os
import subprocess
import sys
from contextlib import nullcontext
from io import StringIO
from itertools import product
from pathlib import Path
from unittest.mock import patch

from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from server.watershed.management.commands.load_watershed_data import Command
from server.watershed.models import Channel, Subcatchment, Watershed


class LegacyLoaderGuardrailTests(SimpleTestCase):
    def execute(
        self,
        *,
        environment,
        force,
        dry_run,
        load_all,
        runids,
        reject_before_query=False,
    ):
        command = Command(stdout=StringIO())
        count_side_effect = None
        if reject_before_query:
            count_side_effect = AssertionError("rejected flags reached the database")
        with (
            override_settings(APP_ENVIRONMENT=environment),
            patch.object(
                Watershed.objects,
                "count",
                return_value=0,
                side_effect=count_side_effect,
            ),
            patch.object(Subcatchment.objects, "count", return_value=0),
            patch.object(Channel.objects, "count", return_value=0),
            patch.object(Watershed.objects, "all"),
            patch.object(Subcatchment.objects, "all"),
            patch.object(Channel.objects, "all"),
            patch(
                "server.watershed.management.commands.load_watershed_data.run"
            ),
            patch(
                "server.watershed.management.commands.load_watershed_data.transaction.atomic",
                side_effect=nullcontext,
            ),
        ):
            command.handle(
                verbosity=1,
                force=force,
                dry_run=dry_run,
                all=load_all,
                runids=runids,
            )

    def test_exhaustive_environment_and_flag_matrix(self):
        for environment, force, dry_run, load_all, has_runids in product(
            ("development", "test", "production"),
            (False, True),
            (False, True),
            (False, True),
            (False, True),
        ):
            runids = ["selected-run"] if has_runids else None
            rejected = (
                (load_all and has_runids)
                or (force and environment == "production")
                or (force and has_runids)
                or (force and not load_all)
            )
            label = (
                f"environment={environment} force={force} dry_run={dry_run} "
                f"all={load_all} runids={has_runids}"
            )

            if rejected:
                with self.subTest(label), self.assertRaises(CommandError):
                    self.execute(
                        environment=environment,
                        force=force,
                        dry_run=dry_run,
                        load_all=load_all,
                        runids=runids,
                        reject_before_query=True,
                    )
            else:
                with self.subTest(label):
                    self.execute(
                        environment=environment,
                        force=force,
                        dry_run=dry_run,
                        load_all=load_all,
                        runids=runids,
                    )

    @override_settings(APP_ENVIRONMENT="production")
    def test_production_force_rejects_before_database_query(self):
        command = Command(stdout=StringIO())
        with patch.object(Watershed.objects, "count") as count:
            with self.assertRaisesMessage(CommandError, "prohibited in production"):
                command.handle(
                    verbosity=1,
                    force=True,
                    dry_run=False,
                    all=True,
                    runids=None,
                )
        count.assert_not_called()

    @override_settings(APP_ENVIRONMENT="development")
    def test_safe_nonproduction_force_deletes_all_before_loading_all(self):
        events = []
        command = Command(stdout=StringIO())

        with (
            patch.object(Watershed.objects, "count", side_effect=(1, 0)),
            patch.object(Subcatchment.objects, "count", return_value=0),
            patch.object(Channel.objects, "count", return_value=0),
            patch.object(Watershed.objects, "all") as watersheds,
            patch.object(Subcatchment.objects, "all") as subcatchments,
            patch.object(Channel.objects, "all") as channels,
            patch(
                "server.watershed.management.commands.load_watershed_data.run",
                side_effect=lambda **kwargs: events.append("load"),
            ),
            patch(
                "server.watershed.management.commands.load_watershed_data.transaction.atomic",
                side_effect=nullcontext,
            ),
        ):
            channels.return_value.delete.side_effect = lambda: events.append("channels")
            subcatchments.return_value.delete.side_effect = lambda: events.append(
                "subcatchments"
            )
            watersheds.return_value.delete.side_effect = lambda: events.append(
                "watersheds"
            )
            command.handle(
                verbosity=1,
                force=True,
                dry_run=False,
                all=True,
                runids=None,
            )

        self.assertEqual(events, ["channels", "subcatchments", "watersheds", "load"])

    @override_settings(APP_ENVIRONMENT="unknown")
    def test_unknown_environment_rejects_before_database_query(self):
        command = Command(stdout=StringIO())
        with patch.object(Watershed.objects, "count") as count:
            with self.assertRaisesMessage(CommandError, "must explicitly identify"):
                command.handle(
                    verbosity=1,
                    force=False,
                    dry_run=True,
                    all=True,
                    runids=None,
                )
        count.assert_not_called()


class ProductionSilkConfigurationTests(SimpleTestCase):
    def test_production_disables_silk_app_middleware_and_url(self):
        project_root = Path(__file__).resolve().parents[2]
        environment = os.environ.copy()
        environment.update(
            APP_ENVIRONMENT="production",
            DJANGO_SECRET_KEY="db04-test-only",
            DJANGO_SETTINGS_MODULE="server.settings",
        )
        script = """
import django
django.setup()
from django.conf import settings
from django.urls import Resolver404, resolve
assert settings.SILK_ENABLED is False
assert 'silk' not in settings.INSTALLED_APPS
assert 'silk.middleware.SilkyMiddleware' not in settings.MIDDLEWARE
try:
    resolve('/silk/')
except Resolver404:
    pass
else:
    raise AssertionError('production Silk URL is enabled')
"""

        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=project_root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
