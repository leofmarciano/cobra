#!/usr/bin/env python3
"""Create GitHub issues for every Cobra sprint and back-link them.

Usage:
    python3 scripts/populate_sprint_issues.py [--dry-run]

The script reads each orchestration/sprints/S<NN>*.md file, opens a GitHub
issue titled "[S<NN>] <title>", labels it by milestone/gate, and then writes
the issue number back into the sprint header and the ROADMAP ledger.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SPRINTS_DIR = REPO_ROOT / "orchestration" / "sprints"
ROADMAP_PATH = REPO_ROOT / "orchestration" / "ROADMAP.md"
REMOTE_OWNER_REPO = "leofmarciano/cobra"


def parse_sprint_header(path: Path) -> dict[str, str]:
    """Parse the small key/value table at the top of a sprint file."""
    table: dict[str, str] = {}
    in_table = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("| Field | Value |"):
            in_table = True
            continue
        if in_table and not line.startswith("|"):
            break
        if in_table and "---" not in line:
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 2:
                table[cells[0]] = cells[1]
    return table


def sprint_title(path: Path) -> tuple[str, str]:
    """Return (sprint_id, title) from the first markdown heading."""
    first = path.read_text(encoding="utf-8").splitlines()[0]
    m = re.match(r"#\s*(S\d+[a-zA-Z0-9_-]*)\s*[—-]\s*(.+)", first)
    if not m:
        raise ValueError(f"Could not parse sprint title in {path}: {first!r}")
    return m.group(1), m.group(2).strip()


def issue_body(path: Path, sprint_id: str, issue_num: int | None = None) -> str:
    body = path.read_text(encoding="utf-8")
    header = (
        f"This issue tracks **{sprint_id}**. "
        "Progress, blockers, and handoffs are committed to the sprint file and "
        "`orchestration/STATE.md`; use this issue for high-level status and discussion.\n\n"
    )
    if issue_num:
        header += f"Issue: #{issue_num}\n\n"
    header += "---\n\n"
    return header + body


def run_gh(*args: str) -> str:
    cmd = ["gh", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    if proc.returncode != 0:
        raise RuntimeError(f"gh command failed: {' '.join(cmd)}\n{proc.stderr.strip()}")
    return proc.stdout.strip()


def create_issue(title: str, body: str, labels: list[str]) -> int:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(body)
        body_file = f.name

    label_arg = ",".join(labels)
    url = run_gh(
        "issue",
        "create",
        "--title",
        title,
        "--body-file",
        body_file,
        "--label",
        label_arg,
    )
    # URL ends with /issues/<number>
    return int(url.rsplit("/", 1)[-1])


def labels_for_sprint(sprint_id: str, title: str, header: dict[str, str]) -> list[str]:
    labels = ["sprint"]
    milestone = header.get("Milestone", "").split()[0]  # "M0" etc.
    if milestone.startswith("M") and milestone[1:].isdigit():
        labels.append(f"milestone-{milestone}")
    if "GATE" in sprint_id.upper() or "GATE" in title.upper():
        labels.append("gate")
    return labels


def update_sprint_file(path: Path, issue_num: int) -> None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    new_lines: list[str] = []
    inserted = False
    for line in lines:
        new_lines.append(line)
        if not inserted and line.startswith("| Field | Value |"):
            new_lines.append("|---|---|")
            new_lines.append(f"| GitHub issue | #{issue_num} |")
            inserted = True
        elif not inserted and line.startswith("|---|") and "Field" in new_lines[-2]:
            # already saw header row; insert here
            new_lines.append(f"| GitHub issue | #{issue_num} |")
            inserted = True
    if not inserted:
        # Fallback: prepend a small table.
        new_lines.insert(1, "")
        new_lines.insert(2, "| Field | Value |")
        new_lines.insert(3, "|---|---|")
        new_lines.insert(4, f"| GitHub issue | #{issue_num} |")
    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def update_roadmap(sprint_id: str, issue_num: int) -> None:
    text = ROADMAP_PATH.read_text(encoding="utf-8")
    pattern = rf"^(\|\s*{re.escape(sprint_id)}\s+\|\s*)(.+?)(\s*\|)"
    repl = rf"\1[\2](#{issue_num})\3"
    new_text, count = re.subn(pattern, repl, text, flags=re.MULTILINE)
    if count == 0:
        print(f"  Warning: could not update ROADMAP.md row for {sprint_id}", file=sys.stderr)
    else:
        ROADMAP_PATH.write_text(new_text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sprint_files = sorted(SPRINTS_DIR.glob("S*.md"))
    print(f"Found {len(sprint_files)} sprint files")

    created: list[tuple[str, int]] = []
    for path in sprint_files:
        sprint_id, title = sprint_title(path)
        header = parse_sprint_header(path)
        labels = labels_for_sprint(sprint_id, title, header)
        issue_title = f"[{sprint_id}] {title}"
        print(f"{sprint_id}: {issue_title} -> labels {labels}")

        if args.dry_run:
            body = issue_body(path, sprint_id)
            print(f"  [dry-run] would create issue with body length {len(body)}")
            continue

        body = issue_body(path, sprint_id)
        issue_num = create_issue(issue_title, body, labels)
        print(
            f"  created issue #{issue_num}: https://github.com/{REMOTE_OWNER_REPO}/issues/{issue_num}"
        )
        update_sprint_file(path, issue_num)
        update_roadmap(sprint_id, issue_num)
        created.append((sprint_id, issue_num))

    print("\nDone.")
    for sprint_id, issue_num in created:
        print(f"  {sprint_id}: #{issue_num}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
