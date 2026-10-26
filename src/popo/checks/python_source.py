"""
:mod:`popo.checks.python_source` module.

Inspect configured Python conventions through ASTs without importing code.
"""

from popo.config.source_checks import SourceCheckConfig

from ._python_declarations import NOMINAL_KINDS, Declaration, parse
from ._python_documentation import documentation_findings
from ._source_declarations import SourceFacts
from ._source_documentation import guide_findings, limits
from ._source_inputs import discover, read_source

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
        Observations from parse; no additional AST traversal occurs here.
    config : SourceCheckConfig
        Consumer-owned annotation, ordering and parameter-layout switches.
    relative : str
        Repository-relative filename for location-only diagnostics.

    Returns
    -------
    list[str]
        Enabled rule violations without identifiers or source excerpts.
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


# !SECTION


# SECTION: FUNCTIONS


def validate(
    config: SourceCheckConfig,
) -> list[str]:
    """
    Return source-convention findings without executing inspected modules.

    Parameters
    ----------
    config : SourceCheckConfig
        Python source paths and opt-in convention settings.

    Returns
    -------
    list[str]
        Location and rule diagnostics, never source or exception contents.
    """
    paths, failures = discover(config)
    failures.extend(guide_findings(config, paths))
    for path in paths:
        source, errors = read_source(path, config.root)
        failures.extend(errors)
        if source is None:
            continue
        relative = path.relative_to(config.root).as_posix()
        lines = source.splitlines()
        try:
            parsed = parse(source)
        except SyntaxError as error:
            failures.extend(limits(config, path, lines, ()))
            failures.append(f'{relative}:{error.lineno}: invalid Python source')
            continue
        failures.extend(limits(config, path, lines, parsed.documentation_lines))
        failures.extend(documentation_findings(parsed, config, relative))
        failures.extend(_convention_findings(parsed, config, relative))
    return failures


# !SECTION
