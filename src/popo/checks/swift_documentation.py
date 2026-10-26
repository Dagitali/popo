"""
:mod:`popo.checks.swift_documentation` module.

Check configured Swift documentation using lexical masking, not compilation.
"""

import re

from popo.config.source_checks import SourceCheckConfig

from ._source_inputs import discover, read_source

# SECTION: CONSTANTS


DECLARATION = re.compile(
    r'^\s*(?:(?:@\w+(?:\([^\n]*\))?|public|private|fileprivate|internal|'
    r'final|nonisolated|open|package|indirect|distributed)\s+)*'
    r'(?:struct|class|enum|actor|protocol|extension)\s+\w+',
)
STRING_START = re.compile(r'(#+)?("""|")')


# !SECTION


# SECTION: FUNCTIONS


def code_only(
    source: str,
) -> str:
    """
    Mask comments and Swift strings while retaining line and column positions.

    Parameters
    ----------
    source : str
        Swift text that is never evaluated.

    Returns
    -------
    str
        Text with nested block comments, line comments, ordinary, multiline
        and raw strings blanked. This is a lexical guard, not a Swift parser;
        regex literals and semantic declaration resolution are unsupported.
    """
    result = list(source)
    index = 0
    while index < len(source):
        start = index
        if source.startswith('//', index):
            end = source.find('\n', index)
            index = len(source) if end == -1 else end
        elif source.startswith('/*', index):
            index += 2
            depth = 1
            while index < len(source) and depth:
                if source.startswith('/*', index):
                    depth += 1
                    index += 2
                elif source.startswith('*/', index):
                    depth -= 1
                    index += 2
                else:
                    index += 1
        elif match := STRING_START.match(source, index):
            hashes = match.group(1) or ''
            closing = match.group(2) + hashes
            index += len(match.group())
            while index < len(source):
                if source.startswith('\\' + hashes, index):
                    index += 2 + len(hashes)
                elif source.startswith(closing, index):
                    index += len(closing)
                    break
                else:
                    index += 1
        else:
            index += 1
            continue
        for offset in range(start, min(index, len(source))):
            if result[offset] != '\n':
                result[offset] = ' '
    return ''.join(result)


def validate(
    config: SourceCheckConfig,
) -> list[str]:
    """
    Return overview, nominal declaration and source-guide findings.

    Parameters
    ----------
    config : SourceCheckConfig
        Swift source selection, documentation switches and optional guide.

    Returns
    -------
    list[str]
        Location-only diagnostics, including missing inputs and guide errors.
        Compiler and DocC validation remain separate responsibilities.
    """
    paths, failures = discover(config)
    guide_name = str(config.settings['source-guide'])
    guide: str | None = None
    if guide_name:
        path = config.root / guide_name
        if not path.resolve().is_relative_to(config.root):
            failures.append('source-guide escapes repository root')
        else:
            guide, errors = read_source(path, config.root)
            failures.extend(errors)
    entries = set(re.findall(r'`([^`\n]+\.swift)`', guide or ''))
    for path in paths:
        source, errors = read_source(path, config.root)
        failures.extend(errors)
        if source is None:
            continue
        relative = path.relative_to(config.root).as_posix()
        lines = source.splitlines()
        code = code_only(source).splitlines()
        first_code = next((i for i, line in enumerate(code) if line.strip()), len(code))
        if config.settings['file-overviews'] and not any(
            line.startswith('/// ') for line in lines[:first_code]
        ):
            failures.append(f'{relative}: missing file overview')
        if guide_name and guide is not None and relative not in entries:
            failures.append(f'{relative}: missing source-guide entry')
        for index, line in enumerate(code):
            if not DECLARATION.match(line):
                continue
            start = index
            while start and code[start - 1].lstrip().startswith('@'):
                start -= 1
            declaration_start = start
            while start and lines[start - 1].lstrip().startswith('///'):
                start -= 1
            if start == declaration_start:
                if config.settings['declaration-docs']:
                    failures.append(
                        f'{relative}:{index + 1}: missing declaration documentation',
                    )
            elif (
                config.settings['declaration-spacing']
                and start
                and lines[start - 1].strip()
            ):
                failures.append(
                    f'{relative}:{start + 1}: missing blank line before documentation',
                )
    return failures


# !SECTION
