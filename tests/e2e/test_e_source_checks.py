"""
:mod:`tests.e2e.test_e_source_checks` module.

Validate installed source checks with synthetic consumers outside checkout.
"""

import json
from pathlib import Path
from typing import Self

import pytest

from tests.support.files import snapshot_files
from tests.support.installation import Installation

# SECTION: TESTS


class TestInstalledSourceChecks:
    """Exercise wheel/sdist console and module entry points without mutation."""

    @pytest.mark.parametrize('module', (False, True), ids=('console', 'module'))
    @pytest.mark.parametrize(
        'command,domain,filename,options,valid,invalid',
        (
            (
                'check-python-source',
                'python-source',
                'rule.py',
                'annotations = true\nparameter-docs=true\nreturn-docs=true\n'
                'source-guide="Guide.md"',
                'def f(value: int) -> int:\n'
                '    """Return an item.\n\n'
                '    Parameters\n    ----------\n    value : int\n'
                '        Input.\n\n    Returns\n    -------\n    int\n'
                '        Item.\n    """\n    return value\n',
                'def f(value: int) -> int: return value',
            ),
            (
                'check-swift-source',
                'swift-source',
                'Rule.swift',
                'member-docs=true\nparameter-docs=true\nreturn-docs=true\n'
                'raises-docs=true\nsource-guide="Guide.md"',
                '/// Overview.\n/// - Parameter value: Input.\n'
                '/// - Returns: Result.\n/// - Throws: Invalid input.\n'
                'func f(value: Int) throws -> Int { value }',
                '/// Overview.\nfunc f(value: Int) throws -> Int { value }',
            ),
            (
                'check-logs',
                'logs',
                'console.log',
                'patterns = { warning = "WARNING" }',
                'Normal startup',
                'WARNING: PRIVATE SYNTHETIC BALANCE',
            ),
        ),
    )
    def test_installed_source_and_log_commands(
        self: Self,
        installation: Installation,
        tmp_path: Path,
        module: bool,
        command: str,
        domain: str,
        filename: str,
        options: str,
        valid: str,
        invalid: str,
    ) -> None:
        """
        Require inputs, reject policy violations and preserve consumer files.

        Parameters
        ----------
        installation : Installation
            Installed wheel or sdist outside the source checkout.
        tmp_path : pathlib.Path
            Disposable consumer policy and input root.
        module : bool
            Select the installed module or console entry point.
        command, domain, filename, options : str
            Explicit command and consumer policy for one validation domain.
        valid, invalid : str
            Synthetic positive and negative source or artifact contents.
        """
        (tmp_path / 'popo.toml').write_text(
            f'[{domain}]\ninclude = ["{filename}"]\n{options}',
        )
        (tmp_path / 'Guide.md').write_text(f'`{filename}`', encoding='utf-8')
        source = tmp_path / filename
        for content, status in ((None, 1), (invalid, 1), (valid, 0)):
            if content is not None:
                source.write_text(content)
            before = snapshot_files(tmp_path)
            result = installation.run(
                command,
                '--root',
                str(tmp_path),
                '--format',
                'json',
                module=module,
            )
            assert result.returncode == status, result.stderr
            assert json.loads(result.stdout)['passed'] == (status == 0)
            assert 'PRIVATE SYNTHETIC BALANCE' not in result.stdout + result.stderr
            assert snapshot_files(tmp_path) == before


# !SECTION
