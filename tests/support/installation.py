"""
:mod:`tests.support.installation` module.

Run installed artifacts and consumer tools outside the source checkout.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path

# SECTION: DATA CLASSES


@dataclass(frozen=True, slots=True)
class Installation:
    """
    Represent an isolated artifact installation for public CLI tests.

    Attributes
    ----------
    python : pathlib.Path
        Interpreter in the temporary installation's virtual environment.
    command : pathlib.Path
        Installed popo console-script executable.
    directory : pathlib.Path
        Subprocess working directory outside the source checkout.
    environment : dict[str, str]
        Environment passed to subprocesses, with PYTHONPATH/PYTHONHOME removed
        by the installation fixture.

    Notes
    -----
    The dataclass is frozen and slotted; it does not create the environment or
    validate paths. Freezing prevents attribute rebinding but does not make the
    environment dictionary immutable.
    """

    python: Path
    command: Path
    directory: Path
    environment: dict[str, str]

    def run(
        self,
        *arguments: str,
        module: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        """
        Run the installed console script or module and capture its result.

        Parameters
        ----------
        *arguments : str
            CLI arguments appended to the chosen entry point.
        module : bool, optional
            Use the installation's Python interpreter with -m popo when
            ``True``; otherwise invoke its console script. Defaults to
            ``False``.

        Returns
        -------
        subprocess.CompletedProcess[str]
            Exit status and captured text output, including unsuccessful CLI
            exits.

        Raises
        ------
        subprocess.TimeoutExpired
            If the process exceeds 30 seconds.
        OSError, UnicodeError
            If startup fails or captured output cannot be decoded.

        Notes
        -----
        Use :attr:`Installation.directory` and
        :attr:`Installation.environment`. Nonzero statuses are returned for
        scenario assertions instead of raising
        :exc:`~subprocess.CalledProcessError`.
        """
        prefix = [str(self.python), '-m', 'popo'] if module else [str(self.command)]
        return self.execute(*prefix, *arguments)

    def execute(
        self,
        *arguments: str,
        directory: Path | None = None,
        timeout: int = 30,
    ) -> subprocess.CompletedProcess[str]:
        """
        Run a consumer tool in the installation's controlled environment.

        Parameters
        ----------
        *arguments : str
            Executable and arguments, without shell evaluation.
        directory : pathlib.Path or None, optional
            Consumer working directory; defaults to the installation directory.
        timeout : int, optional
            Maximum execution time in seconds; defaults to thirty.

        Returns
        -------
        subprocess.CompletedProcess[str]
            Captured text streams and the unchanged process status.

        Raises
        ------
        OSError, UnicodeError
            If startup or text decoding fails.
        subprocess.TimeoutExpired
            If the process exceeds the selected timeout.
        """
        return subprocess.run(
            arguments,
            cwd=directory or self.directory,
            env=self.environment,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )


# !SECTION
