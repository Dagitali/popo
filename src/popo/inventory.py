"""
:mod:`popo.inventory` module.

Inventory committed Git blobs without reading or changing checkout contents.
"""

import datetime
import hashlib
import os
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class SourceFile:
    """Retain a committed path, Git mode and content checksums.

    Attributes
    ----------
    path, mode, sha1, sha256 : str
        UTF-8 root-relative path, tree mode and lowercase hexadecimal hashes.
        Symlink hashes describe link text, never the target's contents.
    """

    path: str
    mode: str
    sha1: str
    sha256: str


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _git(
    root: Path,
    *args: str,
    data: bytes | None = None,
) -> bytes:
    """Run bounded, local-only Git plumbing with sanitized failure messages."""
    try:
        result = subprocess.run(
            ['git', '--no-replace-objects', '-C', str(root), *args],
            input=data,
            capture_output=True,
            timeout=120,
            env={
                key: value
                for key, value in os.environ.items()
                if key
                not in {
                    'GIT_DIR',
                    'GIT_WORK_TREE',
                    'GIT_COMMON_DIR',
                    'GIT_INDEX_FILE',
                    'GIT_OBJECT_DIRECTORY',
                    'GIT_ALTERNATE_OBJECT_DIRECTORIES',
                    'GIT_NAMESPACE',
                    'GIT_PREFIX',
                    'GIT_IMPLICIT_WORK_TREE',
                }
            },
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f'could not run local Git {args[0]}') from error
    if result.returncode:
        raise ValueError(f'local Git {args[0]} failed; check repository and revision')
    return result.stdout


# !SECTION


# SECTION: FUNCTIONS


def collect(
    root: Path,
    revision: str,
) -> tuple[str, tuple[SourceFile, ...]]:
    """
    Hash files from one resolved commit, independent of checkout state.

    Parameters
    ----------
    root : pathlib.Path
        Top-level working-tree directory. Bare repositories are unsupported.
    revision : str
        Required Git revision expression resolving to a commit, including tags.

    Returns
    -------
    tuple[str, tuple[SourceFile, ...]]
        Resolved full commit ID and path-sorted immutable file records.

    Raises
    ------
    ValueError
        Invalid root/revision, Git failure/timeout, empty tree, unsupported
        tree entries (including gitlinks), or malformed Git output. Git
        diagnostics and source bytes are not included in errors.
    OSError, UnicodeError
        Root resolution or UTF-8 decoding fails. No replacement decoding
        occurs.

    Notes
    -----
    Read tree entries and batch-read blobs by object ID. Never follow symlinks,
    recurse into submodules, run filters, read working/index file contents or
    honor replacement objects. Git calls are bounded to 120 seconds each; blob
    output is held in memory. Paths and checksums are evidence, not a binary or
    dependency SBOM. No source files are written or network commands executed.
    """
    root = root.resolve()
    top = Path(_git(root, 'rev-parse', '--show-toplevel').decode().rstrip('\n'))
    if top.resolve() != root:
        raise ValueError('root must be the top-level Git working tree')
    commit = (
        _git(
            root,
            'rev-parse',
            '--verify',
            '--end-of-options',
            revision + '^{commit}',
        )
        .decode()
        .strip()
    )
    tree = _git(root, 'ls-tree', '-rz', '--full-tree', commit)
    entries: list[tuple[str, str, bytes]] = []
    for entry in filter(None, tree.split(b'\0')):
        metadata, path_bytes = entry.split(b'\t', 1)
        mode_bytes, kind, oid = metadata.split()
        if kind != b'blob' or mode_bytes not in (b'100644', b'100755', b'120000'):
            raise ValueError(
                'unsupported Git tree entry; submodules are not inventoried',
            )
        entries.append((path_bytes.decode('utf-8'), mode_bytes.decode(), oid))
    if not entries:
        raise ValueError('commit contains no source files')
    object_ids = b'\n'.join(e[2] for e in entries) + b'\n'
    stream = _git(root, 'cat-file', '--batch', data=object_ids)
    files = []
    offset = 0
    for path, mode, oid in entries:
        end = stream.index(b'\n', offset)
        actual, kind, size_text = stream[offset:end].split()
        size = int(size_text)
        start = end + 1
        stop = start + size
        if (
            actual != oid
            or kind != b'blob'
            or size < 0
            or stream[stop : stop + 1] != b'\n'
        ):
            raise ValueError('malformed Git blob response')
        contents = stream[start:stop]
        files.append(
            SourceFile(
                path,
                mode,
                hashlib.sha1(contents, usedforsecurity=False).hexdigest(),
                hashlib.sha256(contents).hexdigest(),
            ),
        )
        offset = stop + 1
    if offset != len(stream):
        raise ValueError('unexpected trailing Git blob data')
    return commit, tuple(sorted(files, key=lambda item: item.path))


def document(
    root: Path,
    revision: str,
    name: str,
    format_: str,
) -> dict[str, object]:
    """
    Render one committed inventory as plain JSON or source-only SPDX 2.3.

    Parameters
    ----------
    root : pathlib.Path
        Top-level Git working tree passed to collection.
    revision : str
        Explicit commit/tag expression; resolved once before reading objects.
    name : str
        Consumer-owned, nonblank single-line project name.
    format_ : str
        Either ``json`` or ``spdx``. Both use identical committed file bytes.

    Returns
    -------
    dict[str, object]
        Plain schema-version-one evidence or an SPDX 2.3 document. SPDX uses
        unique per-generation namespaces, current UTC creation time, source
        relationships and NOASSERTION license/copyright fields.

    Raises
    ------
    ValueError
        Name/format is invalid or committed collection fails.
    OSError, UnicodeError
        Collection cannot resolve or decode its inputs.

    Notes
    -----
    The SPDX package verification code hashes sorted SHA-1 values per SPDX
    2.3. No dependency completeness, license grants or signing are inferred.
    """
    if not name.strip() or any(c in name for c in '\r\n\0'):
        raise ValueError('name must be nonblank single-line text')
    if format_ not in ('json', 'spdx'):
        raise ValueError('inventory format must be json or spdx')
    commit, files = collect(root, revision)
    if format_ == 'json':
        return {
            'schema_version': 1,
            'kind': 'source-inventory',
            'name': name,
            'revision': commit,
            'scope': 'committed-blobs',
            'files': [
                {'path': f.path, 'mode': f.mode, 'sha256': f.sha256} for f in files
            ],
        }
    package = 'SPDXRef-Source'
    identifiers = [
        'SPDXRef-File-' + hashlib.sha256(f.path.encode()).hexdigest() for f in files
    ]
    return {
        'spdxVersion': 'SPDX-2.3',
        'dataLicense': 'CC0-1.0',
        'SPDXID': 'SPDXRef-DOCUMENT',
        'name': f'{name} committed source inventory',
        'documentNamespace': f'https://spdx.org/spdxdocs/source-{commit}-{uuid.uuid4()}',
        'creationInfo': {
            'created': datetime.datetime.now(datetime.UTC).strftime(
                '%Y-%m-%dT%H:%M:%SZ',
            ),
            'creators': ['Tool: popo source-inventory'],
        },
        'comment': (f'Source/assets at commit {commit}. Not a binary dependency SBOM.'),
        'files': [
            {
                'SPDXID': identity,
                'fileName': './' + f.path,
                'checksums': [
                    {'algorithm': 'SHA1', 'checksumValue': f.sha1},
                    {'algorithm': 'SHA256', 'checksumValue': f.sha256},
                ],
                'licenseConcluded': 'NOASSERTION',
                'licenseInfoInFiles': ['NOASSERTION'],
                'copyrightText': 'NOASSERTION',
            }
            for f, identity in zip(files, identifiers, strict=True)
        ],
        'packages': [
            {
                'SPDXID': package,
                'name': f'{name} source',
                'downloadLocation': 'NOASSERTION',
                'filesAnalyzed': True,
                'packageVerificationCode': {
                    'packageVerificationCodeValue': hashlib.sha1(
                        ''.join(sorted(f.sha1 for f in files)).encode(),
                        usedforsecurity=False,
                    ).hexdigest(),
                },
                'licenseConcluded': 'NOASSERTION',
                'licenseDeclared': 'NOASSERTION',
                'licenseInfoFromFiles': ['NOASSERTION'],
                'copyrightText': 'NOASSERTION',
            },
        ],
        'relationships': [
            {
                'spdxElementId': 'SPDXRef-DOCUMENT',
                'relationshipType': 'DESCRIBES',
                'relatedSpdxElement': package,
            },
        ]
        + [
            {
                'spdxElementId': package,
                'relationshipType': 'CONTAINS',
                'relatedSpdxElement': identity,
            }
            for identity in identifiers
        ],
    }
