"""
:mod:`tests.unit.checks.test_u_files` module.

Exercise configured file existence, header syntax and containment boundaries.
"""

import subprocess
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from popo.checks.files import validate_headers, validate_required
from popo.config.files import (
    HeaderException,
    HeaderRule,
    HeadersConfig,
    RequiredFilesConfig,
)
from tests.support.files import FileWriter, snapshot_files

# SECTION: FIXTURES


@pytest.fixture(name='headers')
def headers_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> HeadersConfig:
    """
    Provide a synthetic consumer header policy with no repository coupling.

    Parameters
    ----------
    tmp_path : pathlib.Path
        Isolated source root.
    monkeypatch : pytest.MonkeyPatch
        Isolate discovery from installed Git and inherited Git configuration.

    Returns
    -------
    HeadersConfig
        Ordered hash-comment rule with identity and purpose requirements.
    """
    monkeypatch.setattr(
        'popo.checks.files.subprocess.run',
        Mock(side_effect=FileNotFoundError('Git unavailable in fixture')),
    )
    return HeadersConfig(
        tmp_path,
        'Sample',
        'Copyright Sample',
        (HeaderRule(('*',), 'hash', '{filename}\n{project}\n\n{notice}\n\n'),),
        (),
        ('.git', '.build', '.venv'),
    )


# !SECTION


# SECTION: TESTS


class TestRequiredFilePolicies:
    """
    Verify all checks read synthetic files and preserve consumer contents.
    """

    def test_required_files_report_all_failures(
        self,
        tmp_path: Path,
    ) -> None:
        """
        Distinguish regular files from directories and absent
        resources.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated temporary consumer root.
        """
        (tmp_path / 'present').write_text('present', encoding='utf-8')
        (tmp_path / 'directory').mkdir()
        failures = validate_required(
            RequiredFilesConfig(tmp_path, ('present', 'directory', 'absent')),
        )
        assert failures == [
            'directory: required file does not exist or is not a file',
            'absent: required file does not exist or is not a file',
        ]

    def test_escaping_required_symlinks(
        self,
        tmp_path: Path,
        write_file: FileWriter,
        symlink: Callable[[Path, Path], None],
    ) -> None:
        """
        Reject existing symlink targets outside the configured root.

        Parameters
        ----------
        tmp_path : pathlib.Path
            Isolated temporary consumer root.
        write_file : FileWriter
            UTF-8 writer creating synthetic policy inputs.
        symlink : collections.abc.Callable
            Platform-aware creator for synthetic symbolic links.
        """
        outside = write_file('outside', 'preserved')
        root = tmp_path / 'repo'
        root.mkdir()
        symlink(root / 'required', outside)
        assert (
            'escapes' in validate_required(RequiredFilesConfig(root, ('required',)))[0]
        )


class TestHeaderPolicies:
    """Check header syntax and rule order with independent consumer inputs."""

    @pytest.mark.parametrize(
        ('kind', 'content'),
        [
            ('hash', '# sample\n# Sample\n#\n# Copyright Sample\n#\n# Purpose.\n'),
            (
                'slash',
                '// sample\n// Sample\n//\n// Copyright Sample\n//\n// Purpose.\n',
            ),
            ('html', '<!--\nsample\nSample\n\nCopyright Sample\n\nPurpose.\n-->'),
            (
                'xml',
                '<?xml version="1.0"?>\n<!DOCTYPE sample>\n'
                '<!--\nsample\nSample\n\nCopyright Sample\n\nPurpose.\n-->',
            ),
            ('block', '/*\nsample\nSample\n\nCopyright Sample\n\nPurpose.\n*/'),
            ('python', '"""sample\nSample\n\nCopyright Sample\n\nPurpose."""\n'),
            ('raw', 'sample\nSample\n\nCopyright Sample\n\nPurpose.\n'),
        ],
    )
    def test_comment_formats(
        self,
        headers: HeadersConfig,
        kind: str,
        content: str,
    ) -> None:
        """
        Accept each documented header syntax without changing file
        bytes.

        Parameters
        ----------
        headers : HeadersConfig
            Synthetic identity, formats and source-discovery policy.
        kind : str
            Comment syntax selected for this parameterized scenario.
        content : str
            Synthetic source contents whose observable result is checked.
        """
        source = headers.root / 'sample'
        source.write_text(content, encoding='utf-8')
        rule = replace(headers.rules[0], format=kind)
        original = snapshot_files(headers.root)
        assert validate_headers(replace(headers, rules=(rule,))) == []
        assert snapshot_files(headers.root) == original

    @pytest.mark.parametrize(
        ('first', 'prefix', 'trim', 'before'),
        [
            ('', '#!', False, '#!/bin/bash\n'),
            ('// !$*UTF8*$!', '', False, '// !$*UTF8*$!\n'),
            ('', '// swift-tools-version:', False, '// swift-tools-version: 6.4\n'),
            ('', '# ', True, '# Article\n\n'),
        ],
    )
    @pytest.mark.parametrize('present', [True, False], ids=['present', 'missing'])
    def test_required_directives(
        self,
        headers: HeadersConfig,
        first: str,
        prefix: str,
        trim: bool,
        before: str,
        present: bool,
    ) -> None:
        """
        Require configured directives and preserve their first-line
        position.

        Parameters
        ----------
        headers : HeadersConfig
            Synthetic identity, formats and source-discovery policy.
        first : str
            Exact required first-line directive, or an empty string.
        prefix : str
            Required first-line prefix when no exact directive is supplied.
        trim : bool
            Whether blank lines after the directive may be removed.
        before : str
            Executable or consumer directive placed before the header.
        present : bool
            Include the required directive, or test its absence independently.
        """
        body = 'sample\nSample\n\nCopyright Sample\n\nPurpose.'
        source = headers.root / 'sample'
        rule = replace(
            headers.rules[0],
            format='raw',
            first_line=first,
            first_line_prefix=prefix,
            trim_after_first_line=trim,
        )
        config = replace(headers, rules=(rule,))
        source.write_text((before if present else '') + body, encoding='utf-8')
        original = snapshot_files(headers.root)
        assert validate_headers(config) == (
            []
            if present
            else ['sample: required first-line directive is missing or malformed']
        )
        assert snapshot_files(headers.root) == original

    @pytest.mark.parametrize('preamble', [False, True])
    @pytest.mark.parametrize('notes', ['Maintainer Notes', 'Notes'])
    def test_optional_schema_preamble_and_required_notes(
        self,
        headers: HeadersConfig,
        preamble: bool,
        notes: str,
    ) -> None:
        """
        Keep schema directives above hash headers and require
        maintainer text.

        Parameters
        ----------
        headers : HeadersConfig
            Synthetic identity, formats and source-discovery policy.
        preamble : bool
            Include or omit the optional schema directive.
        notes : str
            Correct maintainer heading or an independently invalid heading.
        """
        body = (
            '# sample\n# Sample\n#\n# Copyright Sample\n#\n# Purpose.\n#\n'
            f'# {notes}\n# - Keep checks read-only.\n'
        )
        rule = replace(
            headers.rules[0],
            required_text=('\n\nMaintainer Notes\n- ',),
            preamble_prefixes=('# yaml-language-server:',),
        )
        config = replace(headers, rules=(rule,))
        source = headers.root / 'sample'
        directive = '# yaml-language-server: schema\n#\n' if preamble else ''
        source.write_text(directive + body, encoding='utf-8')
        original = snapshot_files(headers.root)
        assert validate_headers(config) == (
            []
            if notes == 'Maintainer Notes'
            else ['sample: required header text is missing']
        )
        assert snapshot_files(headers.root) == original

    @pytest.mark.parametrize(
        ('content', 'message'),
        [
            ('wrong identity', 'identity'),
            ('sample\nSample\n\nCopyright Sample\n\n', 'purpose'),
            ('\xff', 'identity'),
        ],
    )
    def test_malformed_headers(
        self,
        headers: HeadersConfig,
        content: str,
        message: str,
    ) -> None:
        """
        Report missing identity or purpose independently of filename
        selection.

        Parameters
        ----------
        headers : HeadersConfig
            Synthetic identity, formats and source-discovery policy.
        content : str
            Synthetic source contents whose observable result is checked.
        message : str
            Expected diagnostic identifying the failed policy boundary.
        """
        (headers.root / 'sample').write_text(content, encoding='utf-8')
        config = replace(headers, rules=(replace(headers.rules[0], format='raw'),))
        assert message in validate_headers(config)[0]

    @pytest.mark.parametrize(
        ('content', 'message'),
        [
            pytest.param(b'def invalid:', 'invalid Python', id='invalid-python'),
            pytest.param(b'\xff\xfe', 'decode', id='undecodable-source'),
        ],
    )
    def test_invalid_python_and_binary_without_exception(
        self,
        headers: HeadersConfig,
        content: bytes,
        message: str,
    ) -> None:
        """
        Fail malformed Python and undecodable source instead of
        skipping it.

        Parameters
        ----------
        headers : HeadersConfig
            Synthetic identity, formats and source-discovery policy.
        content : bytes
            Malformed or undecodable source written independently per case.
        message : str
            Expected diagnostic for the rejected source.
        """
        source = headers.root / 'sample'
        source.write_bytes(content)
        config = replace(headers, rules=(replace(headers.rules[0], format='python'),))
        failures = validate_headers(config)
        assert len(failures) == 1
        assert message in failures[0]
        assert source.read_bytes() == content

    def test_exception_unknown_format_and_ignored_artifacts(
        self,
        headers: HeadersConfig,
    ) -> None:
        """
        Preserve binary exceptions while rejecting unknown maintained
        formats.

        Parameters
        ----------
        headers : HeadersConfig
            Synthetic identity, formats and source-discovery policy.
        """
        (headers.root / '.hidden').write_bytes(b'\xff')
        (headers.root / 'image.bin').write_bytes(b'\xff')
        (headers.root / '.build').mkdir()
        (headers.root / '.build/cache').write_bytes(b'\xff')
        config = replace(
            headers,
            rules=(replace(headers.rules[0], patterns=('*.py',)),),
            exceptions=(HeaderException(('*.bin',), 'Binary asset'),),
        )
        failures = validate_headers(config)
        assert len(failures) == 1
        assert '.hidden: unclassified' in failures[0]

    @pytest.mark.parametrize('specific_first', [True, False])
    def test_rule_order_and_optional_purpose(
        self,
        headers: HeadersConfig,
        specific_first: bool,
    ) -> None:
        """
        Apply the first matching rule and permit explicit purpose
        exceptions.

        Parameters
        ----------
        headers : HeadersConfig
            Synthetic identity, formats and source-discovery policy.
        specific_first : bool
            Place the purpose-exempt rule before or after the generic rule.
        """
        (headers.root / 'sample').write_text('literal', encoding='utf-8')
        specific = HeaderRule(('sample',), 'raw', 'literal', purpose_required=False)
        rules = (
            (specific, *headers.rules) if specific_first else (*headers.rules, specific)
        )
        original = snapshot_files(headers.root)
        assert validate_headers(replace(headers, rules=rules)) == (
            []
            if specific_first
            else ['sample: header does not match configured identity/prefix']
        )
        assert snapshot_files(headers.root) == original

    def test_escaping_header_symlink_even_with_exception(
        self,
        headers: HeadersConfig,
        symlink: Callable[[Path, Path], None],
    ) -> None:
        """
        Reject escapes before reading or exempting the linked contents.

        Parameters
        ----------
        headers : HeadersConfig
            Synthetic identity, formats and source-discovery policy.
        symlink : collections.abc.Callable
            Platform-aware creator for synthetic symbolic links.
        """
        outside = headers.root.parent / (headers.root.name + '-outside')
        outside.write_bytes(b'\xff')
        symlink(headers.root / 'sample', outside)
        config = replace(
            headers,
            exceptions=(HeaderException(('*',), 'Test exception'),),
        )
        assert 'escapes' in validate_headers(config)[0]

    def test_discovery_timeout_is_failure(
        self,
        headers: HeadersConfig,
    ) -> None:
        """
        Bound Git discovery and retain timeout failures as diagnostics.

        Parameters
        ----------
        headers : HeadersConfig
            Synthetic identity, formats and source-discovery policy.
        """
        with patch(
            'popo.checks.files.subprocess.run',
            side_effect=subprocess.TimeoutExpired('git', 30),
        ):
            assert 'discovery failed' in validate_headers(headers)[0]

    def test_tracked_untracked_deleted_and_ignored_sources(
        self,
        headers: HeadersConfig,
    ) -> None:
        """
        Use Git inventory without inspecting deleted or ignored files.

        Parameters
        ----------
        headers : HeadersConfig
            Synthetic identity, formats and source-discovery policy.
        """
        source = headers.root / 'sample'
        source.write_text(
            '# sample\n# Sample\n#\n# Copyright Sample\n#\n# Purpose.',
            encoding='utf-8',
        )
        with patch(
            'popo.checks.files.subprocess.run',
            return_value=subprocess.CompletedProcess([], 0, 'sample\0deleted\0', ''),
        ) as run:
            assert validate_headers(headers) == []
            assert '--others' in run.call_args.args[0]
            assert '--exclude-standard' in run.call_args.args[0]
            assert run.call_args.kwargs['timeout'] == 30

    def test_broken_git_inventory_fails(
        self,
        headers: HeadersConfig,
    ) -> None:
        """
        Report a broken repository rather than silently changing discovery.

        Parameters
        ----------
        headers : HeadersConfig
            Synthetic consumer root and header policy.
        """
        (headers.root / '.git').mkdir()
        with patch(
            'popo.checks.files.subprocess.run',
            return_value=subprocess.CompletedProcess([], 128, '', 'broken repository'),
        ):
            assert validate_headers(headers) == [
                'header source discovery failed: Git source inventory failed',
            ]

    def test_missing_git_uses_local_discovery(
        self,
        headers: HeadersConfig,
    ) -> None:
        """
        Support a non-Git consumer without requiring a Git installation.

        Parameters
        ----------
        headers : HeadersConfig
            Synthetic consumer root and header policy.
        """
        (headers.root / 'sample').write_text('missing header', encoding='utf-8')
        assert validate_headers(headers) == [
            'sample: header does not match configured identity/prefix',
        ]

    def test_read_failures_are_reported(
        self,
        headers: HeadersConfig,
    ) -> None:
        """
        Keep unreadable source files from passing header validation.

        Parameters
        ----------
        headers : HeadersConfig
            Synthetic consumer root and header policy.
        """
        (headers.root / 'sample').write_text('source', encoding='utf-8')
        error = PermissionError('unreadable source')
        with patch.object(Path, 'read_text', side_effect=error):
            assert 'unreadable source' in validate_headers(headers)[0]

    def test_binary_exception_is_not_decoded(
        self,
        headers: HeadersConfig,
    ) -> None:
        """
        Preserve exempt source bytes without opening their text contents.

        Parameters
        ----------
        headers : HeadersConfig
            Synthetic consumer root and header policy.
        """
        (headers.root / 'image.bin').write_bytes(b'\xff')
        config = replace(headers, exceptions=(HeaderException(('*.bin',), 'Artwork'),))
        error = AssertionError('must not decode')
        with patch.object(Path, 'read_text', side_effect=error):
            assert validate_headers(config) == []

    @pytest.mark.parametrize(
        ('kind', 'content'),
        [
            ('html', 'not a leading comment'),
            ('block', '/*\nunterminated'),
        ],
    )
    def test_missing_comment_delimiters(
        self,
        headers: HeadersConfig,
        kind: str,
        content: str,
    ) -> None:
        """
        Reject missing or unterminated leading comment delimiters.

        Parameters
        ----------
        headers : HeadersConfig
            Synthetic consumer root and header policy.
        kind : str
            Comment syntax selected for the scenario.
        content : str
            Invalid leading-comment source contents.
        """
        (headers.root / 'sample').write_text(content, encoding='utf-8')
        rule = replace(headers.rules[0], format=kind)
        assert 'leading comment' in validate_headers(replace(headers, rules=(rule,)))[0]


class TestHeaderDiscoveryBoundaries:
    """
    Cover directive and filesystem failures without touching real sources.
    """

    def test_optional_shebang(
        self,
        headers: HeadersConfig,
    ) -> None:
        """
        Allow a shebang before a hash header without requiring a directive.
        """
        (headers.root / 'sample').write_text(
            '#!/bin/sh\n# sample\n# Sample\n#\n# Copyright Sample\n#\n# Purpose.\n',
            encoding='utf-8',
        )
        assert validate_headers(headers) == []

    def test_directive_requires_following_content(
        self,
        headers: HeadersConfig,
    ) -> None:
        """Report a file containing only its configured first-line prefix."""
        (headers.root / 'sample').write_text('#!', encoding='utf-8')
        rule = replace(headers.rules[0], first_line_prefix='#!')
        assert 'directive' in validate_headers(replace(headers, rules=(rule,)))[0]

    def test_walk_failure_is_reported(
        self,
        headers: HeadersConfig,
    ) -> None:
        """Keep recursive fallback permission failures visible to consumers."""

        def walk(
            path: Path,
            *,
            on_error: Callable[[OSError], None],
        ) -> object:
            """Simulate a traversal failure through the supplied callback."""
            on_error(PermissionError('cannot traverse source'))
            return iter(())

        with patch.object(Path, 'walk', walk):
            assert validate_headers(headers) == [
                'header source discovery failed: cannot traverse source',
            ]


class TestNonHashPreambles:
    """Keep non-hash preamble handling independent of hash separators."""

    def test_slash_preamble(
        self,
        headers: HeadersConfig,
    ) -> None:
        """Skip a matching directive before a slash-comment source header."""
        (headers.root / 'sample').write_text(
            '// directive\n// sample\n// Sample\n//\n'
            '// Copyright Sample\n//\n// Purpose.\n',
            encoding='utf-8',
        )
        rule = replace(
            headers.rules[0],
            format='slash',
            preamble_prefixes=('// directive',),
        )
        assert validate_headers(replace(headers, rules=(rule,))) == []


class TestFileDiscoveryFailures:
    """
    Keep filesystem failures visible without skipping other policy checks.
    """

    @pytest.mark.parametrize('preserved', [False, True], ids=['checked', 'excepted'])
    def test_dangling_escape_is_not_hidden(
        self,
        headers: HeadersConfig,
        symlink: Callable[[Path, Path], None],
        preserved: bool,
    ) -> None:
        """
        Inspect a dangling symlink before applying preservation exceptions.
        """
        link = headers.root / 'escape.bin'
        symlink(link, headers.root.parent / f'{headers.root.name}-missing-target')
        config = replace(
            headers,
            exceptions=(HeaderException(('*.bin',), 'Binary'),) if preserved else (),
        )
        assert validate_headers(config) == [
            'escape.bin: header source escapes repository',
        ]
        assert link.is_symlink()

    @pytest.mark.parametrize(
        'error',
        [
            PermissionError('access denied'),
            ValueError('bad path'),
            UnicodeError('bad encoding'),
        ],
    )
    @pytest.mark.parametrize('operation', ['resolve', 'is_file'])
    def test_required_path_failure_does_not_stop_remaining_checks(
        self,
        tmp_path: Path,
        error: Exception,
        operation: str,
    ) -> None:
        """
        Report unreadable paths and subsequent missing required files together.
        """
        inspect_path = getattr(Path, operation)

        def inspect(
            path: Path,
            *args: object,
            **kwargs: object,
        ) -> object:
            """Fail one fixture path while retaining normal inspection."""
            if path == tmp_path / 'unreadable':
                raise error
            return inspect_path(path, *args, **kwargs)

        config = RequiredFilesConfig(tmp_path, ('unreadable', 'missing'))
        with patch.object(Path, operation, inspect):
            assert validate_required(config) == [
                f'unreadable: {error}',
                'missing: required file does not exist or is not a file',
            ]


class TestHeaderDirectoryLinks:
    """Keep existing directory-link discovery behavior unchanged."""

    def test_directory_link_is_not_a_source(
        self,
        headers: HeadersConfig,
        symlink: Callable[[Path, Path], None],
    ) -> None:
        """
        Inspect file links without treating a linked directory as a source
        file.
        """
        target = headers.root / 'directory'
        target.mkdir()
        symlink(headers.root / 'directory-link', target)
        assert validate_headers(headers) == []
