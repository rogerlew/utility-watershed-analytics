#!/usr/bin/env python3

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
PRODUCTION_GROUP = "utility-watershed-analytics-production"


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def workflow(name):
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def trigger_block(content):
    match = re.search(r"(?ms)^on:\n(.*?)(?=^[a-zA-Z][^\n]*:\n)", content)
    require(match is not None, "Workflow trigger block is missing.")
    return match.group(1)


def main():
    prepare = workflow("data-release-prepare.yml")
    deploy = workflow("data-release-deploy.yml")
    rollback = workflow("data-release-rollback.yml")
    status = workflow("data-release-status.yml")

    for name, content in (("deploy", deploy), ("rollback", rollback)):
        triggers = trigger_block(content)
        require("workflow_dispatch:" in triggers, f"{name} is not manually dispatched.")
        require(
            not re.search(r"(?m)^  (push|pull_request|schedule):", triggers),
            f"{name} can be triggered without a manual protected action.",
        )
        require(
            f"group: {PRODUCTION_GROUP}" in content and "cancel-in-progress: false" in content,
            f"{name} does not share the non-cancelling production serialization group.",
        )
        for protected_input in (
            "preparation_run_id",
            "artifact_name",
            "authorization_sha256",
            "operation_id",
            "source_commit",
        ):
            require(
                re.search(rf"(?m)^      {protected_input}:$", triggers),
                f"{name} lacks protected input {protected_input}.",
            )
        require("actions/download-artifact@v4" in content, f"{name} does not download a prepared bundle.")
        require("scripts/release_authorization.py verify" in content, f"{name} does not verify authorization.")
        require("systemctl start" in content, f"{name} bypasses DB26 durable execution.")
        require("if: always()" in content and "upload-artifact@v4" in content, f"{name} does not retain failed reports.")
        require("secrets." not in content, f"{name} copies a repository secret instead of using installed credentials.")

    require("environment: production-data-deploy" in deploy, "Deploy environment is not protected distinctly.")
    require("--action deploy" in deploy and "--action rollback" not in deploy, "Deploy accepts the wrong action.")
    require("environment: production-data-rollback" in rollback, "Rollback environment is not distinct.")
    require("--action rollback" in rollback and "--action deploy" not in rollback, "Rollback accepts the wrong action.")

    prepare_triggers = trigger_block(prepare)
    require("workflow_dispatch:" in prepare_triggers, "Preparation is not explicit.")
    require("environment:" not in prepare, "Preparation can access a protected production environment.")
    require("self-hosted" not in prepare, "Preparation runs on a production-capable runner.")
    require("secrets." not in prepare, "Preparation reads repository secrets.")
    require("server-ci.yml" in prepare and "data-contract-ci.yml" in prepare, "Preparation omits CI gates.")
    require("scripts/release_authorization.py prepare" in prepare, "Preparation omits immutable bundling.")
    require("upload-artifact@v4" in prepare and "retention-days: 90" in prepare, "Preparation bundle is not retained.")

    status_triggers = trigger_block(status)
    require("workflow_dispatch:" in status_triggers and "schedule:" in status_triggers, "Status monitoring is not scheduled and manual.")
    require("environment:" not in status and "secrets." not in status, "Status monitoring has mutation credentials.")
    require("systemctl" not in status and "sudo " not in status, "Status monitoring can mutate the host.")
    require("check_database_release_status.py" in status, "Status workflow omits deterministic reconciliation.")
    require("if: always()" in status and "upload-artifact@v4" in status, "Status failures do not retain reports.")

    application_deploy = workflow("deploy.yml")
    require(
        "scripts/deploy_database.sh" not in application_deploy
        and "utility-watershed-analytics-database-deploy@" not in application_deploy,
        "Merging application code can deploy watershed data.",
    )
    print(json.dumps({
        "status": "passed",
        "prepare_environment": None,
        "deploy_environment": "production-data-deploy",
        "rollback_environment": "production-data-rollback",
        "production_concurrency_group": PRODUCTION_GROUP,
        "merge_deploys_data": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
