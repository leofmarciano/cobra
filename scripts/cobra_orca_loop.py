#!/usr/bin/env python3
"""Autonomous Cobra sprint-loop harness backed by Orca orchestration.

This script is the coordinator: it reads orchestration/STATE.md, decides which
role prompt (P0/P1/P2/P3/P4) should run next, dispatches it as an Orca
task/worker, waits for a worker_done/escalation/question, and repeats until
all sprints are closed, a blocker appears, or a gate needs a human decision.

It never edits product source itself; workers (Executor, Validator, etc.) do the
actual sprint work and update STATE.md / sprint logs.

Usage:
    scripts/cobra_orca_loop.sh --dry-run     # show what would be dispatched
    scripts/cobra_orca_loop.sh --once      # run a single state transition
    scripts/cobra_orca_loop.sh               # loop until stopped/done/blocked
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
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

STATUS_FILE = REPO_ROOT / "scripts" / ".cobra_loop_status.json"
PID_FILE = REPO_ROOT / "scripts" / ".cobra_loop.pid"


class LoopError(Exception):
    """Fatal loop condition that requires operator attention."""


@dataclass
class LoopState:
    milestone: str = ""
    active_sprint: str = ""  # e.g. S00-project-bootstrap
    sprint_status: str = ""
    current_task: str = ""
    branch: str = ""
    next_action: str = ""
    blockers: list[str] = field(default_factory=list)

    def is_gate(self) -> bool:
        return any(self.active_sprint.startswith(g + "-") for g in GATE_SPRINT_IDS)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _table_cells(line: str) -> list[str]:
    """Split a markdown table row into cells, preserving inner backticks."""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _clean_value(value: str) -> str:
    """Remove markdown backticks and trailing parenthetical notes from a table cell."""
    value = value.strip().replace("`", "")
    # Remove a trailing "(note)" from cells like "main (create sprint/... at BOOT)".
    if " (" in value:
        value = value.split(" (")[0].strip()
    return value


def parse_state(path: Path = STATE_PATH) -> LoopState:
    text = path.read_text(encoding="utf-8")

    # Extract the "Now" table fields.
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
                key = parts[0]
                now_table[key] = parts[1]

    # Extract the blockers list.
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
    # The active sprint cell is "S00 — title (file)": keep only the sprint id.
    active_sprint = active_sprint_value
    m = re.match(r"^(S\d+[a-zA-Z0-9_-]*)", active_sprint_value)
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
    """Return the path to the active sprint markdown file."""
    # Accept either a bare slug like "S00-project-bootstrap" or a file path.
    if Path(sprint_id).exists():
        return Path(sprint_id)
    prefix = sprint_id.split("-")[0] if "-" in sprint_id else sprint_id
    for p in SPRINTS_DIR.iterdir():
        if p.name.lower().startswith(prefix.lower() + "-") and p.suffix == ".md":
            return p
    return None


def role_for_state(state: LoopState) -> str | None:
    """Return the prompt key (P0..P4) for the current loop state, or None."""
    status = state.sprint_status.lower()

    # Gate sprints are handled by the Gatekeeper.
    if state.is_gate():
        if status in {"not_started", "in_progress"}:
            return "P3"
        if status == "blocked":
            return "P2"
        # Any other gate state (waiting_human_decision, etc.) is not auto-dispatchable.
        return None

    if status in {"not_started", "in_progress"}:
        return "P0"
    if status == "needs_validation":
        return "P1"
    if status == "blocked":
        return "P2"
    if status == "done":
        return None  # Should have been advanced by the Validator.
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
    """Compose a prompt that wraps the canonical role prompt with context."""
    role_path = PROMPTS_DIR / ROLE_PROMPT_FILE[role]
    if not role_path.exists():
        raise LoopError(f"Missing canonical prompt: {role_path}")

    canonical = role_path.read_text(encoding="utf-8")
    sprint_file_ref = (
        sprint_file.relative_to(REPO_ROOT) if sprint_file else state.active_sprint
    )

    header = f"""# Cobra autonomous loop dispatch — {role_name(role)} ({role})

You are running as the {role_name(role)} for Project Cobra inside an
Orca-managed autonomous loop. The filesystem and git history are the durable
memory, exactly as described in AGENTS.md.

Repository root: {REPO_ROOT}
Active sprint: {state.active_sprint}
Sprint file: {sprint_file_ref}
Sprint status: {state.sprint_status}
Current task: {state.current_task}
Branch: {state.branch}
Next action: {state.next_action}

Before doing any work, read AGENTS.md, orchestration/STATE.md,
orchestration/PROTOCOL.md, and the active sprint file named above. Then follow
the canonical {role} prompt below exactly. At handoff, update STATE.md and the
sprint Session log, commit, and send worker_done.

--- CANONICAL PROMPT BELOW ---

"""
    return header + canonical


def _orca_json(*args: str) -> dict[str, Any]:
    """Run an orca command with --json and return the parsed result object."""
    cmd = ["orca", *args, "--json"]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    if proc.returncode != 0:
        raise LoopError(
            f"orca command failed: {' '.join(shlex.quote(a) for a in cmd)}\n"
            f"stderr: {proc.stderr.strip()}"
        )
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise LoopError(
            f"Non-JSON orca output: {proc.stdout[:500]}"
        ) from exc
    if not data.get("ok", True):
        raise LoopError(f"orca reported failure: {data}")
    return data.get("result", data)


def load_status(path: Path = STATUS_FILE) -> dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"version": 1, "history": []}


def save_status(status: dict[str, Any], path: Path = STATUS_FILE) -> None:
    path.write_text(json.dumps(status, indent=2), encoding="utf-8")


def write_pid(pid_file: Path = PID_FILE) -> None:
    pid_file.write_text(str(os.getpid()), encoding="utf-8")


def remove_pid(pid_file: Path = PID_FILE) -> None:
    try:
        pid_file.unlink()
    except FileNotFoundError:
        pass


def ensure_run(status: dict[str, Any], dry_run: bool) -> str:
    run_id = status.get("run_id")
    if run_id:
        return run_id
    if dry_run:
        run_id = "dry-run-00000000-0000-0000-0000-000000000000"
        status["run_id"] = run_id
        return run_id
    result = _orca_json(
        "orchestration",
        "run-create",
        "--objective",
        "Cobra autonomous sprint loop: execute, validate, and gate all sprints until v0.1",
    )
    run_data = result.get("run") if isinstance(result, dict) else None
    run_id = run_data.get("id") if isinstance(run_data, dict) else None
    if not run_id:
        raise LoopError(f"Could not extract run_id from {result}")
    status["run_id"] = run_id
    return run_id


def dispatch_worker(
    run_id: str,
    role: str,
    prompt: str,
    status: dict[str, Any],
    dry_run: bool,
    model: str | None = None,
    effort: str | None = None,
) -> dict[str, Any]:
    """Create an Orca task, start a worker on the current worktree, and return dispatch metadata."""
    title = f"{role} {status.get('active_sprint', 'unknown')}"
    if dry_run:
        print(f"[dry-run] would dispatch {role} with prompt length {len(prompt)}")
        return {
            "task_id": "dry-run-task",
            "dispatch_id": "dry-run-dispatch",
            "terminal_handle": "dry-run-terminal",
        }

    task_result = _orca_json(
        "orchestration",
        "task-create",
        "--run",
        run_id,
        "--task-title",
        title,
        "--spec",
        prompt,
    )
    task_data = task_result.get("task") if isinstance(task_result, dict) else None
    task_id = task_data.get("id") if isinstance(task_data, dict) else None
    if not task_id:
        raise LoopError(f"Could not extract task_id from {task_result}")

    worker_args = [
        "orchestration",
        "worker-start",
        "--task",
        task_id,
        "--worktree",
        "current",
        "--agent",
        "claude",
        "--name",
        f"cobra-{role.lower()}-{status.get('active_sprint', 'unknown')}",
    ]
    if model:
        worker_args += ["--model", model]
    if effort:
        worker_args += ["--effort", effort]
    worker_result = _orca_json(*worker_args)

    # Worker-start may return a nested worker/dispatch object or a flat dict.
    worker_data = worker_result.get("worker") if isinstance(worker_result, dict) else None
    if not isinstance(worker_data, dict):
        worker_data = worker_result

    dispatch_id = worker_data.get("dispatchId") or worker_data.get("id")
    terminal_handle = (
        worker_data.get("terminalHandle")
        or worker_data.get("agentTerminalHandle")
        or worker_data.get("startupTerminal", {}).get("handle")
        or worker_data.get("handle")
    )

    return {
        "task_id": task_id,
        "dispatch_id": dispatch_id,
        "terminal_handle": terminal_handle,
    }


def wait_for_messages(run_id: str, timeout_ms: int) -> list[dict[str, Any]]:
    result = _orca_json(
        "orchestration",
        "check",
        "--wait",
        "--run",
        run_id,
        "--types",
        "worker_done,escalation,question",
        "--timeout-ms",
        str(timeout_ms),
    )
    # The Orca result shape varies; accept a list, nested messages, or raw dict.
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        messages = result.get("messages")
        if isinstance(messages, list):
            return messages
        # A single message may be returned directly.
        if result.get("type") in {"worker_done", "escalation", "question"}:
            return [result]
    return []


def check_git_status() -> tuple[bool, str]:
    proc = subprocess.run(
        ["git", "status", "--porcelain", "--branch"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    if proc.returncode != 0:
        return False, proc.stderr.strip()
    lines = [ln for ln in proc.stdout.splitlines() if not ln.startswith("##")]
    return (not any(ln.strip() for ln in lines)), proc.stdout.strip()


def advance_to_next_sprint(state: LoopState) -> LoopState:
    """Update STATE.md to point at the next sprint in ROADMAP ledger order."""
    text = ROADMAP_PATH.read_text(encoding="utf-8")
    ids: list[str] = []
    for line in text.splitlines():
        if not line.startswith("| S"):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if parts and parts[0].startswith("S"):
            ids.append(parts[0])

    try:
        current_idx = ids.index(state.active_sprint.split("-")[0])
    except ValueError:
        raise LoopError(
            f"Active sprint {state.active_sprint} not found in ROADMAP ledger"
        )

    if current_idx + 1 >= len(ids):
        raise LoopError("All sprints complete — loop finished")

    next_id = ids[current_idx + 1]
    next_sprint_file = find_sprint_file(next_id)
    if next_sprint_file is None:
        raise LoopError(f"Could not find sprint file for {next_id}")

    next_slug = next_sprint_file.stem  # e.g. S01-benchmark-harness
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
    return new_state


def write_state(state: LoopState, path: Path = STATE_PATH) -> None:
    """Rewrite the Now table fields in STATE.md while preserving everything else."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    in_now = False
    new_lines: list[str] = []
    updated = {
        "Milestone": state.milestone,
        "Active sprint": state.active_sprint,
        "Sprint status": state.sprint_status,
        "Current task": state.current_task,
        "Branch": state.branch,
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
            if len(parts) >= 2:
                key = " ".join(parts[:-1]).strip()
                if key in updated:
                    val = updated[key]
                    # Preserve simple two-column alignment.
                    new_lines.append(f"| {key} | {val} |")
                    continue
        new_lines.append(line)
    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def gate_decision_recorded(state: LoopState) -> bool:
    """Return True if DECISIONS.md contains an entry for this gate sprint."""
    if not DECISIONS_PATH.exists():
        return False
    text = DECISIONS_PATH.read_text(encoding="utf-8")
    # Look for the sprint id or gate tag in decision headings/bodies.
    search_terms = [
        state.active_sprint,
        state.active_sprint.split("-")[0],
    ]
    # S05-GATE-day30 -> gate-day30, S21 -> gate-day90, S29 -> v0.1 release
    if state.active_sprint.startswith("S05"):
        search_terms.append("gate-day30")
    if state.active_sprint.startswith("S21"):
        search_terms.append("gate-day90")
    if state.active_sprint.startswith("S29"):
        search_terms.append("v0.1")
    return any(term in text for term in search_terms)


def log_history(status: dict[str, Any], entry: dict[str, Any]) -> None:
    status.setdefault("history", []).append(entry)
    # Keep history bounded.
    status["history"] = status["history"][-200:]


def run_one_cycle(
    status: dict[str, Any],
    args: argparse.Namespace,
) -> tuple[LoopState, str]:
    """Perform one loop cycle: read state, dispatch worker, wait, update status.

    Returns the current LoopState and a control string: "continue", "done",
    "blocked", or "human_gate".
    """
    state = parse_state()
    status["active_sprint"] = state.active_sprint
    status["sprint_status"] = state.sprint_status

    # If STATE somehow says a sprint is done, advance it ourselves as a fallback.
    if state.sprint_status.lower() == "done":
        print(f"Sprint {state.active_sprint} is done; advancing to next sprint")
        new_state = advance_to_next_sprint(state)
        log_history(status, {
            "time": _now_iso(),
            "event": "advanced_done_sprint",
            "from": state.active_sprint,
            "to": new_state.active_sprint,
        })
        return new_state, "continue"

    # Gate waiting for human decision: do not redispatch P3.
    if state.is_gate() and state.sprint_status.lower() not in {"not_started", "in_progress", "blocked"}:
        if not gate_decision_recorded(state):
            print(
                f"Gate sprint {state.active_sprint} is waiting for a human decision. "
                "Pausing loop."
            )
            return state, "human_gate"
        # Decision recorded; the state should already point to the next step.
        # If it still points at the gate, run P4 to reconcile.
        if state.next_action and "P4" in state.next_action:
            print("Gate decision recorded; next action is replan (P4)")
            role = "P4"
        else:
            # State already advanced, treat as continue so we re-read next cycle.
            return state, "continue"
    else:
        role = role_for_state(state)

    if role is None:
        print(
            f"No dispatchable role for sprint {state.active_sprint} with status "
            f"{state.sprint_status}. Pausing loop."
        )
        return state, "blocked"

    sprint_file = find_sprint_file(state.active_sprint)
    if sprint_file is None:
        raise LoopError(f"Could not locate sprint file for {state.active_sprint}")

    prompt = build_prompt(role, state, sprint_file)

    run_id = ensure_run(status, args.dry_run)
    dispatch = dispatch_worker(
        run_id,
        role,
        prompt,
        status,
        args.dry_run,
        model=args.model,
        effort=args.effort,
    )

    log_history(status, {
        "time": _now_iso(),
        "event": "dispatched",
        "role": role,
        "active_sprint": state.active_sprint,
        "sprint_status": state.sprint_status,
        "task_id": dispatch.get("task_id"),
        "dispatch_id": dispatch.get("dispatch_id"),
        "terminal_handle": dispatch.get("terminal_handle"),
    })

    status["current"] = {
        "role": role,
        "active_sprint": state.active_sprint,
        "task_id": dispatch.get("task_id"),
        "dispatch_id": dispatch.get("dispatch_id"),
        "terminal_handle": dispatch.get("terminal_handle"),
        "started_at": _now_iso(),
        "status": "running",
    }
    save_status(status)

    if args.dry_run:
        print("[dry-run] would wait for worker_done/escalation/question")
        return state, "continue"

    # Wait for the worker to report back.
    timeout_ms = int(args.wait_minutes * 60_000)
    messages = wait_for_messages(run_id, timeout_ms)

    # Record what we heard.
    log_history(status, {
        "time": _now_iso(),
        "event": "messages_received",
        "count": len(messages),
        "messages": messages,
    })

    # Determine control flow from messages.
    done_seen = False
    escalation_or_question = False
    for msg in messages:
        msg_type = msg.get("type", "")
        if msg_type == "worker_done":
            done_seen = True
            outcome = msg.get("outcome", "unknown")
            if outcome != "succeeded":
                print(f"Worker reported outcome={outcome}; will re-read STATE and continue")
        elif msg_type in {"escalation", "question"}:
            escalation_or_question = True

    status["current"] = {
        "role": role,
        "active_sprint": state.active_sprint,
        "task_id": dispatch.get("task_id"),
        "dispatch_id": dispatch.get("dispatch_id"),
        "terminal_handle": dispatch.get("terminal_handle"),
        "finished_at": _now_iso(),
        "status": "done" if done_seen else "unknown",
    }
    save_status(status)

    if escalation_or_question:
        print("Worker asked a question or escalated. Pausing for operator input.")
        return state, "blocked"

    return state, "continue"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Autonomous Cobra sprint-loop harness backed by Orca.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be dispatched without calling Orca.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single state transition and exit.",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=100,
        help="Maximum number of dispatch cycles before stopping (default 100).",
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
        default=60,
        help="Minutes to wait for a worker message (default 60).",
    )
    parser.add_argument(
        "--status-file",
        type=Path,
        default=STATUS_FILE,
        help="Path to the loop status JSON file.",
    )
    parser.add_argument(
        "--pid-file",
        type=Path,
        default=PID_FILE,
        help="Path to the PID file used to prevent overlap.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Optional model override for dispatched agents.",
    )
    parser.add_argument(
        "--effort",
        type=str,
        default=None,
        help="Optional reasoning effort override for dispatched agents.",
    )
    args = parser.parse_args(argv)

    if not STATE_PATH.exists():
        print(f"STATE.md not found at {STATE_PATH}", file=sys.stderr)
        return 1

    write_pid(args.pid_file)
    try:
        status = load_status(args.status_file)
        status["started_at"] = _now_iso()
        status["pid"] = os.getpid()

        clean, git_info = check_git_status()
        if not clean:
            if args.dry_run:
                print("[dry-run] warning: working tree is not clean", file=sys.stderr)
            else:
                print(
                    "Working tree is not clean; dispatching Recovery (P2) before continuing.\n"
                    f"{git_info}",
                    file=sys.stderr,
                )
                # We do not auto-dispatch from here; the next cycle will read STATE.md.
                # If the tree is dirty, a human or Recovery session must clean it.
                save_status(status)
                return 2

        start_ts = time.monotonic()
        for cycle in range(1, args.max_cycles + 1):
            if args.max_minutes and (time.monotonic() - start_ts) / 60 > args.max_minutes:
                print(f"Reached --max-minutes={args.max_minutes}; stopping.")
                break

            print(f"\n=== Cycle {cycle} ===")
            state, control = run_one_cycle(status, args)

            if control == "done":
                print("Loop complete: all sprints finished.")
                break
            if control == "blocked":
                print("Loop paused: blocker or worker escalation.")
                break
            if control == "human_gate":
                print("Loop paused: waiting for human gate decision.")
                break
            if args.once:
                print("Ran one cycle (--once); exiting.")
                break

            # Before next cycle, re-read STATE.md. If a worker advanced it, we pick up cleanly.
            print("Cycle complete; reading STATE.md for next transition...")

        save_status(status)
        return 0
    except LoopError as exc:
        print(f"Loop error: {exc}", file=sys.stderr)
        save_status(load_status(args.status_file))
        return 3
    except KeyboardInterrupt:
        print("Interrupted by operator.", file=sys.stderr)
        return 130
    finally:
        remove_pid(args.pid_file)


if __name__ == "__main__":
    sys.exit(main())
