"""Normalize version text in the Python consumer example."""

from packaging.version import Version


def normalized_version(value: str) -> str:
    """Return canonical version text using the consumer's runtime dependency.

    Parameters
    ----------
    value : str
        PEP 440 version text to normalize.

    Returns
    -------
    str
        Canonical version representation.

    Raises
    ------
    packaging.version.InvalidVersion
        If the input is not valid version text.
    """
    return str(Version(value))
