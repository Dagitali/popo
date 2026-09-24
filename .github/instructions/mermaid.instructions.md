---
applyTo: "**/*.mmd,**/*.mermaid,**/*.md"
---
<!--
mermaid.instructions.md
popo

Copyright © 2026 Dagitali LLC. All rights reserved.

Portable guidance for Mermaid diagrams and optional editor integrations.

Responsibilities
- Keep diagrams grounded in repository evidence and editable as plain text.
- Validate syntax and inspect rendered output when tooling is available.
- Preserve privacy, paid-feature consent, and externally managed diagram ownership.

Maintainer Notes
- Keep frontmatter first so instruction discovery continues to work.
- Keep the file scope focused on diagrams and Markdown, not every source file.
- Treat extension commands as optional examples, not contributor prerequisites.
- Verify command availability before use; do not install or update tools implicitly.
-->

# Mermaid Diagrams

Use diagrams when they clarify a relationship better than prose. Match the diagram
to repository evidence and keep labels language- and platform-neutral where possible.
Follow the repository's agent instructions; this file does not authorize external operations.

## Workflow

1. Determine the diagram type and generate Mermaid syntax.
2. Write editable source to a Markdown Mermaid fence, `.mmd`, or `.mermaid` file.
   Preserve the existing location and format when updating a diagram.
3. Validate syntax: correct first-line keyword, arrow types, labels, and balanced brackets.
   Consult current syntax documentation for unfamiliar diagram types.
4. Preview with available local Mermaid tooling and inspect layout, readability, and
   agreement with the source. If validation or rendering is unavailable, state exactly
   what was not verified; never claim a successful check that was not performed.
5. Keep source-controlled diagrams usable without a cloud account or paid extension.

## Tool Selection

Use an available local validator or renderer first. The integrations below retain the
source repository's optional capabilities; equivalent tools are acceptable. Named tools
must actually be exposed in the active environment before an agent can call them.

Do not upload repository content, authenticate or connect cloud services, enable
synchronization, install extensions, or use paid AI features without authorization.
Mermaid Chart features may require an account even for preview; use an account-free
local alternative when that integration is unavailable or unwanted.

## Optional Mermaid Chart Tools

- `mermaid-diagram-validator` — validate Mermaid syntax before presenting any diagram
- `mermaid-diagram-preview` — render a live preview inside VS Code after generating
- `get-syntax-docs-mermaid` — fetch correct syntax docs for any diagram type

## Optional VS Code Commands

Use these only when the extension is installed, authorized, and the commands are available.
Invoke through the Command Palette or an exposed VS Code command API; do not invent command IDs.
Prefer editing `.mmd` files when a command is not needed. Account and feature availability vary
by extension version; check current documentation before relying on them.

### Diagram Editing and Preview

- **Preview** (`mermaidChart.preview`) — preview the active Mermaid editor (`.mmd` or `.mermaid`
  must be open).
- **Create Diagram** (`mermaidChart.createMermaidFile`) — create a demo flowchart and open its
  preview side by side.
- **Repair Diagram** (`mermaidChart.repairDiagram`) — use Mermaid AI to repair the active diagram;
  obtain authorization before consuming Mermaid AI credits.
- **Improve Diagram** (`mermaidChart.improveDiagram`) — use Copilot or the LM API to suggest layout
  and styling variants.

### Generate Diagrams (GitHub Copilot Required)

- **Generate Diagram from Code** (`mermaidChart.generateDiagramFromCode`)
- **Generate Cloud Diagram** (`mermaidChart.generateCloudDiagram`)
- **Generate ER Diagram** (`mermaidChart.generateERDiagram`)
- **Generate Docker Diagram** (`mermaidChart.generateDockerDiagram`)
- **Open AI Chat** (`mermaidChart.openCopilotChat`)

### Mermaid Chart Cloud

- **Login** (`mermaidChart.login`) or **Logout** (`mermaidChart.logout`)
- **Connect Diagram** (`mermaidChart.connectDiagramToMermaidChart`) — link a local diagram to
  Mermaid Chart.
- **Sync Diagram** (`mermaidChart.syncDiagramWithMermaid`) — use only for diagrams already
  connected through frontmatter containing an `id`.

### Review Mermaid Sync

- **Review Mermaid Sync** (`mermaidChart.reviewAppCommits`) — start or open the review flow.
- **Regenerate with Mermaid AI** (`mermaidChart.regenerateDiagramWithMermaidAI`) — regenerate from
  source references.

Do not manually rewrite diagrams managed by the Mermaid Chart GitHub Sync workflow. Accept, reject,
and diff actions remain in the extension UI.

### Install or Update This Pack

- **MermaidChart: Install AI Skills…** (`mermaidChart.installAiSkills`) — only when requested;
  review the generated diff and preserve these portable repository instructions.

## Optional `@mermaid-chart` Slash Commands

| Command | Purpose |
| --- | --- |
| `/generate_diagram_from_code` | General diagram from any source file |
| `/generate_execution_sequence` | Sequence diagram from code flow |
| `/generate_er_diagram` | ER diagram from schema or models |
| `/generate_cloud_architecture_diagram` | Cloud or CI/CD architecture |
| `/generate_docker_diagram` | Architecture from Dockerfiles |
| `/generate_c4_topdown_architecture` | C4 top-down architecture |
| `/analyze_code_ownership` | Code ownership diagram |
| `/generate_dependency_diagram` | Dependency or security visualization |

## Rules

1. Validate syntax and preview when suitable tools are available; report any skipped check.
2. Use current Mermaid syntax documentation before generating unfamiliar diagram types.
3. Choose diagram types for the question: flow, sequence, ER, C4, ownership, dependency,
   cloud, and container diagrams are options, not requirements or platform assumptions.
4. Keep diagram sources editable and preserve existing Markdown references.
5. Obtain authorization before Repair, generation, or other operations that send content
   externally or consume paid credits. Explain the relevant data and cost implications.
6. Do not manually overwrite diagrams owned by an external synchronization workflow.
   Use its established review mechanism; if ownership or workflow is unclear, ask first.
7. Use cloud sync only for already connected diagrams with the expected connection metadata.
   Do not reconnect, upload, or regenerate a managed diagram merely to update documentation.

## Documentation

See the [Mermaid syntax reference] and [Mermaid Chart extension documentation].
The extension reference is optional; it does not establish a repository dependency.

[Mermaid Chart extension documentation]: https://marketplace.visualstudio.com/items?itemName=MermaidChart.vscode-mermaid-chart
[Mermaid syntax reference]: https://mermaid.js.org/intro/syntax-reference.html
