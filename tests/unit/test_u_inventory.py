"""
:mod:`tests.unit.test_u_inventory` module.

Validate committed source identity, checksums, containment and failure
behavior.
"""

import hashlib
import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest

from popo import inventory
from popo.cli import main
from tests.support.files import snapshot_files
from tests.support.inventory import git, repository

# SECTION: CONSTANTS


GIT_FAILURE_FACTORIES = [
    pytest.param(lambda: OSError('private diagnostic'), id='launch'),
    pytest.param(lambda: subprocess.TimeoutExpired('git', 120), id='timeout'),
]


# !SECTION


# SECTION: TESTS


class TestSourceInventory:
    """
    Cover source inventory.

    Exercise inventory semantics using isolated Git objects and CLI output.
    """

    @pytest.mark.parametrize('format_', ['json', 'spdx'])
    def test_committed_bytes_and_read_only_cli(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        format_: str,
    ) -> None:
        """
        Keep worktree/index edits out of both formats without modifying files.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable root for synthetic Git objects and checkout edits.
        capsys : pytest.CaptureFixture[str]
            Captured public CLI output, including failure channels.
        format_ : str
            Selected plain JSON or source-only SPDX representation.
        """
        commit = repository(tmp_path)
        before = snapshot_files(tmp_path)
        assert (
            main(
                [
                    'source-inventory',
                    '--root',
                    str(tmp_path),
                    '--revision',
                    'fixture-tag',
                    '--name',
                    'Example',
                    '--format',
                    format_,
                ],
            )
            == 0
        )
        captured = capsys.readouterr()
        assert captured.err == ''
        report = json.loads(captured.out)
        assert len(report['files']) == 2
        if format_ == 'json':
            assert report['revision'] == commit
            assert report['scope'] == 'committed-blobs'
            assert (
                report['files'][1]['sha256']
                == hashlib.sha256(b'committed\n').hexdigest()
            )
        else:
            assert report['spdxVersion'] == 'SPDX-2.3'
            assert commit in report['comment']
            assert 'documentComment' not in report
            assert len({f['SPDXID'] for f in report['files']}) == 2
            assert (
                report['files'][1]['checksums'][1]['checksumValue']
                == hashlib.sha256(b'committed\n').hexdigest()
            )
            hashes = [
                hashlib.sha1(b, usedforsecurity=False).hexdigest()
                for b in (b'committed\n', b'\x00\xff\nblob')
            ]
            payload = ''.join(sorted(hashes)).encode()
            expected = hashlib.sha1(payload, usedforsecurity=False).hexdigest()
            assert (
                report['packages'][0]['packageVerificationCode'][
                    'packageVerificationCodeValue'
                ]
                == expected
            )
            assert report['packages'][0]['licenseDeclared'] == 'NOASSERTION'
            assert len(report['relationships']) == 3
        assert snapshot_files(tmp_path) == before

    def test_empty_commit_is_not_an_inventory(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Fail clearly for commits without inventoried file entries.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable root for synthetic Git objects and checkout edits.
        """
        git(tmp_path, 'init', '--template=')
        git(tmp_path, 'commit', '--allow-empty', '-m', 'Empty fixture')
        with pytest.raises(ValueError, match='no source files'):
            inventory.collect(tmp_path, 'HEAD')

    @pytest.mark.parametrize('error_factory', GIT_FAILURE_FACTORIES)
    def test_git_errors(
        self,
        tmp_path: Path,
        error_factory: Callable[[], Exception],
    ) -> None:
        """
        Hide private diagnostics while retaining command identity.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable root for synthetic Git objects and checkout edits.
        error_factory : collections.abc.Callable[[], Exception]
            Fresh launch or timeout error with private diagnostic text;
            exception traceback state is not shared between invocations.
        """
        with (
            patch.object(inventory.subprocess, 'run', side_effect=error_factory()),
            pytest.raises(ValueError, match='could not run local Git rev-parse'),
        ):
            inventory.collect(tmp_path, 'HEAD')

    def test_gitlinks_are_rejected(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Do not represent a submodule commit as fully inventoried source.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable root for synthetic Git objects and checkout edits.
        """
        commit = repository(tmp_path)
        git(
            tmp_path,
            'update-index',
            '--add',
            '--cacheinfo',
            '160000',
            commit,
            'dependency',
        )
        git(tmp_path, 'commit', '-m', 'Synthetic gitlink')
        with pytest.raises(ValueError, match='submodules'):
            inventory.collect(tmp_path, 'HEAD')

    @pytest.mark.parametrize('name', ['', ' ', 'two\nlines', 'null\0name'])
    def test_invalid_project_name(
        self,
        tmp_path: Path,
        name: str,
    ) -> None:
        """
        Reject names that cannot be represented as single-line SPDX metadata.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable root for synthetic Git objects and checkout edits.
        name : str
            Invalid single-line metadata value selected by the fixture.
        """
        with pytest.raises(ValueError, match='name'):
            inventory.document(tmp_path, 'HEAD', name, 'json')

    @pytest.mark.parametrize('revision', ['missing', '--help', 'HEAD:no-file'])
    def test_invalid_revision_has_no_partial_json(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        revision: str,
    ) -> None:
        """
        Reject invalid revisions without emitting partial evidence.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable root for synthetic Git objects and checkout edits.
        capsys : pytest.CaptureFixture[str]
            Captured public CLI output, including failure channels.
        revision : str
            Invalid revision expression selected by parameterization.
        """
        repository(tmp_path)
        assert (
            main(
                ['source-inventory', '--root', str(tmp_path), '--revision=' + revision],
            )
            == 1
        )
        captured = capsys.readouterr()
        assert captured.out == ''
        assert 'source-inventory' in captured.err

    @pytest.mark.parametrize(
        'blob',
        [
            b'wrong blob 1\nx\n',
            b'id tree 1\nx\n',
            b'id blob -1\n',
            b'id blob 9\nx\n',
            b'id blob 1\nx\nextra',
            b'',
            b'id blob PRIVATE\nx\n',
            b'id blob 1 PRIVATE\nx\n',
        ],
    )
    def test_malformed_batch_data_fails(
        self,
        tmp_path: Path,
        blob: bytes,
    ) -> None:
        """
        Verify malformed batch data fails.

        Reject mismatched IDs, types, sizes, truncation and trailing object
        data.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable root for synthetic Git objects and checkout edits.
        blob : bytes
            Malformed batch response for independent integrity scenarios.
        """
        with (
            patch.object(
                inventory,
                '_git',
                side_effect=[
                    str(tmp_path).encode(),
                    b'commit',
                    b'100644 blob id\tfile\0',
                    blob,
                ],
            ),
            pytest.raises(ValueError) as raised,
        ):
            inventory.collect(tmp_path, 'HEAD')
        assert 'PRIVATE' not in str(raised.value)

    def test_replacements_are_ignored(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Keep local replacement refs out of committed release evidence.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable root for synthetic Git objects and checkout edits.
        """
        commit = repository(tmp_path)
        git(tmp_path, 'commit', '-m', 'Staged replacement')
        git(tmp_path, 'replace', commit, 'HEAD')
        actual, files = inventory.collect(tmp_path, commit)
        assert actual == commit
        assert (
            next(f for f in files if f.path == 'a_b.txt').sha256
            == hashlib.sha256(b'committed\n').hexdigest()
        )

    def test_repository_environment_is_ignored(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Honor the explicit root despite inherited Git repository overrides.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable root for synthetic Git objects and checkout edits.
        """
        commit = repository(tmp_path)
        with patch.dict(
            'os.environ',
            {
                'GIT_DIR': str(tmp_path / 'missing.git'),
                'GIT_WORK_TREE': '/nonexistent-fixture',
            },
        ):
            actual, _ = inventory.collect(tmp_path, 'HEAD')
        assert actual == commit

    def test_spdx_generations_have_distinct_namespaces(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Verify spdx generations have distinct namespaces.

        Avoid reusing one SPDX namespace across independently created
        documents.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable root for synthetic Git objects and checkout edits.
        """
        repository(tmp_path)
        first = inventory.document(tmp_path, 'HEAD', 'Example', 'spdx')
        second = inventory.document(tmp_path, 'HEAD', 'Example', 'spdx')
        assert first['documentNamespace'] != second['documentNamespace']
        assert first['files'] == second['files']

    def test_subdirectory_is_not_a_repository_root(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Verify subdirectory is not a repository root.

        Prevent accidentally inventorying a parent repository's unrelated
        files.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable root for synthetic Git objects and checkout edits.
        """
        repository(tmp_path)
        nested = tmp_path / 'nested'
        nested.mkdir()
        with pytest.raises(ValueError, match='top-level'):
            inventory.collect(nested, 'HEAD')

    def test_symlinks_are_not_followed(
        self,
        tmp_path: Path,
        symlink: Callable[[Path, Path], None],
    ) -> None:
        """
        Hash committed link text and retain executable and special path modes.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable root for synthetic Git objects and checkout edits.
        symlink : collections.abc.Callable[[pathlib.Path, pathlib.Path], None]
            Skip only unsupported or permission-restricted link operations.
        """
        repository(tmp_path)
        symlink(tmp_path / 'external-link', Path('../private-source'))
        source = tmp_path / 'space\tline\nü.txt'
        source.write_bytes(b'unusual path')
        source.chmod(0o755)
        git(tmp_path, 'add', 'external-link', source.name)
        git(tmp_path, 'commit', '-m', 'Links and names')
        _, files = inventory.collect(tmp_path, 'HEAD')
        link = next(f for f in files if f.path == 'external-link')
        assert link.mode == '120000'
        assert link.sha256 == hashlib.sha256(b'../private-source').hexdigest()
        assert any(f.path == source.name for f in files)

    def test_unsupported_format(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Reject unsupported direct rendering formats before collection.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Disposable root for synthetic Git objects and checkout edits.
        """
        with pytest.raises(ValueError, match='format'):
            inventory.document(tmp_path, 'HEAD', 'Example', 'xml')
