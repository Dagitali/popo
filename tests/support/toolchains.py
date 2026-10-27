"""
:mod:`tests.support.toolchains` module.

Provide isolated Swift toolchain declarations without executing Swift.
"""

from pathlib import Path

import pytest

from tests.support.files import FileWriter

# SECTION: FIXTURES


@pytest.fixture(name='swift_policy_consumer')
def swift_policy_consumer_fixture(
    tmp_path: Path,
    write_file: FileWriter,
) -> Path:
    """Prepare independent local, manifest and scoped CI declarations.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Per-test consumer root; no Python project metadata is created.
    write_file : FileWriter
        UTF-8 fixture writer shared by unit, CLI and installed-command tests.

    Returns
    -------
    pathlib.Path
        Root with explicit stable compiler policy. The manifest body would fail
        if executed; only its first-line tools declaration may be inspected.
    """
    write_file(
        'popo.toml',
        """[swift-policy]
compiler-versions = ["6.1.2", "6.2.0"]
preferred-version = "6.1.2"
tools-version = "5.9"
workflow-globs = [".github/workflows/ci.yml"]
""",
    )
    write_file('.swift-version', '6.1.2\n')
    write_file(
        'Package.swift',
        '// swift-tools-version: 5.9\nfatalError("must not execute")\n',
    )
    write_file(
        '.github/workflows/ci.yml',
        """name: Swift
on: [push]
jobs:
  swift:
    strategy:
      matrix:
        swift: ["6.1.2", "6.2.0"]
    steps:
      - uses: ./fixture-setup
        with:
          swift-version: ${{ matrix.swift }}
""",
    )
    return tmp_path


#!SECTION
