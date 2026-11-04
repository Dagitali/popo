"""
:mod:`popo.checks._openstep` module.

Read the explicit OpenStep property-list subset used by Xcode projects.
"""

import json
import re

# SECTION: TYPE ALIASES


type ProjectValue = str | list[ProjectValue] | dict[str, ProjectValue]


# !SECTION


# SECTION: FUNCTIONS


def parse_project(
    text: str,
) -> ProjectValue:
    """
    Parse the supported OpenStep property-list subset without Xcode.

    Parameters
    ----------
    text : str
        OpenStep project text containing the supported property-list subset.

    Returns
    -------
    ProjectValue
        Parsed string, list or mapping; callers enforce their required root
        type.

    Raises
    ------
    ValueError
        Tokens are truncated, duplicated, malformed or remain after the root.
        Unquoted structural delimiters cannot be scalar values or dictionary
        keys; quoted punctuation remains string data.
    """
    pattern = r'\s+|//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|[{}()=;,]|[^\s{}()=;,"]+'
    tokens = []
    offset = 0
    for match in re.finditer(pattern, text):
        token = match.group()
        if match.start() != offset or (
            token.startswith('/*') and not token.endswith('*/')
        ):
            raise ValueError('Malformed project token')
        offset = match.end()
        if not token.isspace() and not token.startswith(('//', '/*')):
            tokens.append(token)
    if offset != len(text):
        raise ValueError('Malformed project token')
    index = 0

    def peek() -> str:
        """
        Read the next project token without advancing the parser.

        Returns
        -------
        str
            Next unconsumed project token.

        Raises
        ------
        ValueError
            No project token remains at the current parser position.
        """
        if index >= len(tokens):
            raise ValueError('Unexpected end of project')
        return tokens[index]

    def take(
        expected: str | None = None,
    ) -> str:
        """
        Consume the next project token and optionally require its spelling.

        Parameters
        ----------
        expected : str | None, optional
            Required token spelling, or None to accept any next token. Defaults
            to None.

        Returns
        -------
        str
            Consumed project token after optional spelling validation.

        Raises
        ------
        ValueError
            No token remains or its spelling differs from the expected token.
        """
        nonlocal index
        token = peek()
        index += 1
        if expected is not None and token != expected:
            raise ValueError(f'Expected {expected!r}, got {token!r}')
        return token

    def value() -> ProjectValue:
        """
        Parse one recursive OpenStep string, dictionary or array value.

        Returns
        -------
        ProjectValue
            Parsed OpenStep value with nested arrays and dictionaries retained.

        Raises
        ------
        ValueError
            A nested value, delimiter or dictionary key is invalid or
            truncated.
        """
        token = take()
        if token == '{':
            entries: dict[str, ProjectValue] = {}
            while peek() != '}':
                key = value()
                if not isinstance(key, str):
                    raise ValueError('Expected a string project key')
                take('=')
                if key in entries:
                    raise ValueError(f'Duplicate project key: {key}')
                entries[key] = value()
                take(';')
            take('}')
            return entries
        if token == '(':
            items: list[ProjectValue] = []
            while peek() != ')':
                items.append(value())
                if peek() != ')':
                    take(',')
            take(')')
            return items
        if token in {'}', ')', '=', ';', ','}:
            raise ValueError('Unexpected project delimiter')
        return json.loads(token) if token.startswith('"') else token

    result = value()
    if index != len(tokens):
        raise ValueError('Unexpected trailing project content')
    return result


# !SECTION
