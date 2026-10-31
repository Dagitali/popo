"""
:mod:`tests.unit.config.test_u_files` module.

Reject malformed required-file and header policies before source inspection.
"""

import json
import re
from collections.abc import Callable
from pathlib import Path

import pytest

from popo.config import ConfigurationError
from popo.config.files import load_headers_config, load_required_files_config
from tests.support.files import FileWriter, snapshot_files

# SECTION: FIXTURES


@pytest.fixture(
    name='write_policy',
    params=('popo.toml', 'pyproject.toml'),
)
def write_policy_fixture(
    request: pytest.FixtureRequest,
    write_file: FileWriter,
) -> Callable[[str], Path]:
    """
    Write the same file-policy contract under either supported namespace.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Standalone or embedded policy source selected for this scenario.
    write_file : FileWriter
        Shared UTF-8 writer creating isolated consumer inputs.

    Returns
    -------
    collections.abc.Callable[[str], pathlib.Path]
        Writer accepting embedded fixture TOML, including array-table headers.
        Standalone cases remove tool.popo only from leading table headers;
        literal field values remain unchanged. This is a fixture namespace
        transform, not a general TOML parser or configuration merger.
    """
    filename = str(request.param)

    def write(
        settings: str,
    ) -> Path:
        """
        Preserve policy values while selecting the fixture's table namespace.

        Parameters
        ----------
        settings : str
            File-policy fixture with tool.popo table or array-table headers.

        Returns
        -------
        pathlib.Path
            Written standalone or embedded policy file.
        """
        if filename == 'popo.toml':
            settings = re.sub(r'(?m)^(\[\[?)tool\.popo\.', r'\1', settings)
        return write_file(filename, settings)

    return write


# !SECTION


# SECTION: TESTS


class TestFilePolicyConfig:
    """Keep opt-in policy data independent from consumer package metadata."""

    def test_absent_settings_are_opt_in(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Verify absent settings are opt in.

        Leave existing consumers unaffected when file tables are absent.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated temporary consumer root.
        """
        assert load_required_files_config(tmp_path) is None
        assert load_headers_config(tmp_path) is None

    @pytest.mark.parametrize(
        'overrides,message',
        [
            ({'format': 'unsupported'}, 'unsupported header format'),
            *(
                ({'prefix': prefix}, 'invalid header prefix template')
                for prefix in (
                    '{unknown}',
                    '{project.name}',
                    '{project!r}',
                    '{project:10}',
                    '{',
                )
            ),
            ({'patterns': ['../outside']}, 'must stay inside the repository'),
            ({'patterns': []}, 'header patterns must not be empty'),
            ({'patterns': [1]}, 'header patterns must be an array'),
            ({'purpose-required': 'false'}, 'purpose-required must be boolean'),
            ({'unknown': True}, 'unknown header rule setting'),
            ({'first-line': True}, 'use one string first-line or first-line-prefix'),
            (
                {'first-line': 'x', 'first-line-prefix': 'y'},
                'use one string first-line or first-line-prefix',
            ),
            ({'required-text': [False]}, 'required-text must be an array'),
            ({'preamble-prefixes': 'schema'}, 'preamble-prefixes must be an array'),
        ],
    )
    def test_invalid_header_rules(
        self,
        tmp_path: Path,
        write_policy: Callable[[str], Path],
        overrides: dict[str, object],
        message: str,
    ) -> None:
        """
        Reject malformed patterns, templates and directive contracts.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated temporary consumer root.
        write_policy : collections.abc.Callable
            UTF-8 writer creating synthetic policy inputs.
        overrides : dict[str, object]
            Malformed header configuration overriding valid fixture fields.
        message : str
            Specific diagnostic for the intended rule-contract violation.
        """
        fields = {
            'patterns': ['*.py'],
            'format': 'python',
            'prefix': '{filename}',
        } | overrides
        body = (
            '[tool.popo.headers]\nproject = "Sample"\nnotice = "Copyright"\n'
            '[[tool.popo.headers.rules]]\n'
        )
        write_policy(
            body
            + '\n'.join(
                f'{key} = {json.dumps(value)}' for key, value in fields.items()
            ),
        )
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError, match=message):
            load_headers_config(tmp_path)
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        'overrides,message',
        [
            ({'unknown': 'true'}, 'unknown tool.popo.headers setting'),
            ({'project': 'false'}, 'project must be a non-empty string'),
            (
                {'ignored-directories': '["../outside"]'},
                'ignored-directories must contain literal directory names',
            ),
            (
                {'ignored-directories': '["*"]'},
                'ignored-directories must contain literal directory names',
            ),
            ({'exceptions': '"skip"'}, 'headers.exceptions must be an array'),
            ({'rules': '[]'}, 'headers.rules must be a nonempty array'),
        ],
    )
    def test_invalid_header_tables(
        self,
        tmp_path: Path,
        write_policy: Callable[[str], Path],
        overrides: dict[str, str],
        message: str,
    ) -> None:
        """
        Fail malformed top-level settings instead of silently weakening scope.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated temporary consumer root.
        write_policy : collections.abc.Callable
            UTF-8 writer creating synthetic policy inputs.
        overrides : dict[str, str]
            Raw TOML field values replacing otherwise valid header settings.
        message : str
            Diagnostic identifying the intended top-level contract violation.
        """
        fields = {
            'project': '"Sample"',
            'notice': '"Copyright"',
            'rules': '[{patterns=["*"],format="raw",prefix="X"}]',
        } | overrides
        write_policy(
            '[tool.popo.headers]\n'
            + '\n'.join(f'{key} = {value}' for key, value in fields.items()),
        )
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError, match=message):
            load_headers_config(tmp_path)
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        'entry,message',
        [
            ('patterns = ["*.bin"]', 'requires patterns and reason'),
            (
                'patterns = []\nreason = "Binary"',
                'exception patterns must not be empty',
            ),
            (
                'patterns = ["../outside"]\nreason = "Binary"',
                'exception patterns must stay inside the repository',
            ),
            ('patterns = ["*.bin"]\nreason = "   "', 'reason must not be blank'),
            (
                'patterns = ["*.bin"]\nreason = "Binary"\nunknown = true',
                'requires patterns and reason',
            ),
        ],
    )
    def test_invalid_preservation_exceptions(
        self,
        tmp_path: Path,
        write_policy: Callable[[str], Path],
        entry: str,
        message: str,
    ) -> None:
        """
        Require safe exception patterns and a meaningful explicit reason.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated consumer root.
        write_policy : collections.abc.Callable
            Writer for the malformed policy fixture.
        entry : str
            Invalid exception fields supplied by the scenario.
        message : str
            Specific preservation-contract diagnostic expected for the input.
        """
        write_policy(
            """[tool.popo.headers]
project = "Sample"
notice = "Copyright"
[[tool.popo.headers.rules]]
patterns = ["*"]
format = "raw"
prefix = "HEADER"
[[tool.popo.headers.exceptions]]
"""
            + entry,
        )
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError, match=message):
            load_headers_config(tmp_path)
        assert snapshot_files(tmp_path) == before

    @pytest.mark.parametrize(
        'setting,message',
        [
            ('required = []', 'files.required must not be empty'),
            ('required = "README.md"', 'files.required must be an array'),
            ('other = []', 'requires only required'),
            *(
                (
                    f'required = {json.dumps([path])}',
                    'files.required must stay inside the repository',
                )
                for path in (
                    '../outside',
                    '/absolute',
                    '*.md',
                    'C:/outside',
                    r'nested\outside',
                    'file?.md',
                    '[abc].md',
                )
            ),
            ('required = ["same", "same"]', 'files.required contains duplicates'),
            ('required = [1]', 'files.required must be an array'),
        ],
    )
    def test_invalid_required_policy(
        self,
        tmp_path: Path,
        write_policy: Callable[[str], Path],
        setting: str,
        message: str,
    ) -> None:
        """
        Verify invalid required policy.

        Reject empty, unsafe, ambiguous and misspelled required-file inputs.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated temporary consumer root.
        write_policy : collections.abc.Callable
            UTF-8 writer creating synthetic policy inputs.
        setting : str
            Invalid required-file configuration supplied by the scenario.
        message : str
            Specific path, field-shape or duplicate diagnostic expected.
        """
        write_policy('[tool.popo.files]\n' + setting)
        before = snapshot_files(tmp_path)
        with pytest.raises(ConfigurationError, match=message):
            load_required_files_config(tmp_path)
        assert snapshot_files(tmp_path) == before

    def test_valid_header_policy(
        self,
        tmp_path: Path,
        write_policy: Callable[[str], Path],
    ) -> None:
        """
        Verify valid header policy.

        Keep identity, ordered formats and explicit exception reasons intact.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated temporary consumer root.
        write_policy : collections.abc.Callable
            UTF-8 writer creating synthetic policy inputs.
        """
        write_policy(
            """[tool.popo.headers]
project = "Sample"
notice = "Copyright"
[[tool.popo.headers.rules]]
patterns = ["*.py"]
format = "python"
prefix = "{module} {project} {notice}"
[[tool.popo.headers.exceptions]]
patterns = ["*.bin"]
reason = "Binary artwork"
""",
        )
        before = snapshot_files(tmp_path)
        config = load_headers_config(tmp_path)
        assert config is not None and config.project == 'Sample'
        assert config.rules[0].format == 'python'
        assert config.exceptions[0].reason == 'Binary artwork'
        assert snapshot_files(tmp_path) == before

    def test_valid_required_policy(
        self,
        tmp_path: Path,
        write_policy: Callable[[str], Path],
    ) -> None:
        """
        Verify valid required policy.

        Resolve root paths while leaving existence checks to the validator.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated temporary consumer root.
        write_policy : collections.abc.Callable
            UTF-8 writer creating synthetic policy inputs.
        """
        write_policy('[tool.popo.files]\nrequired = ["README.md"]')
        before = snapshot_files(tmp_path)
        config = load_required_files_config(tmp_path)
        assert config is not None and config.required == ('README.md',)
        assert config.root == tmp_path.resolve()
        assert snapshot_files(tmp_path) == before


# !SECTION
