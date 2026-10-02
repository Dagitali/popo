"""
:mod:`tests.meta.test_m_package_artifacts` module.

Verify public distribution content and entry-point contracts.
"""

import configparser
import tarfile
from email.parser import BytesParser
from pathlib import Path
from zipfile import ZipFile

from packaging.requirements import Requirement

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

    def test_distribution_contract(
        self,
        artifact: Path,
    ) -> None:
        """
        Verify wheel and sdist contents, metadata, typing, and entry-point
        contracts.

        Parameters
        ----------
        artifact : pathlib.Path
            Wheel or sdist selected by the shared artifact fixture.
        """
        if artifact.suffix == '.whl':
            with ZipFile(artifact) as archive:
                names = set(archive.namelist())
                assert {
                    'popo/__init__.py',
                    'popo/__main__.py',
                    'popo/cli.py',
                    'popo/py.typed',
                    'popo/checks/automation.py',
                } <= names
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
                names = set(archive.getnames())
                roots = {name.split('/')[0] for name in names}
                assert len(roots) == 1, roots
                root = roots.pop()
                assert {f'{root}/pyproject.toml', f'{root}/src/popo/py.typed'} <= names
                member = f'{root}/PKG-INFO'
                stream = archive.extractfile(member)
                assert stream is not None
                with stream:
                    metadata = stream.read()
        prefix = 'popo/' if artifact.suffix == '.whl' else f'{root}/src/popo/'
        assert {
            f'{prefix}config/{filename}'
            for filename in (
                '__init__.py',
                '_common.py',
                'project.py',
                'dependencies.py',
                'python_policy.py',
                'automation.py',
            )
        } <= names
        assert f'{prefix}config.py' not in names
        assert f'{prefix}automation_config.py' not in names
        assert {'LICENSE', 'NOTICE'} <= {name.rsplit('/', 1)[-1] for name in names}
        parsed = BytesParser().parsebytes(metadata)
        assert parsed['Name'] == 'popo'
        assert parsed['Summary'] == 'Reusable repository policy and consistency checks'
        assert (
            'Documentation, https://github.com/Dagitali/popo/tree/main/docs'
            in parsed.get_all('Project-URL', [])
        )
        assert parsed['License-Expression'] == 'MIT'
        assert set(parsed['Requires-Python'].split(',')) == {'>=3.13', '<3.15'}
        runtime_dependencies = {
            Requirement(value).name.lower()
            for value in parsed.get_all('Requires-Dist', [])
            if 'extra ==' not in value
        }
        assert {'packaging', 'pyyaml'} <= runtime_dependencies


# !SECTION
