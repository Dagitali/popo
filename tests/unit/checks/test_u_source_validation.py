"""
:mod:`tests.unit.checks.test_u_source_validation` module.

Verify ordered source findings and single-pass inspector consumption.
"""

from pathlib import Path
from unittest.mock import Mock, call

import pytest

from popo.checks import _python_declarations, _source_validation
from popo.config.source_checks import SourceCheckConfig

# SECTION: TESTS


class TestParsedSourceFindings:
    """Preserve limit, documentation and convention evaluation contracts."""

    @pytest.mark.parametrize('single_pass', (False, True))
    def test_findings_preserve_order_and_duplicates(
        self,
        tmp_path: Path,
        single_pass: bool,
    ) -> None:
        """
        Collect list or iterator findings after physical source limits.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Lexical consumer root; no files are read or written.
        single_pass : bool
            Supply single-pass iterators instead of reusable lists.
        """
        source = '"""Overview."""'
        parsed = _python_declarations.parse(source)
        settings: dict[str, object] = {'documentation-width': 5, 'max-file-lines': 0}
        config = SourceCheckConfig(tmp_path, 'python-source', (), (), settings)
        inspectors = Mock()
        documentation = ['documentation', 'documentation']
        conventions = ['convention']
        inspectors.documentation.return_value = (
            iter(documentation) if single_pass else documentation
        )
        inspectors.conventions.return_value = (
            iter(conventions) if single_pass else conventions
        )
        assert _source_validation.parsed_source_findings(
            parsed,
            config,
            tmp_path / 'source.py',
            [source],
            inspectors.documentation,
            inspectors.conventions,
        ) == [
            'source.py: file exceeds configured line limit',
            'source.py:1: documentation line too long',
            'documentation',
            'documentation',
            'convention',
        ]
        assert inspectors.mock_calls == [
            call.documentation(parsed, config, 'source.py'),
            call.conventions(parsed, config, 'source.py'),
        ]
        assert documentation == ['documentation', 'documentation']
        assert conventions == ['convention']
        assert settings == {'documentation-width': 5, 'max-file-lines': 0}

    @pytest.mark.parametrize('stage', ('documentation', 'conventions'))
    def test_iteration_failure_prevents_partial_success(
        self,
        tmp_path: Path,
        stage: str,
    ) -> None:
        """
        Propagate deferred inspector failures before invoking later stages.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Lexical consumer root used without filesystem access.
        stage : str
            Inspector whose iterator fails after yielding one finding.
        """
        parsed = _python_declarations.parse('')
        config = SourceCheckConfig(
            tmp_path,
            'python-source',
            (),
            (),
            {'documentation-width': 79, 'max-file-lines': 1000},
        )
        error = RuntimeError('inspector failed')
        inspectors = Mock()
        inspectors.documentation.return_value = iter(())
        inspectors.conventions.return_value = iter(())
        getattr(inspectors, stage).return_value = iter(
            Mock(side_effect=('partial', error)),
            None,
        )
        with pytest.raises(
            RuntimeError,
            match='inspector failed',
            check=lambda raised: raised is error,
        ):
            _source_validation.parsed_source_findings(
                parsed,
                config,
                tmp_path / 'source.py',
                [],
                inspectors.documentation,
                inspectors.conventions,
            )
        inspectors.documentation.assert_called_once_with(parsed, config, 'source.py')
        if stage == 'documentation':
            inspectors.conventions.assert_not_called()
        else:
            inspectors.conventions.assert_called_once_with(parsed, config, 'source.py')


# !SECTION
