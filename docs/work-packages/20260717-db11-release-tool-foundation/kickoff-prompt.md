# Kickoff prompt — DB11 release-tool foundation

Execute `package.md` on `agent/database-backup-deployment-spec` without commit,
push, production access, registry publication, or real release data.

Implement all eight stable command entry points, but fail future-owned behavior
explicitly rather than pretending it works. Build from the repository root,
copy only code into the image, pin the base digest, build twice, audit image
contents, and run verified read-only input by immutable local image ID. Record
sanitized evidence and close the package only when every applicable gate passes.
