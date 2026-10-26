"""
:mod:`tests.unit.configs.test_u_files` module.

Reject malformed required-file and header policies before source inspection.
"""

from pathlib import Path

import pytest

from popo.config import ConfigurationError
from popo.config.files import load_headers_config, load_required_files_config
from tests.support.files import FileWriter

# SECTION: TESTS


class TestFilePolicyConfig:
    """Keep opt-in policy data independent from consumer package metadata."""

    def test_absent_settings_are_opt_in(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Leave existing consumers unaffected when file tables are
        absent.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated temporary consumer root.
        """
        assert load_required_files_config(tmp_path) is None
        assert load_headers_config(tmp_path) is None

    @pytest.mark.parametrize(
        'extra',
        [
            'format = "unsupported"',
            'prefix = "{unknown}"',
            'prefix = "{project.name}"',
            'prefix = "{project!r}"',
            'prefix = "{project:10}"',
            'prefix = "{"',
            'patterns = ["../outside"]',
            'patterns = []',
            'patterns = [1]',
            'purpose-required = "false"',
            'unknown = true',
            'first-line = true',
            'first-line = "x"\nfirst-line-prefix = "y"',
            'required-text = [false]',
            'preamble-prefixes = "schema"',
        ],
    )
    def test_invalid_header_rules(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        extra: str,
    ) -> None:
        """
        Reject malformed patterns, templates and directive contracts.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated temporary consumer root.
        write_file : FileWriter
            UTF-8 writer creating synthetic policy inputs.
        extra : str
            Malformed header configuration overriding valid fixture fields.
        """
        fields = {
            'patterns': '["*.py"]',
            'format': '"python"',
            'prefix': '"{filename}"',
        }
        for line in extra.splitlines():
            key, value = line.split('=', 1)
            fields[key.strip()] = value.strip()
        body = (
            '[tool.popo.headers]\nproject = "Sample"\nnotice = "Copyright"\n'
            '[[tool.popo.headers.rules]]\n'
        )
        write_file(
            'pyproject.toml',
            body + '\n'.join(f'{key} = {value}' for key, value in fields.items()),
        )
        with pytest.raises(ConfigurationError):
            load_headers_config(tmp_path)

    @pytest.mark.parametrize(
        'extra',
        [
            'unknown = true',
            'project = false',
            'ignored-directories = ["../outside"]',
            'ignored-directories = ["*"]',
            'exceptions = "skip"',
            'rules = []',
        ],
    )
    def test_invalid_header_tables(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        extra: str,
    ) -> None:
        """
        Fail malformed top-level settings instead of silently weakening
        scope.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated temporary consumer root.
        write_file : FileWriter
            UTF-8 writer creating synthetic policy inputs.
        extra : str
            Malformed header configuration overriding valid fixture fields.
        """
        identity = '' if extra.startswith('project =') else 'project = "Sample"\n'
        rules = (
            ''
            if extra.startswith('rules =')
            else (
                '\n[[tool.popo.headers.rules]]\npatterns=["*"]\nformat="raw"\nprefix="X"'
            )
        )
        write_file(
            'pyproject.toml',
            '[tool.popo.headers]\n' + identity + 'notice="Copyright"\n' + extra + rules,
        )
        with pytest.raises(ConfigurationError):
            load_headers_config(tmp_path)

    @pytest.mark.parametrize(
        'entry',
        [
            'patterns = ["*.bin"]',
            'patterns = []\nreason = "Binary"',
            'patterns = ["../outside"]\nreason = "Binary"',
            'patterns = ["*.bin"]\nreason = "   "',
            'patterns = ["*.bin"]\nreason = "Binary"\nunknown = true',
        ],
    )
    def test_invalid_preservation_exceptions(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        entry: str,
    ) -> None:
        """
        Require safe exception patterns and a meaningful explicit reason.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated consumer root.
        write_file : FileWriter
            Writer for the malformed policy fixture.
        entry : str
            Invalid exception fields supplied by the scenario.
        """
        write_file(
            'pyproject.toml',
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
        with pytest.raises(ConfigurationError):
            load_headers_config(tmp_path)

    @pytest.mark.parametrize(
        'setting',
        [
            'required = []',
            'required = "README.md"',
            'other = []',
            'required = ["../outside"]',
            'required = ["/absolute"]',
            'required = ["*.md"]',
            'required = ["C:/outside"]',
            'required = ["same", "same"]',
            'required = [1]',
        ],
    )
    def test_invalid_required_policy(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        setting: str,
    ) -> None:
        """
        Reject empty, unsafe, ambiguous and misspelled required-file
        inputs.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated temporary consumer root.
        write_file : FileWriter
            UTF-8 writer creating synthetic policy inputs.
        setting : str
            Invalid required-file configuration supplied by the scenario.
        """
        write_file('pyproject.toml', '[tool.popo.files]\n' + setting)
        with pytest.raises(ConfigurationError):
            load_required_files_config(tmp_path)

    def test_valid_header_policy(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Keep identity, ordered formats and explicit exception reasons
        intact.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated temporary consumer root.
        write_file : FileWriter
            UTF-8 writer creating synthetic policy inputs.
        """
        write_file(
            'pyproject.toml',
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
        config = load_headers_config(tmp_path)
        assert config is not None and config.project == 'Sample'
        assert config.rules[0].format == 'python'
        assert config.exceptions[0].reason == 'Binary artwork'

    def test_valid_required_policy(
        self,
        tmp_path: Path,
        write_file: FileWriter,
    ) -> None:
        """
        Resolve root paths while leaving existence checks to the
        validator.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated temporary consumer root.
        write_file : FileWriter
            UTF-8 writer creating synthetic policy inputs.
        """
        write_file('pyproject.toml', '[tool.popo.files]\nrequired = ["README.md"]')
        config = load_required_files_config(tmp_path)
        assert config is not None and config.required == ('README.md',)
        assert config.root == tmp_path.resolve()


# !SECTION
