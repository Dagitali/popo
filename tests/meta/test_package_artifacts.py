"""
:mod:`tests.meta.test_package_artifacts` module.

Verify public distribution content and entry-point contracts.
"""

import configparser
import tarfile
from email.parser import BytesParser
from pathlib import Path
from zipfile import ZipFile

# SECTION: TESTS


class TestPackageArtifacts:
    """
    Verify package artifacts contracts.

    Notes
    -----
    Inspect wheel and sdist contents, metadata, licensing, configuration
    modules, typing markers, and the wheel console entry point. Shared fixtures
    select validated artifacts; archive inspection does not extract them into
    the checkout.
    """

    def test_distribution_contract(self, artifact: Path) -> None:
        """
        Verify wheel and sdist contents, metadata, typing, and entry-point
        contracts.

        Parameters
        ----------
        artifact : pathlib.Path
            Built wheel or source distribution selected by the shared artifact
            fixture.
        """
        if artifact.suffix == '.whl':
            with ZipFile(artifact) as archive:
                names = archive.namelist()
                for filename in (
                    '__init__.py',
                    '__main__.py',
                    'cli.py',
                    'py.typed',
                    'checks/automation.py',
                ):
                    assert f'popo/{filename}' in names
                metadata = archive.read(
                    next(n for n in names if n.endswith('/METADATA')),
                )
                entries = archive.read(
                    next(n for n in names if n.endswith('/entry_points.txt')),
                ).decode()
                parser = configparser.ConfigParser()
                parser.read_string(entries)
                assert parser['console_scripts']['popo'] == 'popo.cli:main'
        else:
            with tarfile.open(artifact, 'r:gz') as archive:
                names = archive.getnames()
                for suffix in ('/pyproject.toml', '/src/popo/py.typed'):
                    assert any(n.endswith(suffix) for n in names)
                member = min(
                    (n for n in names if n.endswith('/PKG-INFO')),
                    key=len,
                )
                stream = archive.extractfile(member)
                assert stream is not None
                with stream:
                    metadata = stream.read()
        prefix = (
            'popo/'
            if artifact.suffix == '.whl'
            else names[0].split('/')[0] + '/src/popo/'
        )
        for filename in (
            '__init__.py',
            '_common.py',
            'project.py',
            'dependencies.py',
            'python_policy.py',
            'automation.py',
        ):
            assert f'{prefix}config/{filename}' in names
        assert f'{prefix}config.py' not in names
        assert f'{prefix}automation_config.py' not in names
        for filename in ('LICENSE', 'NOTICE'):
            assert any(n.endswith('/' + filename) for n in names)
        parsed = BytesParser().parsebytes(metadata)
        assert parsed['Name'] == 'popo'
        assert parsed['Summary'] == 'Reusable repository policy and consistency checks'
        assert (
            'Documentation, https://github.com/Dagitali/popo/tree/main/docs'
            in parsed.get_all('Project-URL', [])
        )
        assert parsed['License-Expression'] == 'MIT'
        assert set(parsed['Requires-Python'].split(',')) == {'>=3.13', '<3.15'}
        assert any(
            r.startswith('packaging') for r in parsed.get_all('Requires-Dist', [])
        )
        assert any(
            r.lower().startswith('pyyaml') and 'extra ==' not in r
            for r in parsed.get_all('Requires-Dist', [])
        )


# !SECTION
