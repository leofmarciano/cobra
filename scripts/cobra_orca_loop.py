#!/usr/bin/env python3
"""Autonomous Cobra sprint-loop harness (Devin-only workers).

The harness is the coordinator: it reads orchestration/STATE.md, decides which
role prompt (P0/P1/P2/P3/P4) should run next, spawns a NON-INTERACTIVE Devin
CLI worker (`devin --print`) with that prompt, waits for it to finish, then
classifies progress from STATE.md + git. It repeats until a sprint boundary,
a blocker, or a gate that needs a human decision.

Orca's role: the scheduled Orca automation runs this script hourly and its
supervisor agent reports our LOOP_RESULT lines to the operator. Workers are
plain `devin -p` subprocesses (Orca worker-start only supports claude/codex,
and this project is Devin-only by owner decision D-004).

The harness never edits product source itself; the only file it may write and
commit is orchestration/STATE.md (fallback sprint advancement).

Usage:
    scripts/cobra_orca_loop.sh --dry-run     # show what would be dispatched
    scripts/cobra_orca_loop.sh --once        # run a single worker session
    scripts/cobra_orca_loop.sh               # loop until blocked/done/budget

Exit codes:
    0  progress made (or clean no-op)
    2  human attention required (gate, blocker, question, dirty tree w/o fix)
    3  loop error
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATION_DIR = REPO_ROOT / "orchestration"
STATE_PATH = ORCHESTRATION_DIR / "STATE.md"
ROADMAP_PATH = ORCHESTRATION_DIR / "ROADMAP.md"
DECISIONS_PATH = ORCHESTRATION_DIR / "DECISIONS.md"
PROMPTS_DIR = ORCHESTRATION_DIR / "prompts"
SPRINTS_DIR = ORCHESTRATION_DIR / "sprints"

ROLE_PROMPT_FILE = {
    "P0": "P0-execute.md",
    "P1": "P1-validate.md",
    "P2": "P2-recovery.md",
    "P3": "P3-gate-review.md",
    "P4": "P4-replan.md",
}

GATE_SPRINT_IDS = {"S05", "S21", "S29"}
# A gate counts as "decided by the human" only when its unique tag appears in
# DECISIONS.md. Never match on the bare sprint id: earlier decision entries
# legitimately mention sprint ids (e.g. D-003 discusses S05 without deciding it).
GATE_DECISION_TAGS = {
    "S05": "gate-day30",
    "S21": "gate-day90",
    "S29": "v0.1.0-preview",
}

STATUS_FILE = REPO_ROOT / "scripts" / ".cobra_loop_status.json"
PID_FILE = REPO_ROOT / "scripts" / ".cobra_loop.pid"
LOG_DIR = REPO_ROOT / "scripts" / ".cobra_loop_logs"

# Consecutive worker sessions with zero observable progress before we stop
# burning scheduled runs and ask the operator to look.
MAX_NO_PROGRESS = 2


class LoopError(Exception):
    """Fatal loop condition that requires operator attention."""


@dataclass
class LoopState:
    milestone: str = ""
    active_sprint: str = ""  # bare id (S00) or slug (S00-project-bootstrap)
    sprint_status: str = ""
    current_task: str = ""
    branch: str = ""
    next_action: str = ""
    blockers: list[str] = field(default_factory=list)

    def sprint_id(self) -> str:
        """Bare sprint id, e.g. 'S05' from 'S05-GATE-day30' or 'S05'."""
        return self.active_sprint.split("-")[0] if self.active_sprint else ""

    def is_gate(self) -> bool:
        return self.sprint_id() in GATE_SPRINT_IDS


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _clean_value(value: str) -> str:
    """Remove markdown backticks and a trailing parenthetical note."""
    value = value.strip().replace("`", "")
    if " (" in value:
        value = value.split(" (")[0].strip()
    return value


def parse_state(path: Path = STATE_PATH) -> LoopState:
    text = path.read_text(encoding="utf-8")

    now_table: dict[str, str] = {}
    in_now = False
    for line in text.splitlines():
        if line.startswith("## Now"):
            in_now = True
            continue
        if in_now and line.startswith("##"):
            break
        if in_now and line.startswith("|") and "---" not in line:
            parts = _table_cells(line)
            if len(parts) >= 2:
                now_table[parts[0]] = parts[1]

    blockers: list[str] = []
    in_blockers = False
    for line in text.splitlines():
        if line.startswith("## Blockers"):
            in_blockers = True
            continue
        if in_blockers and line.startswith("##"):
            break
        if in_blockers and line.startswith("- "):
            item = line[2:].strip()
            if item and item != "(none)":
                blockers.append(item)

    def _get(key: str) -> str:
        return _clean_value(now_table.get(key, ""))

    active_sprint_value = _get("Active sprint")
    active_sprint = active_sprint_value
    # Accept "S00 — title", "S05-GATE-day30", "S00" — keep id or full slug.
    m = re.match(r"^(S\d+[A-Za-z0-9_-]*)", active_sprint_value)
    if m:
        active_sprint = m.group(1)

    return LoopState(
        milestone=_get("Milestone"),
        active_sprint=active_sprint,
        sprint_status=_get("Sprint status"),
        current_task=_get("Current task"),
        branch=_get("Branch"),
        next_action=_get("Next action"),
        blockers=blockers,
    )


def find_sprint_file(sprint_id: str) -> Path | None:
    if Path(sprint_id).exists():
        return Path(sprint_id)
    prefix = sprint_id.split("-")[0] if "-" in sprint_id else sprint_id
    for p in sorted(SPRINTS_DIR.iterdir()):
        if p.suffix == ".md" and p.name.lower().startswith(prefix.lower() + "-"):
            return p
    return None


def gate_decision_recorded(state: LoopState) -> bool:
    if not DECISIONS_PATH.exists():
        return False
    tag = GATE_DECISION_TAGS.get(state.sprint_id())
    if not tag:
        return False
    return tag in DECISIONS_PATH.read_text(encoding="utf-8")


def role_for_state(state: LoopState) -> str | None:
    """Return the prompt key (P0..P4) to dispatch, or None (needs human/no-op)."""
    status = state.sprint_status.lower()

    if state.is_gate():
        if status == "not_started":
            return "P3"  # assemble evidence, write gate report, then block
        if status in {"in_progress", "needs_validation", "blocked"}:
            # P3 already ran (or is mid-flight). Only re-dispatch to FINALIZE
            # after the human recorded the decision in DECISIONS.md.
            return "P3" if gate_decision_recorded(state) else None
        return None

    if status in {"not_started", "in_progress"}:
        return "P0"
    if status == "needs_validation":
        return "P1"
    # blocked => waiting on a human (see STATE Blockers). Never auto-dispatch.
    return None


def role_name(role: str) -> str:
    return {
        "P0": "Executor",
        "P1": "Validator",
        "P2": "Recovery agent",
        "P3": "Gatekeeper",
        "P4": "Replanner",
    }.get(role, role)


def build_prompt(role: str, state: LoopState, sprint_file: Path | None) -> str:
    role_path = PROMPTS_DIR / ROLE_PROMPT_FILE[role]
    if not role_path.exists():
        raise LoopError(f"Missing canonical prompt: {role_path}")

    canonical = role_path.read_text(encoding="utf-8")
    sprint_file_ref = sprint_file.relative_to(REPO_ROOT) if sprint_file else state.active_sprint

    header = f"""# Cobra autonomous loop dispatch — {role_name(role)} ({role})

You are running as the {role_name(role)} for Project Cobra inside an
autonomous, NON-INTERACTIVE loop session (no human is watching this run).
The filesystem and git history are the durable memory, exactly as described
in AGENTS.md.

Repository root: {REPO_ROOT}
Active sprint: {state.active_sprint}
Sprint file: {sprint_file_ref}
Sprint status: {state.sprint_status}
Current task: {state.current_task}
Branch: {state.branch}
Next action: {state.next_action}

Autonomous-mode overrides (they refine, never replace, the canonical prompt):
1. You cannot ask questions mid-run. Wherever the canonical prompt says to
   ask/tell the operator or wait for a human, instead: write the item into
   orchestration/STATE.md (Blockers or Human-input queue), set the sprint
   status accordingly (`blocked` if you cannot proceed), commit, and finish
   your reply.
2. Budget one focused session (~40 minutes of work). Stop at a task boundary
   with the full handoff ritual rather than starting something you cannot
   finish.
3. Your LAST actions before finishing MUST be: update STATE.md + the sprint
   Session log, then `git add`/`git commit` everything. A session that ends
   with a dirty working tree is a protocol failure.
4. Never touch sprints other than the active one. Never push to remote.

--- CANONICAL PROMPT BELOW ---

"""
    return header + canonical


# ----------------------------------------------------------------------------
# Devin worker execution
# ----------------------------------------------------------------------------


def run_worker(
    role: str,
    prompt: str,
    args: argparse.Namespace,
) -> dict[str, Any]:
    """Run `devin --print` with the prompt; return outcome metadata."""
    LOG_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    log_path = LOG_DIR / f"{stamp}-{role}.log"

    cmd = [
        args.devin_bin,
        "-p",
        prompt,
        "--permission-mode",
        args.permission_mode,
    ]
    if args.model:
        cmd += ["--model", args.model]

    started = time.monotonic()
    timeout_s = int(args.wait_minutes * 60)
    timed_out = False
    with open(log_path, "w", encoding="utf-8") as log:
        log.write(f"# role={role} started={_now_iso()} timeout_s={timeout_s}\n")
        log.flush()
        proc = subprocess.Popen(
            cmd,
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=REPO_ROOT,
            text=True,
        )
        try:
            returncode = proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.terminate()  # give Devin a chance to wind down
            try:
                returncode = proc.wait(timeout=90)
            except subprocess.TimeoutExpired:
                proc.kill()
                returncode = proc.wait()

    duration_min = (time.monotonic() - started) / 60
    tail = ""
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = "\n".join(lines[-15:])
    except OSError:
        pass

    return {
        "returncode": returncode,
        "timed_out": timed_out,
        "duration_min": round(duration_min, 1),
        "log": str(log_path),
        "tail": tail,
    }


# ----------------------------------------------------------------------------
# Git helpers
# ----------------------------------------------------------------------------


def _git(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *argv], capture_output=True, text=True, cwd=REPO_ROOT, check=False
    )


def git_is_clean() -> tuple[bool, str]:
    proc = _git("status", "--porcelain")
    if proc.returncode != 0:
        return False, proc.stderr.strip()
    return (not proc.stdout.strip()), proc.stdout.strip()


def git_head() -> str:
    return _git("rev-parse", "HEAD").stdout.strip()


# ----------------------------------------------------------------------------
# Status file
# ----------------------------------------------------------------------------


def load_status(path: Path = STATUS_FILE) -> dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"version": 2, "history": []}


def save_status(status: dict[str, Any], path: Path = STATUS_FILE) -> None:
    path.write_text(json.dumps(status, indent=2), encoding="utf-8")


def log_history(status: dict[str, Any], entry: dict[str, Any]) -> None:
    status.setdefault("history", []).append(entry)
    status["history"] = status["history"][-200:]


def write_pid(pid_file: Path = PID_FILE) -> None:
    pid_file.write_text(str(os.getpid()), encoding="utf-8")


def remove_pid(pid_file: Path = PID_FILE) -> None:
    try:
        pid_file.unlink()
    except FileNotFoundError:
        pass


# ----------------------------------------------------------------------------
# STATE.md fallback advancement (Validator normally does this)
# ----------------------------------------------------------------------------


def roadmap_sprint_ids() -> list[str]:
    ids: list[str] = []
    for line in ROADMAP_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| S"):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if parts and re.match(r"^S\d+", parts[0]):
            ids.append(parts[0])
    return ids


def write_state(state: LoopState, path: Path = STATE_PATH) -> None:
    """Rewrite the Now-table fields in STATE.md, preserving everything else."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    in_now = False
    new_lines: list[str] = []
    updated = {
        "Milestone": state.milestone,
        "Active sprint": state.active_sprint,
        "Sprint status": f"`{state.sprint_status}`",
        "Current task": state.current_task,
        "Branch": f"`{state.branch}`",
        "Next action": state.next_action,
    }
    for line in lines:
        if line.startswith("## Now"):
            in_now = True
            new_lines.append(line)
            continue
        if in_now and line.startswith("##"):
            in_now = False
        if in_now and line.startswith("|") and "---" not in line:
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 2 and parts[0] in updated:
                new_lines.append(f"| {parts[0]} | {updated[parts[0]]} |")
                continue
        new_lines.append(line)
    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def advance_to_next_sprint(state: LoopState) -> LoopState:
    """Fallback: point STATE.md at the next ledger sprint and COMMIT it."""
    ids = roadmap_sprint_ids()
    try:
        current_idx = ids.index(state.sprint_id())
    except ValueError:
        raise LoopError(f"Active sprint {state.active_sprint} not found in ROADMAP ledger")
    if current_idx + 1 >= len(ids):
        raise LoopError("All sprints complete — loop finished")

    next_id = ids[current_idx + 1]
    next_file = find_sprint_file(next_id)
    if next_file is None:
        raise LoopError(f"Could not find sprint file for {next_id}")

    next_slug = next_file.stem
    new_state = LoopState(
        milestone=state.milestone,
        active_sprint=next_slug,
        sprint_status="not_started",
        current_task="T1",
        branch=f"sprint/{next_slug}",
        next_action="Run P0 (Executor)",
        blockers=[],
    )
    write_state(new_state)
    _git("add", str(STATE_PATH.relative_to(REPO_ROOT)))
    commit = _git(
        "commit",
        "-m",
        f"loop: advance STATE to {next_id} after {state.sprint_id()} closed",
    )
    if commit.returncode != 0:
        raise LoopError(f"Failed to commit STATE advancement: {commit.stderr}")
    return new_state


# ----------------------------------------------------------------------------
# Main cycle
# ----------------------------------------------------------------------------


def emit_result(kind: str, **fields: Any) -> None:
    """Print the standardized line the Orca supervisor reports to the operator."""
    detail = " ".join(f"{k}={v}" for k, v in fields.items())
    print(f"LOOP_RESULT: {kind} {detail}".strip())


def run_one_cycle(status: dict[str, Any], args: argparse.Namespace) -> str:
    """One transition. Returns: continue | done | human | error."""
    state = parse_state()
    status["active_sprint"] = state.active_sprint
    status["sprint_status"] = state.sprint_status

    # Sprint already closed by the Validator but STATE not advanced: fallback.
    if state.sprint_status.lower() == "done":
        new_state = advance_to_next_sprint(state)
        log_history(
            status,
            {
                "time": _now_iso(),
                "event": "advanced_done_sprint",
                "from": state.active_sprint,
                "to": new_state.active_sprint,
            },
        )
        emit_result("advanced", frm=state.sprint_id(), to=new_state.sprint_id())
        return "continue"

    # Dirty tree at cycle start = a previous session died mid-work → Recovery.
    clean, git_info = git_is_clean()
    role: str | None
    if not clean:
        print(f"Working tree dirty at cycle start:\n{git_info}")
        role = "P2"
    else:
        role = role_for_state(state)

    if role is None:
        if state.is_gate():
            emit_result(
                "human_required",
                reason="gate_decision",
                sprint=state.sprint_id(),
                detail="Gate report awaits a human go/narrow/stop in DECISIONS.md",
            )
        elif state.sprint_status.lower() == "blocked":
            emit_result(
                "human_required",
                reason="blocked",
                sprint=state.sprint_id(),
                blockers="; ".join(state.blockers) or "see STATE.md",
            )
        else:
            emit_result(
                "human_required",
                reason="unrecognized_state",
                sprint=state.sprint_id(),
                status=state.sprint_status,
            )
        return "human"

    sprint_file = find_sprint_file(state.active_sprint)
    if sprint_file is None and role not in {"P2", "P4"}:
        raise LoopError(f"Could not locate sprint file for {state.active_sprint}")

    prompt = build_prompt(role, state, sprint_file)

    if args.dry_run:
        print(
            f"[dry-run] would run devin as {role_name(role)} ({role}) "
            f"for {state.active_sprint} [{state.sprint_status}]; "
            f"prompt {len(prompt)} chars"
        )
        return "continue"

    head_before = git_head()
    state_before = STATE_PATH.read_text(encoding="utf-8")

    print(
        f"Dispatching {role_name(role)} ({role}) for {state.active_sprint} "
        f"[{state.sprint_status}] via {args.devin_bin} --print ..."
    )
    outcome = run_worker(role, prompt, args)

    log_history(
        status,
        {
            "time": _now_iso(),
            "event": "worker_finished",
            "role": role,
            "active_sprint": state.active_sprint,
            "sprint_status_before": state.sprint_status,
            **{k: outcome[k] for k in ("returncode", "timed_out", "duration_min", "log")},
        },
    )
    save_status(status)

    # Classify progress from durable state, not from the worker's words.
    new_state = parse_state()
    head_after = git_head()
    state_changed = STATE_PATH.read_text(encoding="utf-8") != state_before
    progressed = state_changed or head_after != head_before

    clean_after, dirty_after = git_is_clean()
    if outcome["timed_out"]:
        emit_result(
            "worker_timeout",
            role=role,
            sprint=state.sprint_id(),
            minutes=outcome["duration_min"],
            log=outcome["log"],
        )
        # Dirty tree will route the NEXT cycle to P2 recovery automatically.
        return "continue" if not args.once else "human"

    if not clean_after:
        print(
            "Worker finished with a dirty tree (protocol violation); "
            "next cycle will dispatch Recovery (P2)."
        )
        print(dirty_after)

    if not progressed:
        key = f"{state.active_sprint}:{state.sprint_status}:{role}"
        counts = status.setdefault("no_progress", {})
        counts[key] = counts.get(key, 0) + 1
        save_status(status)
        if counts[key] >= MAX_NO_PROGRESS:
            emit_result(
                "human_required",
                reason="no_progress",
                role=role,
                sprint=state.sprint_id(),
                attempts=counts[key],
                log=outcome["log"],
                tail=json.dumps(outcome["tail"][-400:]),
            )
            return "human"
        print(
            f"No observable progress (attempt {counts[key]}/{MAX_NO_PROGRESS}); "
            "will retry next cycle."
        )
        return "continue"

    status.setdefault("no_progress", {}).pop(
        f"{state.active_sprint}:{state.sprint_status}:{role}", None
    )

    emit_result(
        "session_complete",
        role=role,
        sprint=new_state.sprint_id(),
        status=new_state.sprint_status,
        duration_min=outcome["duration_min"],
        commits=_git("rev-list", "--count", f"{head_before}..{head_after}").stdout.strip() or "0",
    )

    # Surface newly-blocked / gate-waiting states immediately.
    if new_state.sprint_status.lower() == "blocked" or (
        new_state.is_gate() and role == "P3" and not gate_decision_recorded(new_state)
    ):
        reason = "gate_decision" if new_state.is_gate() else "blocked"
        emit_result(
            "human_required",
            reason=reason,
            sprint=new_state.sprint_id(),
            blockers="; ".join(new_state.blockers) or "see STATE.md",
        )
        return "human"

    return "continue"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Autonomous Cobra sprint-loop harness (Devin workers).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be dispatched without running Devin.",
    )
    parser.add_argument("--once", action="store_true", help="Run a single worker session and exit.")
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=100,
        help="Maximum dispatch cycles before stopping (default 100).",
    )
    parser.add_argument(
        "--max-minutes",
        type=float,
        default=0,
        help="Maximum total runtime in minutes (0 = no limit).",
    )
    parser.add_argument(
        "--wait-minutes",
        type=float,
        default=50,
        help="Per-worker time budget in minutes (default 50).",
    )
    parser.add_argument(
        "--model", type=str, default=None, help="Optional model override passed to `devin --model`."
    )
    parser.add_argument(
        "--effort",
        type=str,
        default=None,
        help="Ignored (kept for automation-prompt compatibility).",
    )
    parser.add_argument(
        "--permission-mode",
        type=str,
        default="dangerous",
        choices=["auto", "accept-edits", "smart", "dangerous"],
        help="Devin permission mode for workers (default: dangerous; "
        "required for unattended git/build/test commands).",
    )
    parser.add_argument(
        "--devin-bin",
        type=str,
        default=os.environ.get("COBRA_DEVIN_BIN", "devin"),
        help="Devin CLI binary (default: devin, or $COBRA_DEVIN_BIN).",
    )
    parser.add_argument("--status-file", type=Path, default=STATUS_FILE)
    parser.add_argument("--pid-file", type=Path, default=PID_FILE)
    args = parser.parse_args(argv)

    if not STATE_PATH.exists():
        print(f"STATE.md not found at {STATE_PATH}", file=sys.stderr)
        return 1

    write_pid(args.pid_file)
    try:
        status = load_status(args.status_file)
        status["started_at"] = _now_iso()
        status["pid"] = os.getpid()

        start_ts = time.monotonic()
        result = 0
        for cycle in range(1, args.max_cycles + 1):
            if args.max_minutes and (time.monotonic() - start_ts) / 60 > args.max_minutes:
                print(f"Reached --max-minutes={args.max_minutes}; stopping.")
                break

            print(f"\n=== Cycle {cycle} ===")
            try:
                control = run_one_cycle(status, args)
            except LoopError as exc:
                if "loop finished" in str(exc):
                    emit_result("all_sprints_complete")
                    control = "done"
                else:
                    raise

            save_status(status)
            if control == "done":
                break
            if control == "human":
                result = 2
                break
            if args.once:
                print("Ran one cycle (--once); exiting.")
                break

        save_status(status)
        return result
    except LoopError as exc:
        print(f"Loop error: {exc}", file=sys.stderr)
        emit_result("loop_error", detail=str(exc)[:200])
        return 3
    except KeyboardInterrupt:
        print("Interrupted by operator.", file=sys.stderr)
        return 130
    finally:
        remove_pid(args.pid_file)


if __name__ == "__main__":
    sys.exit(main())
