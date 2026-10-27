"""
:mod:`popo.checks.python_source` module.

Inspect configured Python conventions through ASTs without importing code.
"""

from pathlib import Path

from popo.config.source_checks import SourceCheckConfig

from ._python_declarations import NOMINAL_KINDS, Declaration, parse
from ._python_documentation import documentation_findings
from ._source_declarations import SourceFacts
from ._source_documentation import limits
from ._source_validation import parsed_source_findings, validate_sources

# SECTION: PROTECTED FUNCTIONS


def _convention_findings(
    source: SourceFacts[Declaration],
    config: SourceCheckConfig,
    relative: str,
) -> list[str]:
    """
    Check Python annotation, instance-method order and signature layout.

    Parameters
    ----------
    source : SourceFacts[Declaration]
        Collected declaration facts; no source is parsed again here.
    config : SourceCheckConfig
        Consumer-owned annotation, ordering and parameter-layout switches.
    relative : str
        Repository-relative filename for location-only diagnostics.

    Returns
    -------
    list[str]
        Enabled rule violations in declaration order, without identifiers or
        source excerpts; empty when enabled rules are satisfied.

    Notes
    -----
    Annotation checking requires a return annotation and annotations on every
    parameter, including receivers; annotation types are not validated. Method
    ordering uses the collector's instance-method names rather than all class
    members.
    Parameter layout uses precomputed signature facts for each declaration.
    """
    failures: list[str] = []
    for declaration in source.declarations:
        facts = declaration.facts
        location = f'{relative}:{facts.line}'
        if facts.kind in NOMINAL_KINDS:
            if config.settings[
                'alphabetical-methods'
            ] and declaration.instance_methods != tuple(
                sorted(declaration.instance_methods),
            ):
                failures.append(f'{location}: instance methods not alphabetical')
        elif config.settings['annotations'] and not declaration.annotated:
            failures.append(f'{location}: missing signature annotations')
        if config.settings['parameter-lines'] and not facts.parameter_lines:
            failures.append(f'{location}: parameters require separate lines')
    return failures


def _source_findings(
    config: SourceCheckConfig,
    path: Path,
    source: str,
) -> list[str]:
    """
    Collect Python size, documentation and convention findings for one file.

    Parameters
    ----------
    config : SourceCheckConfig
        Validated consumer-owned limits and documentation/convention settings.
    path : pathlib.Path
        Path used for diagnostics; must be lexically inside config.root.
        This function inspects the supplied text without reading the file.
    source : str
        Decoded source text to inspect without executing consumer code.

    Returns
    -------
    list[str]
        Physical file-length and documentation-width findings, followed by
        documentation and convention findings; empty when all checks pass.
        Invalid Python syntax yields file-limit findings followed by a syntax
        diagnostic. Documentation widths and declaration rules are skipped
        when parsing fails.

    Raises
    ------
    KeyError
        Required limit or rule settings are absent from direct configuration.
    ValueError
        The supplied path is outside config.root or a numeric limit is invalid.
    """
    failures: list[str] = []
    relative = path.relative_to(config.root).as_posix()
    lines = source.splitlines()
    try:
        parsed = parse(source)
    except SyntaxError as error:
        failures.extend(limits(config, path, lines, ()))
        failures.append(f'{relative}:{error.lineno}: invalid Python source')
        return failures
    return parsed_source_findings(
        parsed,
        config,
        path,
        lines,
        documentation_findings,
        _convention_findings,
    )


# !SECTION


# SECTION: FUNCTIONS


def validate(
    config: SourceCheckConfig,
) -> list[str]:
    """
    Validate selected Python source files without executing consumer code.

    Parameters
    ----------
    config : popo.config.source_checks.SourceCheckConfig
        Policy for ``python-source``, normally obtained from
        :func:`~popo.config.source_checks.load_source_check`. Requires a
        resolved repository root, include/exclude glob patterns and domain
        settings.
        Configuration is neither loaded nor revalidated here.

    Returns
    -------
    list[str]
        Discovery and guide findings first, then read or source-rule findings
        for each selected file in sorted path order. An empty list means no
        findings from the configured checks. Diagnostics use relative paths
        and line numbers where applicable, without source excerpts or raw
        exception messages. Unreadable files are reported and skipped while
        remaining files are checked.

    Raises
    ------
    KeyError
        config.settings lacks an option required by this checker.
    ValueError
        A numeric limit cannot be converted to an integer, or a selected path
        cannot be expressed relative to config.root. These indicate a
        configuration that does not satisfy the loader's contracts.

    Notes
    -----
    Inspect sorted, deduplicated files selected by include/exclude patterns.
    Require exact backticked source paths in the optional source guide before
    reading selected files as UTF-8. Physical line limits apply to readable
    files; width limits apply only to recognized documentation lines. Missing
    glob matches, unsafe paths and input read/decode failures become redacted
    findings rather than raw filesystem or decoding exceptions.

    Parse Python ASTs without importing or executing inspected modules. Invalid
    syntax produces a location-only diagnostic after physical file-limit
    checks; documentation and convention checks are skipped for that file.
    Interpret documentation as NumPy-style docstrings. Annotation completeness,
    instance-method ordering and parameter layout are separately opt-in.
    File-overview and declaration-documentation requirements follow the
    consumer's settings. This check does not perform type checking or execute
    examples; those remain separate responsibilities.
    """
    return validate_sources(config, _source_findings)


# !SECTION
