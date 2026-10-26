"""
:mod:`popo.checks.files` module.

Validate exact required files and configured source headers without mutation.
"""

import ast
import subprocess
from fnmatch import fnmatchcase
from itertools import dropwhile, takewhile
from pathlib import Path

from ..config.files import HeaderRule, HeadersConfig, RequiredFilesConfig

# SECTION: PROTECTED FUNCTIONS


def _header(
    text: str,
    rule: HeaderRule,
) -> str:
    """Extract a leading comment while preserving consumer directives."""
    if rule.first_line or rule.first_line_prefix:
        first, separator, text = text.partition('\n')
        if (
            not separator
            or (rule.first_line and first != rule.first_line)
            or (rule.first_line_prefix and not first.startswith(rule.first_line_prefix))
        ):
            raise ValueError('required first-line directive is missing or malformed')
        if rule.trim_after_first_line:
            text = text.lstrip('\n')
    for prefix in rule.preamble_prefixes:
        if text.startswith(prefix):
            text = text.partition('\n')[2]
            if rule.format == 'hash':
                text = text.removeprefix('#\n')
    if rule.format == 'raw':
        return text
    if rule.format == 'python':
        try:
            return ast.get_docstring(ast.parse(text)) or ''
        except SyntaxError as error:
            raise ValueError('invalid Python source') from error
    if rule.format == 'xml':
        text = ''.join(
            dropwhile(
                lambda line: line.startswith(('<?xml ', '<!DOCTYPE ')),
                text.splitlines(keepends=True),
            ),
        )
    if rule.format in {'html', 'xml', 'block'}:
        start, end = ('/*\n', '*/') if rule.format == 'block' else ('<!--\n', '-->')
        if not text.startswith(start) or end not in text:
            raise ValueError('required leading comment is missing')
        return text.removeprefix(start).partition(end)[0].strip('\n')
    marker = '#' if rule.format == 'hash' else '//'
    if text.startswith('#!'):
        text = text.partition('\n')[2]
    return '\n'.join(
        line.removeprefix(marker).removeprefix(' ')
        for line in takewhile(lambda line: line.startswith(marker), text.splitlines())
    )


def _problem(
    relative: str,
    text: str,
    rule: HeaderRule,
    config: HeadersConfig,
) -> str | None:
    """Apply literal identity/purpose contracts after extracting the header."""
    header = _header(text, rule)
    path = Path(relative)
    prefix = rule.prefix.format(
        filename=path.name,
        module=path.stem.replace('-', '_'),
        project=config.project,
        notice=config.notice,
    )
    if not header.startswith(prefix):
        return 'header does not match configured identity/prefix'
    rest = header.removeprefix(prefix)
    if rule.purpose_required and not rest.split('\n\n', 1)[0].strip():
        return 'file purpose is missing'
    if any(value not in rest for value in rule.required_text):
        return 'required header text is missing'
    return None


def _sources(
    config: HeadersConfig,
) -> list[Path]:
    """Discover tracked/unignored sources, with bounded non-Git fallback."""
    try:
        result = subprocess.run(
            [
                'git',
                '-C',
                str(config.root),
                'ls-files',
                '--cached',
                '--others',
                '--exclude-standard',
                '-z',
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        result = None
    if result is not None and result.returncode == 0:
        paths = {config.root / name for name in result.stdout.split('\0') if name}
    else:
        if result is not None and (config.root / '.git').exists():
            raise OSError('Git source inventory failed')
        paths = set()
        for directory, directories, names in config.root.walk(on_error=_walk_error):
            directories[:] = [
                name for name in directories if name not in config.ignored_directories
            ]
            paths.update(directory / name for name in names)
    return sorted(
        path
        for path in paths
        if (path.is_file() or (path.is_symlink() and not path.exists()))
        and not set(path.relative_to(config.root).parts[:-1]).intersection(
            config.ignored_directories,
        )
        and path.name != '.git'
    )


def _walk_error(
    error: OSError,
) -> None:
    """Keep unreadable fallback directories from silently reducing coverage."""
    raise error


# !SECTION


# SECTION: FUNCTIONS


def validate_headers(
    config: HeadersConfig,
) -> list[str]:
    """
    Check maintained files with first-match rules and explicit exceptions.

    Parameters
    ----------
    config : HeadersConfig
        Consumer-owned identity, templates, directives and exclusions.

    Returns
    -------
    list[str]
        Unclassified formats, malformed headers, discovery/read failures and
        symlink escapes, including dangling links. Exception contents are never
        decoded.

    Notes
    -----
    Pattern matching is case-sensitive fnmatch over root-relative POSIX paths;
    stars can span separators. Rules use declaration order. No code from
    configuration is evaluated and files are never changed.
    """
    failures = []
    try:
        paths = _sources(config)
    except (OSError, UnicodeError, subprocess.TimeoutExpired) as error:
        return [f'header source discovery failed: {error}']
    for path in paths:
        relative = path.relative_to(config.root).as_posix()
        try:
            if not path.resolve().is_relative_to(config.root):
                failures.append(f'{relative}: header source escapes repository')
                continue
            if any(
                fnmatchcase(relative, pattern)
                for entry in config.exceptions
                for pattern in entry.patterns
            ):
                continue
            rule = next(
                (
                    entry
                    for entry in config.rules
                    if any(fnmatchcase(relative, pattern) for pattern in entry.patterns)
                ),
                None,
            )
            if rule is None:
                failures.append(
                    f'{relative}: unclassified header format; '
                    'configure a rule or preservation exception',
                )
                continue
            problem = _problem(relative, path.read_text(encoding='utf-8'), rule, config)
            if problem:
                failures.append(f'{relative}: {problem}')
        except (OSError, UnicodeError, ValueError) as error:
            failures.append(f'{relative}: {error}')
    return failures


def validate_required(
    config: RequiredFilesConfig,
) -> list[str]:
    """
    Report every missing, non-file or escaping required path.

    Parameters
    ----------
    config : RequiredFilesConfig
        Resolved root and exact filenames, validated by the loader.

    Returns
    -------
    list[str]
        Relative-path diagnostics; all configured entries are checked. Path
        resolution and inspection errors become diagnostics rather than
        stopping later checks.
    """
    failures = []
    for relative in config.required:
        path = config.root / relative
        try:
            if not path.resolve().is_relative_to(config.root):
                failures.append(f'{relative}: required file escapes repository')
            elif not path.is_file():
                failures.append(
                    f'{relative}: required file does not exist or is not a file',
                )
        except (OSError, UnicodeError, ValueError) as error:
            failures.append(f'{relative}: {error}')
    return failures


# !SECTION
