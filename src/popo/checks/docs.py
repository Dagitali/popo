"""
:mod:`popo.checks.docs` module.

Validate repository-local Markdown links and heading anchors.
"""

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

# SECTION: CONSTANTS


HEADING_PATTERN = re.compile(r'^#{1,6}\s+(?P<heading>.+?)\s*#*\s*$')
LINK_PATTERN = re.compile(r'(?<!!)\[[^\]]+\]\((?P<target>[^)]+)\)')

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


def _anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    in_fence = False
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.lstrip().startswith(('```', '~~~')):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_PATTERN.match(line)
        if match is None:
            continue
        base = _slugify(match.group('heading'))
        count = counts.get(base, 0)
        counts[base] = count + 1
        anchors.add(base if count == 0 else f'{base}-{count}')
    return anchors


def _markdown_paths(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob('*.md')
        if not any(part in IGNORED_PARTS for part in path.relative_to(root).parts)
        and 'docs/build' not in path.relative_to(root).as_posix()
    )


def _slugify(heading: str) -> str:
    heading = re.sub(r'<[^>]+>', '', heading).strip().lower()
    heading = re.sub(r'[^\w\- ]', '', heading)
    return re.sub(r'[\s]+', '-', heading)


# !SECTION


# SECTION: FUNCTIONS


def validate(root: Path) -> list[str]:
    """Return broken repository-local Markdown link failures."""

    if not root.is_dir():
        return [f'repository root does not exist: {root}']
    failures: list[str] = []
    for source in _markdown_paths(root):
        for line_number, line in enumerate(
            source.read_text(encoding='utf-8').splitlines(),
            start=1,
        ):
            for match in LINK_PATTERN.finditer(line):
                raw_target = match.group('target').strip().strip('<>')
                if ' "' in raw_target:
                    raw_target = raw_target.split(' "', maxsplit=1)[0]
                parsed = urlsplit(raw_target)
                if parsed.scheme or parsed.netloc:
                    continue
                target_path = (
                    source if not parsed.path else source.parent / unquote(parsed.path)
                )
                if target_path.is_dir():
                    target_path = target_path / 'README.md'
                if not target_path.is_file():
                    failures.append(
                        f'{source}:{line_number}: local target does not exist: '
                        f'{raw_target}',
                    )
                    continue
                if parsed.fragment and unquote(parsed.fragment).lower() not in _anchors(
                    target_path,
                ):
                    failures.append(
                        f'{source}:{line_number}: anchor does not exist: {raw_target}',
                    )
    return failures


# !SECTION
