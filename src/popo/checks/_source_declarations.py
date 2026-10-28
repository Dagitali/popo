"""
:mod:`popo.checks._source_declarations` module.

Store the declaration facts shared by source-policy front ends.
"""

from dataclasses import dataclass
from typing import Literal, Self

# SECTION: TYPE ALIASES


# Conceptual result requirements, independent of native annotation/markup names.
type ResultSection = Literal['', 'Returns', 'Yields']


# !SECTION


# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class CallableRequirements:
    """
    Describe derived return and exception documentation requirements.

    Attributes
    ----------
    return_section : ResultSection
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
    validation, code execution or type resolution. from_observations only
    normalizes result-section priority and retains the supplied raise flag.
    """

    return_section: ResultSection = ''
    raises: bool = False

    @classmethod
    def from_observations(
        cls,
        *,
        returns: bool = False,
        yields: bool = False,
        raises: bool = False,
    ) -> Self:
        """
        Normalize native callable observations into shared requirements.

        Parameters
        ----------
        returns : bool, optional
            Native evidence requires value-result documentation.
        yields : bool, optional
            Native evidence requires generator-result documentation, taking
            precedence over returns. Swift currently supplies no yield flag.
        raises : bool, optional
            Native evidence requires exception documentation; this remains
            independent of the result section and proves no escape behavior.

        Returns
        -------
        Self
            Yields for generators, otherwise Returns for value results, or no
            result section. Native collectors retain observation/scope rules.

        Notes
        -----
        This factory selects requirement vocabulary without inspecting source,
        resolving types or executing code. Direct construction remains valid
        for already normalized requirements and default empty requirements.
        """
        return cls('Yields' if yields else 'Returns' if returns else '', raises)


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
    return_section : ResultSection
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
    return_section: ResultSection = ''
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
