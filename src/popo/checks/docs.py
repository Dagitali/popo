"""
:mod:`popo.checks.docs` module.

Validate repository-local Markdown links and heading anchors.
"""

import re
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import unquote, urlsplit

# SECTION: CONSTANTS


FENCE_PATTERN = re.compile(r'^ {0,3}(?P<marker>`{3,}|~{3,})')
EXPLICIT_ANCHOR_PATTERN = re.compile(
    r'<a\s+(?:name|id)=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
HEADING_PATTERN = re.compile(r'^#{1,6}\s+(?P<heading>.+?)\s*#*\s*$')
LINK_PATTERN = re.compile(r'(?<!!)\[[^\]]+\]\((?P<target>[^)]+)\)')
REFERENCE_PATTERN = re.compile(r'^ {0,3}\[[^\]]+\]:[ \t]*(<[^>]*>|\S+)')

IGNORED_PARTS = {
    '.git',
    '.mypy_cache',
    '.pytest_cache',
    '.ruff_cache',
    '.venv',
    '__pycache__',
    'build',
    'dist',
    'htmlcov',
}


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _anchors(
    path: Path,
) -> set[str]:
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    for _, line in _content_lines(path):
        anchors.update(value.lower() for value in EXPLICIT_ANCHOR_PATTERN.findall(line))
        match = HEADING_PATTERN.match(line)
        if match is None:
            continue
        base = _slugify(match.group('heading'))
        count = counts.get(base, 0)
        counts[base] = count + 1
        anchors.add(base if count == 0 else f'{base}-{count}')
    return anchors


def _content_lines(
    path: Path,
) -> Iterator[tuple[int, str]]:
    """Yield original line numbers and text outside fenced code examples."""
    fence: str | None = None
    for line_number, line in enumerate(
        path.read_text(encoding='utf-8').splitlines(),
        start=1,
    ):
        marker = FENCE_PATTERN.match(line)
        if marker is not None:
            candidate = marker.group('marker')
            if fence is None:
                fence = candidate
                continue
            if (
                candidate[0] == fence[0]
                and len(candidate) >= len(fence)
                and not line.removeprefix(marker.group()).strip()
            ):
                fence = None
                continue
        if fence is None:
            yield line_number, line


def _markdown_paths(
    root: Path,
) -> list[Path]:
    return sorted(
        path
        for path in root.rglob('*.md')
        if not any(part in IGNORED_PARTS for part in path.relative_to(root).parts)
        and 'docs/build' not in path.relative_to(root).as_posix()
    )


def _slugify(
    heading: str,
) -> str:
    heading = re.sub(r'<[^>]+>', '', heading).strip().lower()
    heading = re.sub(r'[^\w\- ]', '', heading)
    return re.sub(r'[\s]+', '-', heading)


# !SECTION


# SECTION: FUNCTIONS


def validate(
    root: Path,
) -> list[str]:
    """
    Return broken repository-local Markdown link failures.

    Parameters
    ----------
    root : pathlib.Path
        Repository tree to inspect, excluding known generated directories.

    Returns
    -------
    list[str]
        Missing-root, missing-target, missing-anchor, or repository-escape
        diagnostics, retaining the source path and original line number for
        links.

    Notes
    -----
    Inspect inline links and single-line reference definitions outside fenced
    code blocks. Accept heading and explicit HTML anchors. External URLs are
    skipped without network requests; undefined reference labels and inline
    image links are not checked. Fragments are validated only for Markdown
    targets; other local targets are checked for existence. Files are never
    modified.
    """

    if not root.is_dir():
        return [f'repository root does not exist: {root}']
    resolved_root = root.resolve()
    failures: list[str] = []
    anchor_cache: dict[Path, set[str]] = {}
    for source in _markdown_paths(root):
        for line_number, line in _content_lines(source):
            reference = REFERENCE_PATTERN.match(line)
            targets = (
                [reference.group(1)]
                if reference is not None
                else LINK_PATTERN.findall(line)
            )
            for target in targets:
                raw_target = target.strip().strip('<>')
                if ' "' in raw_target:
                    raw_target = raw_target.split(' "', maxsplit=1)[0]
                parsed = urlsplit(raw_target)
                if parsed.scheme or parsed.netloc:
                    continue
                target_path = (
                    source if not parsed.path else source.parent / unquote(parsed.path)
                )
                if target_path.is_dir() and parsed.fragment:
                    target_path = target_path / 'README.md'
                resolved_target = target_path.resolve()
                if not resolved_target.is_relative_to(resolved_root):
                    failures.append(
                        f'{source}:{line_number}: link escapes repository: '
                        f'{raw_target}',
                    )
                    continue
                if target_path.is_dir() and not parsed.fragment:
                    continue
                if not target_path.is_file():
                    failures.append(
                        f'{source}:{line_number}: local target does not exist: '
                        f'{raw_target}',
                    )
                    continue
                if parsed.fragment and target_path.suffix.lower() == '.md':
                    anchor_path = resolved_target
                    anchors = anchor_cache.get(anchor_path)
                    if anchors is None:
                        anchors = anchor_cache[anchor_path] = _anchors(anchor_path)
                    if unquote(parsed.fragment).lower() not in anchors:
                        failures.append(
                            f'{source}:{line_number}: anchor does not exist: '
                            f'{raw_target}',
                        )
    return failures


# !SECTION
