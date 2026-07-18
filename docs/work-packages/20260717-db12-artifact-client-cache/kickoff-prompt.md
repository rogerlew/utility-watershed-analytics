# Kickoff prompt — DB12 artifact client and cache

Execute `package.md` on `agent/database-backup-deployment-spec` without commit,
push, production access, provider work, or real release data.

Follow the authoritative local `forest1:/wc1` design. Implement a standard-
library artifact client with streaming verified publication/fetch, exact
content keys, corruption-safe atomic cache behavior, concurrency safety, and
bounded cache-only cleanup. Run acceptance only in a temporary subtree of the
accepted test namespace and remove it afterward. Rebuild and audit the release-
tool image reproducibly, then record sanitized evidence and honest status.
