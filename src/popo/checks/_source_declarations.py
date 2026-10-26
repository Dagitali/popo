"""
:mod:`popo.checks._source_declarations` module.

Store the declaration facts shared by source-policy front ends.
"""

from dataclasses import dataclass

# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class CallableRequirements:
    """
    Describe derived return and exception documentation requirements.

    Attributes
    ----------
    return_section : str
        Required conceptual section: Returns, Yields, or empty when unneeded.
        Documentation interpreters map this to the language's notation.
    raises : bool
        Whether explicit raise or throws/rethrows syntax requires coverage.
        This does not establish exception escape behavior.

    Notes
    -----
    Language-specific collectors decide how annotations, bodies or signatures
    contribute these requirements. Parameter documentation remains represented
    separately by DeclarationFacts.parameter_names. The record performs no
    validation, code execution or type resolution.
    """

    return_section: str = ''
    raises: bool = False


@dataclass(frozen=True, slots=True)
class DeclarationFacts:
    """
    Describe syntax-derived documentation and signature requirements.

    Attributes
    ----------
    line : int
        One-based declaration line for location-only findings.
    kind : str
        Language-specific declaration keyword or category.
    documentation : str
        Attached documentation, without source-language delimiters.
    parameter_names : tuple[str, ...] or None
        Names requiring documentation, or None for unsupported signatures.
        Python receivers and unnamed Swift arguments are excluded.
    return_section : str
        Required conceptual section: Returns, Yields, or empty when unneeded.
        Documentation interpreters map this to the language's notation.
    raises : bool
        Whether explicit raise or throws/rethrows syntax requires coverage.
        This does not establish exception escape behavior.
    parameter_lines : bool
        Whether parameter declarations satisfy the language's layout rule.
    """

    line: int
    kind: str
    documentation: str
    parameter_names: tuple[str, ...] | None
    return_section: str = ''
    raises: bool = False
    parameter_lines: bool = True


@dataclass(frozen=True, slots=True)
class SourceFacts[Declaration]:
    """
    Describe a parsed source file without executing consumer code.

    Attributes
    ----------
    has_overview : bool
        Whether the language's file-overview convention is satisfied.
    documentation_lines : tuple[int, ...]
        One-based physical documentation lines for common width checks.
    declarations : tuple[Declaration, ...]
        Language-specific records containing shared DeclarationFacts and only
        the additional observations needed by that language's rules.
    """

    has_overview: bool
    documentation_lines: tuple[int, ...]
    declarations: tuple[Declaration, ...]


# !SECTION
