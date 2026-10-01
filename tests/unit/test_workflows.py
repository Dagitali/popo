"""
:mod:`tests.unit.test_workflows` module.

Protect configurable routing and publication boundaries.
"""

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

# SECTION: TYPE ALIASES


type WorkflowLoader = Callable[[str], dict[str, Any]]


# !SECTION


# SECTION: FIXTURES


@pytest.fixture(name='workflow')
def workflow_fixture(
    repository_root: Path,
) -> WorkflowLoader:
    """
    Provide a loader for workflow documents in the checkout.

    Parameters
    ----------
    repository_root : pathlib.Path
        Checkout containing .github/workflows.

    Returns
    -------
    WorkflowLoader
        Callable reading a named workflow with :class:`yaml.BaseLoader`,
        preserving scalar values such as on and false as strings.

    Notes
    -----
    The fixture itself does not read files. Loading happens when the returned
    callable is invoked; read, decode, and YAML errors propagate from that
    call. The loader performs no schema validation or workflow execution.
    """

    def load(name: str) -> dict[str, Any]:
        """
        Read a checkout workflow with string-valued YAML scalars.

        Parameters
        ----------
        name : str
            Workflow filename joined to the fixture's .github/workflows
            directory.

        Returns
        -------
        dict[str, typing.Any]
            Parsed workflow document, narrowed to a dictionary for test
            assertions.

        Raises
        ------
        OSError, UnicodeError
            If reading or UTF-8 decoding fails.
        yaml.YAMLError
            If the workflow is not valid YAML.

        Notes
        -----
        :class:`yaml.BaseLoader` preserves all scalar values as strings. The
        :func:`typing.cast` does not validate the parsed document's shape.
        Supply trusted fixture filenames; path containment is not enforced by
        this helper.
        """
        path = repository_root / '.github' / 'workflows' / name
        return cast(
            dict[str, Any],
            yaml.load(path.read_text(encoding='utf-8'), Loader=yaml.BaseLoader),
        )

    return load


# !SECTION


# SECTION: TESTS


class TestWorkflows:
    """
    Verify workflows contracts.

    Notes
    -----
    Inspect checkout workflow documents and execute only extracted routing/tag
    guards in controlled local fixtures. Do not dispatch hosted workflows or
    publish releases; tag-gate Git operations stay in a temporary repository.
    """

    def test_disposable_installation_is_manual_and_read_only(
        self,
        workflow: WorkflowLoader,
    ) -> None:
        """
        Verify installation automation triggers and read permissions.

        Parameters
        ----------
        workflow : WorkflowLoader
            Loader reading checkout workflow YAML with scalar values preserved
            as strings.
        """
        document = workflow('deployment-test.yml')
        assert set(document['on']) == {'workflow_dispatch'}
        assert document['permissions'] == {}
        job = document['jobs']['install-test']
        assert job['permissions'] == {'contents': 'read'}
        assert job['strategy']['matrix']['python-version'] == ['3.13', '3.14']
        assert len(job['strategy']['matrix']['os']) == 3
        assert job['steps'][-1]['run'] == 'python -m pytest tests/meta tests/e2e'

    @pytest.mark.parametrize(
        ('rules', 'head', 'repository', 'event', 'success'),
        [
            ({}, 'topic/change', 'fork/project', 'pull_request', True),
            (
                {'main': {'head_pattern': 'release/.*', 'same_repository': True}},
                'release/1.0.0',
                'owner/project',
                'pull_request',
                True,
            ),
            (
                {'main': {'head_pattern': 'release/.*', 'same_repository': True}},
                'release/1.0.0',
                'fork/project',
                'pull_request',
                False,
            ),
            (
                {'main': {'head_pattern': 'release/.*'}},
                'feature/change',
                'owner/project',
                'pull_request',
                False,
            ),
            ({'main': {'head_pattern': 'release/.*'}}, '', '', 'merge_group', True),
            ([], 'topic', 'owner/project', 'pull_request', False),
            (
                {'main': {'head_pattern': '['}},
                'topic',
                'owner/project',
                'pull_request',
                False,
            ),
            (
                {'main': {'head_pattern': '.*', 'same_repository': 'false'}},
                'topic',
                'owner/project',
                'pull_request',
                False,
            ),
            (
                {'main': {'head_pattern': '.*', 'typo': True}},
                'topic',
                'owner/project',
                'pull_request',
                False,
            ),
        ],
    )
    def test_pr_routing(
        self,
        workflow: WorkflowLoader,
        rules: object,
        head: str,
        repository: str,
        event: str,
        success: bool,
    ) -> None:
        """
        Verify routing accepts or rejects each configured event and branch.

        Parameters
        ----------
        workflow : WorkflowLoader
            Loader reading checkout workflow YAML with scalar values preserved
            as strings.
        rules : object
            Routing-policy object serialized into the workflow script
            environment.
        head : str
            Source branch name supplied to the routing guard.
        repository : str
            Source repository name used to evaluate same-repository
            restrictions.
        event : str
            GitHub event name determining pull-request or merge-group routing
            behavior.
        success : bool
            Whether the routing guard should exit successfully.
        """
        script = workflow('pr.yml')['jobs']['guard']['steps'][0]['run']
        environment = os.environ | {
            'RULES': json.dumps(rules),
            'BASE_REF': 'main',
            'HEAD_REF': head,
            'HEAD_REPOSITORY': repository,
            'REPOSITORY': 'owner/project',
            'EVENT_NAME': event,
        }
        result = subprocess.run(
            [sys.executable, '-c', script],
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert (result.returncode == 0) is success, result.stderr

    def test_publication_requires_explicit_opt_in(
        self,
        workflow: WorkflowLoader,
    ) -> None:
        """
        Verify publication gates and consumption of validated artifacts.

        Parameters
        ----------
        workflow : WorkflowLoader
            Loader reading checkout workflow YAML with scalar values preserved
            as strings.
        """
        document = workflow('cd.yml')
        assert (
            document['on']['workflow_dispatch']['inputs']['publish']['default']
            == 'false'
        )
        release = document['jobs']['release']
        for gate in (
            'workflow_dispatch',
            'inputs.publish',
            'ENABLE_RELEASE_PUBLISHING',
            'refs/heads/',
            'default_branch',
        ):
            assert gate in release['if']
        assert release['needs'] == 'build'
        assert release['environment'] == 'release'
        assert release['permissions'] == {'contents': 'write'}
        assert document['jobs']['build']['permissions'] == {'contents': 'read'}
        assert not any('checkout@' in step.get('uses', '') for step in release['steps'])
        command = release['steps'][-1]['run']
        assert '--verify-tag' in command and '--latest=false' in command
        assert 'EXPECTED_TAG_OBJECT' in command and 'sha256sum --check' in command
        assert 'upload --clobber' not in command

    @pytest.mark.skipif(
        shutil.which('bash') is None or shutil.which('git') is None,
        reason='Tag gate requires Bash and Git',
    )
    @pytest.mark.parametrize(
        'case',
        ['valid', 'lightweight', 'missing', 'invalid', 'off-branch'],
    )
    def test_release_tag_gate(
        self,
        workflow: WorkflowLoader,
        tmp_path: Path,
        case: str,
    ) -> None:
        """
        Verify the tag gate requires an annotated, integrated release.

        Parameters
        ----------
        workflow : WorkflowLoader
            Loader reading checkout workflow YAML with scalar values preserved
            as strings.
        tmp_path : pathlib.Path
            Per-test temporary directory for files and isolated consumer
            repositories.
        case : str
            Tag fixture variant: valid, lightweight, missing, invalid, or off-
            branch.
        """
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith('GIT_')
        } | {'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}

        def git(*arguments: str) -> subprocess.CompletedProcess[str]:
            """
            Run a Git fixture command with isolated identity and disabled
            signing/hooks.

            Parameters
            ----------
            *arguments : str
                Git subcommand and arguments used to prepare the temporary
                repository.

            Returns
            -------
            subprocess.CompletedProcess[str]
                Successful command result with captured stdout and stderr.

            Raises
            ------
            subprocess.CalledProcessError
                If Git exits unsuccessfully.
            subprocess.TimeoutExpired
                If the command exceeds 30 seconds.
            OSError, UnicodeError
                If startup or captured-output decoding fails.

            Notes
            -----
            Commands operate in the enclosing test's ``tmp_path``.
            Global/system Git configuration and inherited GIT_ variables are
            excluded; identity, signing, and hook overrides are supplied
            explicitly. Repository mutations create local test fixtures rather
            than changing the checkout.
            """
            return subprocess.run(
                [
                    'git',
                    '-c',
                    'user.name=Workflow Test',
                    '-c',
                    'user.email=test@example.invalid',
                    '-c',
                    'commit.gpgsign=false',
                    '-c',
                    'tag.gpgsign=false',
                    '-c',
                    f'core.hooksPath={tmp_path / 'no-hooks'}',
                    *arguments,
                ],
                cwd=tmp_path,
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
                env=environment,
            )

        git('init', '-b', 'main')
        git('commit', '--allow-empty', '-m', 'Fixture root')
        git('update-ref', 'refs/remotes/origin/main', 'HEAD')
        if case == 'off-branch':
            git('commit', '--allow-empty', '-m', 'Not integrated')
        if case == 'lightweight':
            git('tag', 'v1.2.3')
        elif case != 'missing':
            git('tag', '-a', 'v1.2.3', '-m', 'Fixture tag')
        script = next(
            step['run']
            for step in workflow('cd.yml')['jobs']['build']['steps']
            if step.get('id') == 'tag'
        )
        result = subprocess.run(
            ['bash', '-c', script],
            timeout=30,
            cwd=tmp_path,
            capture_output=True,
            text=True,
            env=environment
            | {
                'RELEASE_TAG': 'bad/tag' if case == 'invalid' else 'v1.2.3',
                'DEFAULT_BRANCH': 'main',
                'GITHUB_OUTPUT': str(tmp_path / 'output'),
            },
        )
        assert (result.returncode == 0) is (case == 'valid'), result.stderr


# !SECTION
