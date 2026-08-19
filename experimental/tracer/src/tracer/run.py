"""CLI entry point: ``python -m tracer.run --workload <name> --out <dir>``.

This is the command used by the S03 validation block. It traces the requested
Cobra prototype workload(s), builds the dependency DAG, runs critical-path
and parallelism analysis, and emits Markdown + Graphviz DOT reports.
"""

from __future__ import annotations

from tracer.reports import main

if __name__ == "__main__":
    raise SystemExit(main())
