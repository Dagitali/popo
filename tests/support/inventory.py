"""
:mod:`tests.support.inventory` module.

Create small committed Git repositories for source-inventory acceptance tests.
"""

import subprocess
from pathlib import Path

# SECTION: FUNCTIONS


def git(
    root: Path,
    *args: str,
) -> str:
    """
    Run bounded Git fixture commands without user hooks or commit signing.

    Parameters
    ----------
    root : pathlib.Path
        Disposable repository directory.
    *args : str
        Git arguments for synthetic setup, never production repositories.

    Returns
    -------
    str
        UTF-8 stdout with trailing whitespace removed.

    Raises
    ------
    subprocess.CalledProcessError, subprocess.TimeoutExpired
        Git fails or exceeds 30 seconds.
    OSError, UnicodeError
        Git cannot launch or output cannot decode.
    """
    return subprocess.check_output(
        [
            'git',
            '-C',
            str(root),
            '-c',
            'core.hooksPath=/dev/null',
            '-c',
            'commit.gpgsign=false',
            '-c',
            'user.name=Synthetic Fixture',
            '-c',
            'user.email=fixture@example.invalid',
            *args,
        ],
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=30,
    ).strip()


def repository(
    root: Path,
) -> str:
    """
    Commit text and binary fixtures, then dirty both worktree and index.

    Parameters
    ----------
    root : pathlib.Path
        Existing empty temporary directory.

    Returns
    -------
    str
        Full commit ID identifying original source bytes.

    Raises
    ------
    OSError, UnicodeError
        Fixture files cannot be written or Git output decoded.
    subprocess.CalledProcessError, subprocess.TimeoutExpired
        Repository setup fails or times out.
    """
    git(root, 'init', '--template=')
    (root / 'a_b.txt').write_bytes(b'committed\n')
    (root / 'a-b.txt').write_bytes(b'\x00\xff\nblob')
    git(root, 'add', '.')
    git(root, 'commit', '-m', 'Synthetic source')
    commit = git(root, 'rev-parse', 'HEAD')
    git(root, 'tag', 'fixture-tag')
    (root / 'a_b.txt').write_text('staged edit', encoding='utf-8')
    git(root, 'add', 'a_b.txt')
    (root / 'a_b.txt').write_text('unstaged edit', encoding='utf-8')
    (root / 'untracked.txt').write_text('not inventoried', encoding='utf-8')
    return commit


# !SECTION
