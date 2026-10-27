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
LINK_PATTERN = re.compile(r'(?P<image>!?)\[[^\]]*\]\((?P<target>[^)]+)\)')
REFERENCE_PATTERN = re.compile(
    r'^ {0,3}\[(?P<label>[^]\n]+)\]:[ \t]*(?P<target><[^>]*>|\S+)',
)
REFERENCE_USE_PATTERN = re.compile(r'\[([^]\n]+)\][ \t]*\[([^]\n]*)\]')
INLINE_CODE_PATTERN = re.compile(r'(?<!`)(`+)(?!`)(.*?)\1(?!`)')

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
    'node_modules',
}


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _anchors(
    path: Path,
) -> set[str]:
    """
    Collect supported heading and explicit HTML anchors outside fenced code.

    Parameters
    ----------
    path : pathlib.Path
        UTF-8 Markdown target to inspect.

    Returns
    -------
    set[str]
        Lowercase heading slugs and lowercased HTML anchor names or IDs.
        Repeated heading slugs receive ``-1``, ``-2``, and later suffixes;
        explicit anchors do not increment heading-duplicate counters.

    Raises
    ------
    OSError
        If the Markdown file cannot be read.
    UnicodeError
        If the file cannot be decoded as UTF-8.

    Notes
    -----
    Only the supported ATX headings and HTML anchor patterns are recognized.
    This is not a complete renderer-specific Markdown anchor implementation.
    """
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
    """
    Yield source lines outside recognized backtick or tilde code fences.

    Parameters
    ----------
    path : pathlib.Path
        UTF-8 Markdown file; the complete file is read when iteration begins.

    Yields
    ------
    tuple[int, str]
        Original one-based line number and visible text without its newline
        or HTML comment spans. Text on either side of a comment is joined.

    Raises
    ------
    OSError
        If the file cannot be read when iteration begins.
    UnicodeError
        If the file cannot be decoded as UTF-8 when iteration begins.

    Notes
    -----
    Fences start with at least three matching markers after at most three
    spaces. Closing fences must use the same marker, be at least as long,
    and have only whitespace after the markers. Fence lines are excluded;
    an unclosed fence suppresses all remaining lines. HTML comments are masked
    without changing line numbers. Inline code and indented code blocks are
    not filtered here; link scanning separately masks inline code.
    """
    fence: str | None = None
    in_comment = False
    for line_number, line in enumerate(
        path.read_text(encoding='utf-8').splitlines(),
        start=1,
    ):
        marker = None if in_comment else FENCE_PATTERN.match(line)
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
        if fence is not None:
            continue
        # Comment delimiters inside inline code are literal Markdown examples.
        visible = INLINE_CODE_PATTERN.sub(lambda match: ' ' * len(match.group()), line)
        parts: list[str] = []
        position = 0
        while True:
            delimiter = '-->' if in_comment else '<!--'
            index = (line if in_comment else visible).find(delimiter, position)
            if index < 0:
                if not in_comment:
                    parts.append(line[position:])
                break
            if not in_comment:
                parts.append(line[position:index])
            position = index + len(delimiter)
            in_comment = not in_comment
        yield line_number, ''.join(parts)


def _markdown_paths(
    root: Path,
) -> list[Path]:
    """
    Return sorted paths matching ``*.md`` beneath the repository root.

    Parameters
    ----------
    root : pathlib.Path
        Directory from which recursive source discovery begins.

    Returns
    -------
    list[pathlib.Path]
        Sorted glob matches outside ignored root-relative path components.
        Matches are not separately filtered to regular files.

    Notes
    -----
    Ignore a path when any root-relative component exactly matches a name in
    :data:`~popo.checks.docs.IGNORED_PARTS`; substring matches such as
    docs/building.md remain. Filtering applies to discovered sources, not
    explicitly linked targets. Glob matching follows the host filesystem's case
    rules. Discovery does not enforce the resolved-target boundary used during
    link validation.
    """
    return sorted(
        path
        for path in root.rglob('*.md')
        if not any(part in IGNORED_PARTS for part in path.relative_to(root).parts)
    )


def _slugify(
    heading: str,
) -> str:
    """
    Convert heading text to the checker's simplified lowercase anchor slug.

    Parameters
    ----------
    heading : str
        Heading text after removal of the Markdown heading markers.

    Returns
    -------
    str
        Normalized anchor base, possibly empty, without a duplicate suffix.

    Notes
    -----
    Strip HTML tags and surrounding whitespace, retain word characters,
    hyphens, and spaces, then replace surviving space runs with hyphens.
    Underscores are retained. Duplicate suffixes are added by
    :func:`~popo.checks.docs._anchors`, not here; full Markdown rendering and
    entity decoding are not performed.
    """
    heading = re.sub(r'<[^>]+>', '', heading).strip().lower()
    heading = re.sub(r'[^\w\- ]', '', heading)
    return re.sub(r'[\s]+', '-', heading)


def _target_findings(
    source: Path,
    line_number: int,
    target: str,
    image: bool,
    resolved_root: Path,
    anchor_cache: dict[Path, set[str]],
) -> list[str]:
    """
    Check one URL's local destination and optional Markdown anchor.

    Parameters
    ----------
    source : pathlib.Path
        Markdown source used for relative target resolution and diagnostics.
    line_number : int
        Original one-based source line containing the link or definition.
    target : str
        Parsed destination text, possibly angle-wrapped or followed by a title.
    image : bool
        Whether the destination is an inline image rather than a regular link.
    resolved_root : pathlib.Path
        Resolved repository boundary for local targets.
    anchor_cache : dict[pathlib.Path, set[str]]
        Per-invocation cache updated only for inspected Markdown targets.

    Returns
    -------
    list[str]
        Malformed URL, missing target, escape or anchor findings. External URLs
        are skipped without fetching; no finding proves remote validity.

    Raises
    ------
    OSError, UnicodeError
        Target resolution, inspection, reading or UTF-8 decoding fails.

    Notes
    -----
    Keep malformed URLs local to this diagnostic so later links are checked.
    Existing directory links need no README unless they include a fragment.
    """
    raw_target = target.strip().strip('<>')
    if ' "' in raw_target:
        raw_target = raw_target.split(' "', maxsplit=1)[0]
    try:
        parsed = urlsplit(raw_target)
    except ValueError:
        return [f'{source}:{line_number}: invalid link target: {raw_target}']
    if parsed.scheme or parsed.netloc:
        return []
    target_path = source if not parsed.path else source.parent / unquote(parsed.path)
    if target_path.is_dir() and parsed.fragment:
        target_path = target_path / 'README.md'
    resolved_target = target_path.resolve()
    if not resolved_target.is_relative_to(resolved_root):
        return [f'{source}:{line_number}: link escapes repository: {raw_target}']
    if target_path.is_dir() and not parsed.fragment and not image:
        return []
    if not target_path.is_file():
        return [f'{source}:{line_number}: local target does not exist: {raw_target}']
    if parsed.fragment and target_path.suffix.lower() == '.md':
        anchor_path = resolved_target
        anchors = anchor_cache.get(anchor_path)
        if anchors is None:
            anchors = anchor_cache[anchor_path] = _anchors(anchor_path)
        if unquote(parsed.fragment).lower() not in anchors:
            return [f'{source}:{line_number}: anchor does not exist: {raw_target}']
    return []


# !SECTION


# SECTION: FUNCTIONS


def validate(
    root: Path,
) -> list[str]:
    """
    Return Markdown URL-syntax and repository-local target findings.

    Parameters
    ----------
    root : pathlib.Path
        Repository tree to inspect, excluding known generated directories.

    Returns
    -------
    list[str]
        Missing-root, missing-target, missing-anchor, repository-escape,
        invalid-reference and malformed-URL findings. Link/reference findings
        retain the source path and original line number.

    Raises
    ------
    OSError
        If a discovered source or inspected Markdown target cannot be read.
    UnicodeError
        If inspected Markdown cannot be decoded as UTF-8.

    Notes
    -----
    Inspect inline links/images and single-line reference definitions outside
    fenced code, HTML comments, and inline code. Accept heading and explicit
    HTML anchors; headings do not require explicit HTML tags. Normalize
    reference labels with whitespace folding and case folding; reject
    conflicting destinations and undefined full or collapsed reference uses.
    Shortcut reference syntax and nested/escaped link syntax are not fully
    supported. Malformed URLs become findings without stopping later links.
    External URLs are skipped without network requests. Fragments are validated
    only for Markdown targets; other local targets are checked for existence.
    Files are never modified.
    Check reference definitions even when unused. Accept existing directory
    links without fragments; resolve directory fragments through README.md.
    Decode local URL paths and reject destinations whose resolved paths fall
    outside the resolved root, including symlinked targets. This boundary is
    a link-target policy, not a filesystem sandbox for source discovery.
    Cache Markdown anchors only within this invocation, keyed by resolved path.
    """

    if not root.is_dir():
        return [f'repository root does not exist: {root}']
    resolved_root = root.resolve()
    failures: list[str] = []
    anchor_cache: dict[Path, set[str]] = {}
    for source in _markdown_paths(root):
        lines = list(_content_lines(source))
        references: dict[str, str] = {}
        for line_number, line in lines:
            reference = REFERENCE_PATTERN.match(line)
            if reference is None:
                continue
            label = ' '.join(reference.group('label').split()).casefold()
            target = reference.group('target').strip('<>')
            if label in references and references[label] != target:
                failures.append(
                    f'{source}:{line_number}: conflicting reference: '
                    f'{reference.group('label')}',
                )
            references.setdefault(label, target)
        for line_number, line in lines:
            reference = REFERENCE_PATTERN.match(line)
            if reference is not None:
                targets = [(reference.group('target'), False)]
            else:
                line = INLINE_CODE_PATTERN.sub('', line)
                for text, label in REFERENCE_USE_PATTERN.findall(line):
                    label = label or text
                    if ' '.join(label.split()).casefold() not in references:
                        failures.append(
                            f'{source}:{line_number}: undefined reference: {label}',
                        )
                targets = [
                    (match.group('target'), bool(match.group('image')))
                    for match in LINK_PATTERN.finditer(line)
                ]
            for target, image in targets:
                failures.extend(
                    _target_findings(
                        source,
                        line_number,
                        target,
                        image,
                        resolved_root,
                        anchor_cache,
                    ),
                )
    return failures


# !SECTION
