"""
:mod:`popo.checks._source_declarations` module.

Store the declaration facts shared by source-policy front ends.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, Protocol, Self

# SECTION: TYPE ALIASES


# Conceptual result requirements, independent of native annotation/markup names.
type ResultSection = Literal['', 'Returns', 'Yields']


# !SECTION


# SECTION: DATA CLASSES (1 of 2)


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

    @classmethod
    def from_requirements(
        cls,
        *,
        line: int,
        kind: str,
        documentation: str,
        parameter_names: tuple[str, ...] | None,
        requirements: CallableRequirements,
        parameter_lines: bool = True,
    ) -> Self:
        """
        Assemble shared declaration facts from native observations.

        Parameters
        ----------
        line : int
            One-based declaration line selected by the native collector.
        kind : str
            Native declaration keyword or category.
        documentation : str
            Attached documentation with source-language delimiters removed.
        parameter_names : tuple[str, ...] or None
            Documentable names, or None for an unsupported signature.
            Native receiver and unnamed-argument exclusions remain intact.
        requirements : CallableRequirements
            Previously derived conceptual result and exception requirements.
        parameter_lines : bool, optional
            Native signature-layout decision, including language exceptions.

        Returns
        -------
        Self
            Declaration facts retaining supplied observations unchanged.

        Notes
        -----
        This factory owns the requirement-to-field mapping, not syntax,
        documentation attachment, policy evaluation or requirement derivation.
        Direct construction remains available for already flattened facts.
        No source is read, parsed, validated or executed.
        """
        return cls(
            line=line,
            kind=kind,
            documentation=documentation,
            parameter_names=parameter_names,
            return_section=requirements.return_section,
            raises=requirements.raises,
            parameter_lines=parameter_lines,
        )


@dataclass(frozen=True, slots=True)
class ParameterSpan:
    """
    Store physical parameter extent independently of native syntax locations.

    Attributes
    ----------
    start : int
        One-based first parameter line, excluding leading whitespace.
    end : int or None
        One-based final parameter line, excluding trailing whitespace, or None
        when native syntax does not provide an end location.

    Notes
    -----
    Native collectors select the extent. Python supplies AST argument spans
    and checks defaults separately; Swift includes type/default text in spans.
    Receiver exceptions remain native policy decisions.
    """

    start: int
    end: int | None


# !SECTION


# SECTION: PROTOCOLS


class DeclarationRecord(Protocol):
    """
    Expose shared declaration facts without replacing native observations.

    Notes
    -----
    Native frozen records satisfy this structural contract through their facts
    field. A read-only property permits immutable implementations without
    requiring inheritance, wrappers or runtime protocol checks. Python retains
    annotation/order observations; Swift retains attachment/spacing facts.
    """

    @property
    def facts(self) -> DeclarationFacts:
        """
        Return precomputed shared documentation and signature observations.

        Returns
        -------
        DeclarationFacts
            Native declaration location, documentation and callable facts.
            Access must not parse, read, modify or execute consumer source.
        """
        ...


# !SECTION


# SECTION: DATA CLASSES (2 of 2)


@dataclass(frozen=True, slots=True)
class SourceFacts[Declaration: DeclarationRecord]:
    """
    Describe a parsed source file without executing consumer code.

    Attributes
    ----------
    has_overview : bool
        Whether the language's file-overview convention is satisfied.
    documentation_lines : tuple[int, ...]
        One-based physical documentation lines for common width checks.
    declarations : tuple[Declaration, ...]
        Native records satisfying DeclarationRecord, retaining shared facts
        and language-specific observations. Native discovery order is retained:
        Python breadth-first, Swift source order.
    """

    has_overview: bool
    documentation_lines: tuple[int, ...]
    declarations: tuple[Declaration, ...]


# !SECTION


# SECTION: FUNCTIONS


def parameter_lines(
    declaration_line: int,
    spans: Iterable[ParameterSpan],
) -> bool:
    """
    Require distinct single-line parameters after the declaration line.

    Parameters
    ----------
    declaration_line : int
        One-based native declaration line.
    spans : collections.abc.Iterable[ParameterSpan]
        Native parameter extents; each span is consumed once in any order.

    Returns
    -------
    bool
        True for no parameters or distinct single-line spans strictly after
        declaration_line. Missing end locations fail the single-line rule.

    Notes
    -----
    Native adapters own receiver exceptions, default-expression checks and
    syntax support. No source is parsed, read, modified or executed here.
    """
    seen: set[int] = set()
    for span in spans:
        if (
            span.start <= declaration_line
            or span.start != span.end
            or span.start in seen
        ):
            return False
        seen.add(span.start)
    return True


# !SECTION
