<!--
README.md
popo/examples

Copyright © 2026 Dagitali LLC. All rights reserved.

Self-contained consumer examples sharing one local and CI guardrail contract.

Maintainer Notes
- Keep each example independently copyable, including hidden files.
- Reuse acceptance tests without erasing consumer-owned policy differences.
-->

# Consumer Examples

Copy one directory, including its hidden files, to a disposable repository root. Each example owns
one `popo.toml` profile and delegates Make, pre-commit and CI to `make guardrails`. None depends on
neighboring examples, Popo's source tree, or Popo's contributor Makefile. Tool-installation inputs
are shared between local setup and that consumer's CI workflow.

| Example | Additional policy | Separate application command |
| --- | --- | --- |
| [CDK] | Exact Python CDK dependency pins and declared Python/tool consistency | Install app dependencies, then `make test` or `make synth` |
| [Python] | Dependency minimum constraints and declared Python/tool consistency | Install the package, then `make test` |
| [Swift] | Language-neutral documentation, required files, action pins and parity | `make test` compiles the Swift package |

All examples use explicit `popo check-all --profile guardrails` selection. Bare `check-all` retains
legacy defaults; it does not automatically select a named profile. Runtime Python must satisfy both
Popo and the selected consumer policy. Each README documents local setup, drift exercises and its
execution boundaries. The CDK example uses Python; no AWS credentials or deployment are required.

Parameterized acceptance tests copy each consumer and verify real Make, installed Git-hook and
workflow-command execution against installed wheels and sdists. They detect Make recipe, hook
argument, CI invocation and working-directory drift, plus shared Markdown failures. Deterministic
integration tests exercise the same inputs through the public CLI. Application tests and CDK
synthesis are separate from Popo's read-only guardrail execution.

These are POSIX examples requiring Git, Make and an installed supported Python runtime. Windows
retains Popo's native CLI coverage; these example execution tests are skipped there. Local command
execution does not establish hosted workflow success, branch enforcement or publication.

[CDK]: cdk/README.md
[Python]: python/README.md
[Swift]: swift/README.md
