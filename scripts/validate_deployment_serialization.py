#!/usr/bin/env python3

from pathlib import Path
import json
import re


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIRECTORY = ROOT / ".github" / "workflows"
PRODUCTION_GROUP = "utility-watershed-analytics-production"


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def main():
    production_workflows = []
    groups = set()
    for path in sorted(WORKFLOW_DIRECTORY.glob("*.yml")):
        content = path.read_text(encoding="utf-8")
        if re.search(r"^\s*environment:\s*production\s*$", content, re.MULTILINE):
            production_workflows.append(path.relative_to(ROOT).as_posix())
            match = re.search(r"^\s*group:\s*([^\s#]+)", content, re.MULTILINE)
            require(match is not None, f"Production workflow lacks concurrency group: {path.name}")
            groups.add(match.group(1))
            require(
                re.search(r"^\s*cancel-in-progress:\s*false\s*$", content, re.MULTILINE),
                f"Production workflow may cancel an in-progress operation: {path.name}",
            )
    require(production_workflows, "No production workflow was found.")
    require(
        groups == {PRODUCTION_GROUP},
        "Production workflows do not share the canonical concurrency group.",
    )

    deploy = (ROOT / "scripts" / "deploy_application.sh").read_text(encoding="utf-8")
    configure = (ROOT / "scripts" / "configure_database_roles.sh").read_text(
        encoding="utf-8"
    )
    rotate = (ROOT / "scripts" / "rotate_database_credential.sh").read_text(
        encoding="utf-8"
    )
    entrypoint = (ROOT / "server" / "entrypoint.prod.sh").read_text(encoding="utf-8")
    workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(
        encoding="utf-8"
    )
    require("with_operation_lock.sh" in deploy, "Application deploy does not self-acquire the host lock.")
    require(
        deploy.count("require_operation_lock.sh") >= 3,
        "Application deploy does not reassert the host lock at mutation boundaries.",
    )
    require(
        "require_operation_lock.sh" in configure
        and "require_operation_lock.sh" in rotate,
        "Database role operations do not require the host lock.",
    )
    require(
        '--env-from-file "$migration_environment_file"' in deploy,
        "Migration does not use its separate credential file.",
    )
    require(
        "manage.py check_application_compatibility" in deploy,
        "Application compatibility is not checked before worker replacement.",
    )
    require(
        "migrate --check --noinput" in entrypoint,
        "Production startup does not fail on pending migrations.",
    )
    mutation_lines = [
        line
        for line in entrypoint.splitlines()
        if "manage.py migrate" in line and "--check" not in line
    ]
    require(not mutation_lines, "Production startup still executes migrations.")
    require(
        "PRODUCTION_MIGRATION_ENV" in workflow
        and ".env.production-migration" in workflow,
        "Production workflow does not deliver and clean the migration credential separately.",
    )
    print(
        json.dumps(
            {
            "status": "passed",
            "production_concurrency_group": PRODUCTION_GROUP,
            "production_workflows": production_workflows,
            "explicit_migration": True,
            "startup_migration_mutation": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
