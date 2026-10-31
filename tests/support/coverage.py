"""
:mod:`tests.support.coverage` module.

Build independent synthetic coverage exports without native tooling.
"""


# SECTION: FUNCTIONS


def export_report(
    adapter: str,
    rows: list[tuple[str, int, int]],
) -> dict[str, object]:
    """
    Encode independent per-target/block coverage records for both adapters.

    Parameters
    ----------
    adapter : str
        llvm or xccov export shape selected by the test.
    rows : list[tuple[str, int, int]]
        Source path, covered count and executable count for each record.

    Returns
    -------
    dict[str, object]
        Fresh JSON-compatible export with line/function/region counts for LLVM
        or executable/covered line counts for Xcode. Each row is in a separate
        block/target to exercise cross-group aggregation and deduplication.
    """
    groups = []
    for path, covered, total in rows:
        file: dict[str, object] = (
            {
                'filename': path,
                'summary': {
                    m: {'covered': covered, 'count': total}
                    for m in ('lines', 'functions', 'regions')
                },
            }
            if adapter == 'llvm'
            else {'path': path, 'coveredLines': covered, 'executableLines': total}
        )
        groups.append({'files': [file]})
    return {'data' if adapter == 'llvm' else 'targets': groups}


# !SECTION
