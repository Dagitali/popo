"""
:mod:`tests.unit.checks.test_u_automation` module.

Exercise portable, read-only automation contracts.
"""

from dataclasses import replace
from pathlib import Path

import pytest

from popo.checks.automation import validate
from popo.config.automation import AutomationConfig, load_automation_config
from tests.support.files import FileWriter

# SECTION: TESTS


@pytest.mark.parametrize(
    ('source', 'message'),
    [
        ('name: one\nname: two', 'duplicate YAML key'),
        ('[', ''),
        ('[]', 'document must be a mapping'),
        ('1: value', 'keys must be strings'),
        ('uses: false', 'uses must be a string'),
        ('uses: upstream/action@main', 'full commit SHA'),
        ('uses: ./missing', 'missing local automation target'),
        ('uses: ./../outside.yml', 'path escapes repository'),
    ],
)
def test_bad_documents(
    tmp_path: Path,
    write_file: FileWriter,
    source: str,
    message: str,
) -> None:
    """
    Verify invalid YAML, references, and targets produce one file diagnostic.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Per-test temporary directory for files and isolated consumer
        repositories.
    write_file : FileWriter
        Fixture writer that creates parent directories and writes UTF-8
        repository files.
    source : str
        YAML document text selected for the validation scenario.
    message : str
        Expected diagnostic substring; an empty string selects a successful
        case.
    """
    write_file('.github/workflows/ci.yml', source)
    failures = validate(AutomationConfig(tmp_path))
    assert len(failures) == 1
    assert message in failures[0]


@pytest.mark.parametrize(
    'metadata',
    [
        '{',
        '[]',
        '{}',
        '{"name":"CI","description":"CI","categories":false}',
        '{"name":"CI","description":"CI","filePatterns":["["]}',
    ],
)
def test_bad_metadata(
    tmp_path: Path,
    write_file: FileWriter,
    metadata: str,
) -> None:
    """
    Verify invalid template metadata fails full checking but passes pins-only
    mode.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Per-test temporary directory for files and isolated consumer
        repositories.
    write_file : FileWriter
        Fixture writer that creates parent directories and writes UTF-8
        repository files.
    metadata : str
        Metadata text selected for the parsing or validation scenario.
    """
    write_file('templates/ci.yml', 'name: CI')
    write_file('templates/ci.properties.json', metadata)
    config = AutomationConfig(
        tmp_path,
        workflow_globs=(),
        template_globs=('templates/*.yml',),
    )
    assert validate(config)
    assert validate(config, pins_only=True) == []


@pytest.mark.parametrize(
    'step,ok',
    [
        ('{run: echo ok, shell: bash}', True),
        ('{run: echo ok}', False),
        ('{run: echo ok, shell: ""}', False),
        ('{run: echo ok, uses: ./local, shell: bash}', False),
        ('{name: missing}', False),
    ],
)
def test_composite_structure(
    tmp_path: Path,
    write_file: FileWriter,
    step: str,
    ok: bool,
) -> None:
    """
    Verify composite step structure and shell requirements for each candidate.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Per-test temporary directory for files and isolated consumer
        repositories.
    write_file : FileWriter
        Fixture writer that creates parent directories and writes UTF-8
        repository files.
    step : str
        YAML composite step inserted into an otherwise valid action document.
    ok : bool
        Whether the parameterized scenario should return no validation
        failures.
    """
    write_file(
        'actions/test/action.yaml',
        f'name: Test\ndescription: Test\nruns:\n  using: composite\n  steps: [{step}]',
    )
    config = AutomationConfig(
        tmp_path,
        workflow_globs=(),
        action_globs=('actions/*/action.yaml',),
    )
    assert (validate(config) == []) is ok


@pytest.mark.parametrize(
    'source',
    [
        'on: {push: null}',
        'on: {workflow_call: []}',
        'on: {workflow_call: {inputs: {x: {type: invalid}}}}',
    ],
)
def test_invalid_workflow_target(
    tmp_path: Path,
    write_file: FileWriter,
    source: str,
) -> None:
    """
    Verify local workflow calls reject missing or invalid input contracts.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Per-test temporary directory for files and isolated consumer
        repositories.
    write_file : FileWriter
        Fixture writer that creates parent directories and writes UTF-8
        repository files.
    source : str
        YAML document text selected for the validation scenario.
    """
    write_file('target.yml', source)
    write_file('.github/workflows/ci.yml', 'jobs: {call: {uses: ./target.yml}}')
    assert validate(AutomationConfig(tmp_path))


@pytest.mark.parametrize(
    'values,ok',
    [('{}', False), ('{path: src}', True), ('{path: src, extra: x}', False)],
)
def test_local_action_inputs(
    tmp_path: Path,
    write_file: FileWriter,
    values: str,
    ok: bool,
) -> None:
    """
    Verify local action calls enforce required and declared input names.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Per-test temporary directory for files and isolated consumer
        repositories.
    write_file : FileWriter
        Fixture writer that creates parent directories and writes UTF-8
        repository files.
    values : str
        YAML with mapping supplied to the local action or reusable workflow
        call.
    ok : bool
        Whether the parameterized scenario should return no validation
        failures.
    """
    write_file('actions/test/action.yml', 'inputs: {path: {required: true}}')
    write_file(
        '.github/workflows/ci.yml',
        f'steps: [{{uses: ./actions/test, with: {values}}}]',
    )
    assert (validate(AutomationConfig(tmp_path)) == []) is ok


def test_optional_configuration(
    tmp_path: Path,
    write_file: FileWriter,
) -> None:
    """
    Verify automation opt-in and an explicit empty discovery list are honored.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Per-test temporary directory for files and isolated consumer
        repositories.
    write_file : FileWriter
        Fixture writer that creates parent directories and writes UTF-8
        repository files.
    """
    assert not load_automation_config(tmp_path).configured
    write_file('pyproject.toml', '[tool.popo.automation]\nworkflow-globs = []')
    config = load_automation_config(tmp_path)
    assert config.configured
    assert validate(config) == []


def test_orphan_missing_and_escaping_files(
    tmp_path: Path,
    write_file: FileWriter,
) -> None:
    """
    Verify missing templates, metadata, orphan companions, and symlink escapes.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Per-test temporary directory for files and isolated consumer
        repositories.
    write_file : FileWriter
        Fixture writer that creates parent directories and writes UTF-8
        repository files.
    """
    config = AutomationConfig(
        tmp_path,
        workflow_globs=(),
        template_globs=('templates/*.yml',),
    )
    assert 'no automation files match' in validate(config)[0]
    write_file('templates/ci.yml', 'name: CI')
    assert validate(config)  # Missing metadata.
    write_file('templates/ci.properties.json', '{"name":"CI","description":"CI"}')
    orphan = write_file('templates/other.properties.json', '{}')
    assert 'orphan template metadata' in validate(config)[0]
    orphan.unlink()
    outside = write_file('outside/ci.yml', 'name: CI')
    link = tmp_path / 'templates/link.yml'
    link.symlink_to(outside)
    confined = replace(config, root=tmp_path / 'templates', template_globs=('*.yml',))
    assert any('escapes repository' in failure for failure in validate(confined))


def test_overlapping_categories_fail(
    tmp_path: Path,
    write_file: FileWriter,
) -> None:
    """
    Verify conflicting discovery categories produce a diagnostic.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Per-test temporary directory for files and isolated consumer
        repositories.
    write_file : FileWriter
        Fixture writer that creates parent directories and writes UTF-8
        repository files.
    """
    write_file('ci.yml', 'uses: upstream/action@main')
    config = AutomationConfig(
        tmp_path,
        workflow_globs=('ci.yml',),
        yaml_globs=('*.yml',),
    )
    assert any('conflicting automation categories' in item for item in validate(config))


@pytest.mark.parametrize(
    'reference,template,ok',
    [
        ('example/library/.github/workflows/target.yml@RELEASE_SHA', True, True),
        ('example/library/.github/workflows/target.yml@RELEASE_SHA', False, False),
        ('example/library/.github/workflows/target.yml@main', True, False),
        ('other/library/action@RELEASE_SHA', True, False),
        ('example/library/missing.yml@RELEASE_SHA', True, False),
        ('upstream/action@' + 'a' * 40, True, True),
    ],
)
def test_placeholder_scope(
    tmp_path: Path,
    write_file: FileWriter,
    reference: str,
    template: bool,
    ok: bool,
) -> None:
    """
    Verify placeholder exemptions depend on template scope and existing self
    targets.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Per-test temporary directory for files and isolated consumer
        repositories.
    write_file : FileWriter
        Fixture writer that creates parent directories and writes UTF-8
        repository files.
    reference : str
        Automation uses value selected for the pin or target-resolution
        scenario.
    template : bool
        Whether the caller is discovered as a template rather than an ordinary
        workflow.
    ok : bool
        Whether the parameterized scenario should return no validation
        failures.
    """
    write_file('.github/workflows/target.yml', 'on: {workflow_call: null}')
    path = write_file('templates/ci.yml', f'jobs: {{call: {{uses: {reference}}}}}')
    write_file('templates/ci.properties.json', '{"name":"CI","description":"CI"}')
    before = path.read_bytes()
    config = AutomationConfig(
        tmp_path,
        template_globs=('templates/*.yml',) if template else (),
        workflow_globs=('.github/workflows/*.yml',)
        if template
        else ('templates/*.yml',),
        local_repositories=('example/library',),
        template_placeholder_refs=('RELEASE_SHA',),
    )
    for pins_only in (False, True):
        assert (validate(config, pins_only=pins_only) == []) is ok
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    ('values', 'message'),
    [
        ('{}', 'missing required input'),
        ('{extra: x}', 'unknown inputs'),
        ('{text: false}', 'wrong type'),
        ('{text: yes, count: true}', 'wrong type'),
        ('{text: yes, enabled: yes}', 'wrong type'),
        ('[]', 'with must be a mapping'),
        ('{text: yes, enabled: true, count: 2}', ''),
        ('{text: "${{ inputs.text }}", count: "${{ inputs.count }}"}', ''),
    ],
)
def test_workflow_inputs(
    tmp_path: Path,
    write_file: FileWriter,
    values: str,
    message: str,
) -> None:
    """
    Verify reusable workflow input names, required values, and supplied types.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Per-test temporary directory for files and isolated consumer
        repositories.
    write_file : FileWriter
        Fixture writer that creates parent directories and writes UTF-8
        repository files.
    values : str
        YAML with mapping supplied to the local action or reusable workflow
        call.
    message : str
        Expected diagnostic substring; an empty string selects a successful
        case.
    """
    write_file(
        '.github/workflows/target.yml',
        """on:
  workflow_call:
    inputs:
      text: {required: true, type: string}
      enabled: {type: boolean}
      count: {type: number}
""",
    )
    write_file(
        '.github/workflows/caller.yml',
        'jobs:\n  call:\n    uses: ./.github/workflows/target.yml\n'
        f'    with: {values}\n',
    )
    failures = validate(AutomationConfig(tmp_path))
    assert bool(failures) == bool(message)
    if message:
        assert message in failures[0]


def test_yaml_only_and_recursive_alias(
    tmp_path: Path,
    write_file: FileWriter,
) -> None:
    """
    Verify generic YAML skips pin checks and recursive aliases terminate
    traversal.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Per-test temporary directory for files and isolated consumer
        repositories.
    write_file : FileWriter
        Fixture writer that creates parent directories and writes UTF-8
        repository files.
    """
    write_file('form.yml', 'form: &form {uses: arbitrary, nested: *form}')
    config = AutomationConfig(tmp_path, workflow_globs=(), yaml_globs=('form.yml',))
    assert validate(config) == []
    assert validate(replace(config, workflow_globs=('form.yml',), yaml_globs=()))
