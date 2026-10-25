<!--
source-inventory.md
popo/docs

Copyright © 2026 Dagitali LLC. All rights reserved.

Committed source inventory formats, evidence scope and consumer adoption.

Maintainer Notes
- Keep source-only evidence distinct from dependency SBOMs and release approval.
- Preserve explicit revision selection and read-only consumer behavior.
-->

# Committed Source Inventories

Introduced in v0.10.0, this command generates evidence from a selected Git commit. It does not run
package manifests, rewrite consumer files, infer licensing, scan dependencies or approve a release.

- [Invocation](#invocation)
- [Revision and File Semantics](#revision-and-file-semantics)
- [Output Contracts](#output-contracts)
- [Errors and Limits](#errors-and-limits)
- [Consumer Adoption](#consumer-adoption)

## Invocation

```console
popo source-inventory --revision HEAD --name Example > source-inventory.json
popo source-inventory --revision v1.0.0 --name Example --format spdx > source.spdx.json
```

`--root` selects the top-level working tree (default current directory). `--revision` is required;
`--name` defaults to `Source` and must be nonblank single-line text. `--format` accepts `json`
(default) or `spdx`. Both formats use the same committed blobs. This command is separate from
`check-all`, profiles and native check-result JSON; it emits the evidence document itself.

## Revision and File Semantics

Resolve the revision once to a full commit ID, then read that commit's complete tree and batch-read
blobs by object ID. Staged edits, unstaged changes, untracked files and checkout deletions do not
change evidence. Git replacement objects are disabled and inherited Git repository-selection
environment overrides are cleared. Annotated/lightweight tags resolving to a commit are accepted;
missing objects, trees and option-like invalid revisions fail.

Regular and executable files are included. Symlinks are inventoried as their committed link text,
never followed; plain JSON retains the Git mode. Gitlinks/submodules fail rather than silently
claiming their contents were inventoried. No LFS filter runs: an LFS pointer is the committed blob,
not its external payload. Paths must decode as UTF-8, including spaces, tabs and newlines. Invalid
UTF-8 paths fail rather than being replaced or omitted. Empty trees and nested roots fail.

## Output Contracts

Plain JSON uses schema version one, `kind: source-inventory`, the consumer name, resolved
`revision`, `scope: committed-blobs` and sorted `files` with `path`, `mode` and SHA-256. For the
same name and commit, this format is reproducible and does not include source contents or wall-clock
metadata.

SPDX JSON uses version 2.3 with a source package and file relationships, path-derived unique file
identifiers, SHA-1/SHA-256 checksums and a package verification code calculated from sorted file
SHA-1 values. License and copyright fields use `NOASSERTION`; the SPDX document's CC0 data-license
field does not license consumer source. Each generation has a fresh namespace UUID and current UTC
creation time, so the complete SPDX document is intentionally not byte-for-byte reproducible. See
the [SPDX verification rules] and [namespace rules].

Neither format inventories linked frameworks, transitive dependencies, installed packages or a
compiled product. Paths and hashes can reveal repository metadata; review evidence before sharing.

## Errors and Limits

Success returns zero and one complete JSON document on stdout. Collection/rendering errors return
one, a diagnostic on stderr and no partial evidence on stdout; argument errors retain argparse's
status two. Shell redirection creates output files and may leave an empty file after failure.
Consumers must propagate exit statuses and publish evidence only after successful generation.

Git must be installed. Bare repositories are unsupported. Git commands are local-only with a
120-second timeout per invocation; blobs are batch-read into memory, so very large repositories can
require substantial memory. Git error streams and source contents are omitted from failure messages.
Checksums establish identity, not authenticity or correctness. No network fetch is performed and
unavailable objects remain failures.

## Consumer Adoption

Use v0.10.0 or later and pin an immutable revision containing the command. Compare both formats
against independent committed-byte fixtures before removing local generators. Keep native release
identity, signing and readiness policies separate. Use the same resolved commit for these reports
and the source archive. Existing worktree-hash inventories change semantics when adopting
committed-only output; update consumers rather than silently treating the formats as identical.

[namespace rules]: https://spdx.github.io/spdx-spec/v2.3.1/document-creation-information/#65-spdx-document-namespace-field
[SPDX verification rules]: https://spdx.github.io/spdx-spec/v2.3.1/package-information/#79-package-verification-code-field
