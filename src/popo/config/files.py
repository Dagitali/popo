"""
:mod:`popo.config.files` module.

Load opt-in required-file and language-neutral header contracts.
"""

from dataclasses import dataclass
from pathlib import Path
from string import Formatter
from typing import cast

from ._common import ConfigurationError, read_popo, read_string, require_table

# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class RequiredFilesConfig:
    """Store a resolved consumer root and exact required relative filenames."""

    root: Path
    required: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HeaderRule:
    """Describe first-match patterns, comment syntax and literal templates.

    Notes
    -----
    Prefix fields enforce executable directives before extracting a header.
    Template substitutions are limited to filename, module, project and notice.
    Required text and purpose checks apply after the expanded header prefix.
    """

    patterns: tuple[str, ...]
    format: str
    prefix: str
    required_text: tuple[str, ...] = ()
    first_line: str = ''
    first_line_prefix: str = ''
    trim_after_first_line: bool = False
    preamble_prefixes: tuple[str, ...] = ()
    purpose_required: bool = True


@dataclass(frozen=True, slots=True)
class HeaderException:
    """Preserve matched files without reading contents, with a stated reason."""

    patterns: tuple[str, ...]
    reason: str


@dataclass(frozen=True, slots=True)
class HeadersConfig:
    """Store consumer identity, ordered rules and explicit preservation policy."""

    root: Path
    project: str
    notice: str
    rules: tuple[HeaderRule, ...]
    exceptions: tuple[HeaderException, ...]
    ignored_directories: tuple[str, ...]


# !SECTION


# SECTION: PROTECTED FUNCTIONS


def _boolean(
    table: dict[str, object],
    key: str,
    default: bool,
) -> bool:
    """Reject string-valued booleans in consumer policy."""
    value = table.get(key, default)
    if type(value) is not bool:
        raise ConfigurationError(f'{key} must be boolean')
    return value


def _paths(
    value: object,
    label: str,
    *,
    patterns: bool,
) -> tuple[str, ...]:
    """Validate portable root-relative paths without filesystem access."""
    result = _strings(value, label)
    for item in result:
        if (
            Path(item).is_absolute()
            or '..' in item.split('/')
            or '\\' in item
            or ':' in item
            or item in {'.', ''}
            or (not patterns and any(token in item for token in '*?['))
        ):
            raise ConfigurationError(f'{label} must stay inside the repository')
    return result


def _strings(
    value: object,
    label: str,
) -> tuple[str, ...]:
    """Require unique nonempty strings rather than silently accepting typos."""
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ConfigurationError(f'{label} must be an array of nonempty strings')
    result = tuple(cast(list[str], value))
    if len(set(result)) != len(result):
        raise ConfigurationError(f'{label} contains duplicates')
    return result


def _template(
    value: str,
) -> str:
    """Validate a literal template without allowing attribute/index access."""
    try:
        for _, field, spec, conversion in Formatter().parse(value):
            if field is not None and (
                field not in {'filename', 'module', 'project', 'notice'}
                or spec
                or conversion
            ):
                raise ValueError('unsupported substitution')
    except ValueError as error:
        raise ConfigurationError(f'invalid header prefix template: {error}') from error
    return value


# !SECTION


# SECTION: FUNCTIONS


def load_headers_config(
    root: Path,
) -> HeadersConfig | None:
    """
    Load identity and ordered header rules without inspecting sources.

    Parameters
    ----------
    root : pathlib.Path
        Consumer root containing optional tool.popo.headers settings.

    Returns
    -------
    HeadersConfig or None
        Validated header policy, or None when the table is absent.

    Raises
    ------
    ConfigurationError
        If unknown settings, unsafe patterns or invalid rules are present.
    OSError, UnicodeError
        If configuration cannot be read or decoded.
    """
    popo = read_popo(root)
    if 'headers' not in popo:
        return None
    table = require_table(popo['headers'], name='tool.popo.headers')
    if set(table) - {'project', 'notice', 'rules', 'exceptions', 'ignored-directories'}:
        raise ConfigurationError('unknown tool.popo.headers setting')
    rules: list[HeaderRule] = []
    entries = table.get('rules', [])
    if not isinstance(entries, list) or not entries:
        raise ConfigurationError('headers.rules must be a nonempty array')
    for entry in entries:
        row = require_table(entry, name='header rule')
        if set(row) - {
            'patterns',
            'format',
            'prefix',
            'required-text',
            'first-line',
            'first-line-prefix',
            'trim-after-first-line',
            'preamble-prefixes',
            'purpose-required',
        }:
            raise ConfigurationError('unknown header rule setting')
        patterns = _paths(row.get('patterns'), 'header patterns', patterns=True)
        if not patterns:
            raise ConfigurationError('header patterns must not be empty')
        kind = read_string(row, 'format', default='')
        if kind not in {'raw', 'python', 'hash', 'slash', 'html', 'xml', 'block'}:
            raise ConfigurationError('unsupported header format')
        first = row.get('first-line', '')
        first_prefix = row.get('first-line-prefix', '')
        if (
            not isinstance(first, str)
            or not isinstance(first_prefix, str)
            or (first and first_prefix)
        ):
            raise ConfigurationError('use one string first-line or first-line-prefix')
        rules.append(
            HeaderRule(
                patterns,
                kind,
                _template(read_string(row, 'prefix', default='')),
                _strings(row.get('required-text', []), 'required-text'),
                first,
                first_prefix,
                _boolean(row, 'trim-after-first-line', False),
                _strings(row.get('preamble-prefixes', []), 'preamble-prefixes'),
                _boolean(row, 'purpose-required', True),
            ),
        )
    entries = table.get('exceptions', [])
    if not isinstance(entries, list):
        raise ConfigurationError('headers.exceptions must be an array')
    exceptions: list[HeaderException] = []
    for entry in entries:
        row = require_table(entry, name='header exception')
        if set(row) != {'patterns', 'reason'}:
            raise ConfigurationError('header exception requires patterns and reason')
        patterns = _paths(row['patterns'], 'exception patterns', patterns=True)
        if not patterns:
            raise ConfigurationError('exception patterns must not be empty')
        reason = read_string(row, 'reason', default='')
        if not reason.strip():
            raise ConfigurationError('header exception reason must not be blank')
        exceptions.append(HeaderException(patterns, reason))
    ignored = _strings(
        table.get(
            'ignored-directories',
            [
                '.git',
                '.venv',
                '.build',
                '.swiftpm',
                '__pycache__',
                '.pytest_cache',
                '.mypy_cache',
                '.ruff_cache',
                'build',
                'dist',
                'node_modules',
            ],
        ),
        'ignored-directories',
    )
    if any(
        '/' in item
        or '\\' in item
        or item in {'.', '..'}
        or any(c in item for c in '*?[')
        for item in ignored
    ):
        raise ConfigurationError(
            'ignored-directories must contain literal directory names',
        )
    return HeadersConfig(
        root.resolve(),
        read_string(table, 'project', default=''),
        read_string(table, 'notice', default=''),
        tuple(rules),
        tuple(exceptions),
        ignored,
    )


def load_required_files_config(
    root: Path,
) -> RequiredFilesConfig | None:
    """
    Load exact required paths; absence leaves aggregate checks unchanged.

    Parameters
    ----------
    root : pathlib.Path
        Consumer root containing optional tool.popo.files settings.

    Returns
    -------
    RequiredFilesConfig or None
        Validated policy, or None when the table is absent.

    Raises
    ------
    ConfigurationError
        If paths, keys or their types are invalid.
    OSError, UnicodeError
        If configuration cannot be read or decoded.
    """
    popo = read_popo(root)
    if 'files' not in popo:
        return None
    table = require_table(popo['files'], name='tool.popo.files')
    if set(table) != {'required'}:
        raise ConfigurationError('tool.popo.files requires only required')
    paths = _paths(table['required'], 'files.required', patterns=False)
    if not paths:
        raise ConfigurationError('files.required must not be empty')
    return RequiredFilesConfig(root.resolve(), paths)
