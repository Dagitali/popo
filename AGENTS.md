# AGENTS

These instructions apply to automated coding agents working in this repository.

- Treat `pyproject.toml` as the canonical package and tool configuration.
- Preserve the `src/` layout and keep the public API intentionally small.
- Keep checks read-only: commands may inspect repositories but must not modify them.
- Keep generic checking logic separate from any one consumer repository's policy.
- Add or update tests whenever command behavior or configuration changes.
- Organize tests by unit, integration, meta, and e2e scope; keep shared fixtures in tests/support.
  Default checks run unit and integration tests; artifact layers are opt-in.
- Use single-quoted Python strings, an 88-character line length, and strict typing.
- Run `make check` before completion when practical.
- Update `README.md` and `CHANGELOG.md` for user-visible changes.
- Do not publish packages, create release tags, or mutate external repositories without explicit
  authorization.
