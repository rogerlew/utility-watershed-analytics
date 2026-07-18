# DB17 kickoff prompt

Execute `package.md` exactly as authorized.

Start from `319bf717d570cb42356ef5e4b88f90e60c612ba2`. Implement strict
standalone and batch preparation in the code-only release tool, reuse DB12's
forest1-backed artifact client, and make DB11's `prepare` command available.
Use only synthetic public fixtures and the isolated artifact test namespace.

Do not inspect or mutate `wepp3`, use production data or credentials, publish
to the production artifact namespace, modify the legacy runtime loader, or
commit/push DB17. Stop rather than infer a stable identity or silently skip a
required input.
