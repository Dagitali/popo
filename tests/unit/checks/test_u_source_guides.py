"""
:mod:`tests.unit.checks.test_u_source_guides` module.

Verify exact selected-path matching and read-only source-guide diagnostics.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from popo.checks._source_documentation import guide_findings
from popo.config.source_checks import SourceCheckConfig
from tests.support.files import FileWriter, snapshot_files
from tests.support.source_checks import SourceCase

# SECTION: TESTS


class TestSourceGuides:
    """Keep guide matching independent of native source syntax and contents."""

    @pytest.mark.parametrize(
        'selected,entries,missing',
        [
            (
                ('a/source', 'b/source'),
                ('unrelated', 'a/source', 'b/source', 'later'),
                (),
            ),
            (
                ('nested/source',),
                ('source', 'other/nested/source', 'nested/source.extra'),
                ('nested/source',),
            ),
            (
                ('z/source', 'a/source', 'z/source'),
                ('a/source', 'unrelated', 'a/source'),
                ('z/source', 'z/source'),
            ),
            (('a/source',), (), ('a/source',)),
            ((), ('unrelated',), ()),
        ],
        ids=(
            'all-present',
            'exact-paths',
            'duplicate-missing',
            'empty-guide',
            'no-inputs',
        ),
    )
    def test_selected_entries_preserve_exact_paths_and_order(
        self,
        tmp_path: Path,
        source_case: SourceCase,
        write_file: FileWriter,
        selected: tuple[str, ...],
        entries: tuple[str, ...],
        missing: tuple[str, ...],
    ) -> None:
        """
        Match exact spans without reading source files or changing the guide.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated consumer root containing the guide alone.
        source_case : SourceCase
            Python or Swift domain supplied by the shared language fixture.
        write_file : FileWriter
            Writer creating the guide without creating selected source files.
        selected : tuple[str, ...]
            Ordered relative paths, including intentional duplicate selections.
        entries : tuple[str, ...]
            Backticked paths mixed with unrelated guide entries.
        missing : tuple[str, ...]
            Missing paths in required diagnostic order, retaining duplicates.
        """
        domain, _, _ = source_case
        write_file('Guide.md', '\n'.join(f'`{entry}`' for entry in entries))
        config = SourceCheckConfig(
            tmp_path,
            domain,
            (),
            (),
            {'source-guide': 'Guide.md'},
        )
        before = snapshot_files(tmp_path)
        assert guide_findings(config, [tmp_path / name for name in selected]) == [
            f'{name}: missing source-guide entry' for name in missing
        ]
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        'failure',
        ('missing', 'directory', 'decode', 'permission'),
    )
    @pytest.mark.parametrize(
        'selected',
        (False, True),
        ids=('no-sources', 'selected-source'),
    )
    def test_unreadable_guide_is_reported_for_every_selection(
        self,
        tmp_path: Path,
        source_case: SourceCase,
        failure: str,
        selected: bool,
    ) -> None:
        """
        Keep guide read failures visible regardless of source selection.

        Empty selections still require a readable guide. Selected source files
        must not be opened while checking guide entries or read failures.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated consumer root containing the guide failure scenario.
        source_case : SourceCase
            Python or Swift domain supplied by the shared language fixture.
        failure : str
            Missing guide, directory, invalid UTF-8 or denied read.
        selected : bool
            Whether to select an unreadable native source as a read guard.
        """
        domain, filename, _ = source_case
        guide = tmp_path / 'Guide.md'
        if failure == 'directory':
            guide.mkdir()
        elif failure != 'missing':
            guide.write_bytes(b'PRIVATE\xff' if failure == 'decode' else b'PRIVATE')
        paths = [tmp_path / filename] if selected else []
        for path in paths:
            path.write_bytes(b'PRIVATE SOURCE\xff')
        config = SourceCheckConfig(
            tmp_path,
            domain,
            (),
            (),
            {'source-guide': 'Guide.md'},
        )
        before = snapshot_files(tmp_path)
        read = Path.read_text
        with patch.object(
            Path,
            'read_text',
            autospec=True,
            side_effect=PermissionError('PRIVATE READ')
            if failure == 'permission'
            else read,
        ) as reader:
            assert guide_findings(config, paths) == [
                'Guide.md: cannot read UTF-8 input',
            ]
        reader.assert_called_once_with(guide, encoding='utf-8')
        assert snapshot_files(tmp_path) == before


# !SECTION
