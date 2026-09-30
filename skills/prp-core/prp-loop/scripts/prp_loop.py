# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
prp_loop.py: state machine and gates for the in-session PRP loop.

Pipeline:
    plan -> implement (loop until green, commit, open PR) -> review
    review clean? -> done
    review dirty? -> fix (loop until green) -> push -> review   (cyclic, bounded)

Design:
- The session that invoked /prp-loop drives the loop. It asks this script for the next
  action, runs that action's prompt in a fresh native subagent (Claude Code's Agent tool,
  Codex's spawn_agent), and reports back. This script never launches an agent.
- This script owns everything that must not rest on a model's judgment: stage order,
  iteration and cycle bounds, --until, the green check, the plan, PR, and review gates,
  the checkpoint commit, the push, and every halt.
- State lives in <checkout-root>/.prp/state/prp-loop.state.json. Each stage subagent
  writes its final message to the result file named in its action; `report` reads it.
- Green comes from the stage's `VALIDATION: GREEN` sentinel, or from the optional
  --validate command, which is authoritative when given.
- `owner` records the session driving the loop, so the plugin's Stop hook keeps that
  session, and no other, working until the loop is done or halted. It is read from the
  harness's environment, so the skill's instructions stay harness-neutral; a harness
  that exports no session id records no owner and relies on the skill alone.

Commands (each prints one JSON object: the action to take next):
    prp_loop.py "<feature>" [--base B] [--max-cycles N] [--max-implement-iterations N]
                [--validate CMD] [--until STAGE] [--owner SESSION]
    prp_loop.py --resume [--until STAGE] [--owner SESSION]
    prp_loop.py next         # the pending action, preparing one when none is pending
    prp_loop.py dispatched   # the pending action's subagent is running
    prp_loop.py report       # apply the pending action's result and advance
    prp_loop.py status
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


def _project_root() -> Path:
    """The project being operated on — the user's repo, NOT where this script lives.
    Location-agnostic: derive the root from git (else cwd), so the identical script
    works whether it sits in a local skill or is bundled inside a plugin skill."""
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
        ).stdout.strip()
        if top:
            return Path(top)
    except Exception:
        pass
    return Path.cwd()


def _prp_dir() -> Path:
    """Resolve the PRP store of the checkout being operated on.

    Mirrors the canonical shell resolver the skills carry: the store is `.prp/` in
    the checkout root, --show-toplevel gives every worktree its own store, and the
    store ignores itself so the loop's state never shows up in `git status`. The
    state therefore stays with the worktree the loop drives. PRP_DIR relocates it;
    set it to run several worktrees against one store.
    """
    root = _project_root().resolve()

    override = os.environ.get("PRP_DIR")
    prp_dir = Path(override).expanduser().resolve() if override else root / ".prp"
    prp_dir.mkdir(parents=True, exist_ok=True)
    ignore = prp_dir / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n")
    return prp_dir


ROOT = _project_root()  # worktree being operated on (git toplevel, else cwd)
PRP_DIR = _prp_dir()  # that worktree's own store, unless PRP_DIR overrides it
STATE_FILE = PRP_DIR / "state" / "prp-loop.state.json"
RESULTS_DIR = PRP_DIR / "state" / "prp-loop"
PLANS_DIR = PRP_DIR / "plans"
REVIEW_DIR = PRP_DIR / "reviews"
LEGACY_STATE_FILE = ROOT / ".claude" / "prp-loop.state.json"

GREEN = "VALIDATION: GREEN"
PROTECTED_BRANCHES = {"main", "master", "development", "develop"}
STAGE_NAMES = ["plan", "implement", "pr", "review", "fix"]
COMMANDS = {"next", "dispatched", "report", "status"}
# The loop's own artifacts — never commit these, even when the target repo doesn't gitignore them.
LOOP_ARTIFACTS = (
    ".prp/",  # the PRP store: belt and braces, it also gitignores itself
    ".claude/prp-loop.state.json*",  # legacy state file + its atomic-write temp
    ".claude/prp-loop.run.log",
)


class Halted(Exception):
    """Raised after the state is saved as halted; main() prints the halted action."""


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------- state ----------
def load_state() -> dict | None:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError as e:
            sys.exit(f"state file {STATE_FILE} is corrupt ({e}); fix or delete it to start over")
    return None


def save_state(state: dict) -> None:
    state["updated_at"] = now()
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_name(STATE_FILE.name + ".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    os.replace(tmp, STATE_FILE)  # atomic: a crash mid-write never corrupts the state file


def record(state: dict, stage: str, result: str) -> None:
    state.setdefault("history", []).append(
        {"stage": stage, "cycle": state["cycle"], "result": result, "at": now()}
    )


def halt(state: dict, reason: str) -> None:
    state["status"] = "halted"
    state["halt_reason"] = reason
    state["pending"] = None
    save_state(state)
    raise Halted(reason)


def complete_stage(state: dict, stage: str, next_stage: str) -> None:
    """Advance past a finished stage, honoring --until."""
    state["pending"] = None
    state["stage"] = next_stage
    if next_stage == "done":
        state["status"] = "done"
    elif state.get("until") == stage:
        state["stage"] = "done"
        state["status"] = "done"
        state["stopped_by_until"] = stage
    save_state(state)


def set_pending(state: dict, stage: str, step: str, prompt: str, **extra: object) -> None:
    """Queue the one agent action the driving session must run next."""
    state["seq"] = state.get("seq", 0) + 1
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_file = RESULTS_DIR / f"{state['seq']:03d}-{stage}-{step}.md"
    result_file.unlink(missing_ok=True)  # never read a result left by an earlier attempt
    state["pending"] = {
        "id": state["seq"],
        "stage": stage,
        "step": step,
        "prompt": (
            f"{prompt}\n\nBefore you return, write your complete final message, verbatim, "
            f"to {result_file}, overwriting it. The PRP loop reads that file, not a summary."
        ),
        "result_file": str(result_file),
        **extra,
    }
    save_state(state)


# ---------- shells ----------
def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()


# ---------- helpers ----------
def plan_snapshot() -> dict[str, float]:
    if not PLANS_DIR.exists():
        return {}
    return {str(p): p.stat().st_mtime for p in PLANS_DIR.glob("*.plan.md")}


def newest_plan(before: dict[str, float]) -> str | None:
    """The plan written by this run's plan stage — new or modified since the snapshot,
    never a pre-existing plan that happened to be lying around."""
    if not PLANS_DIR.exists():
        return None
    fresh = [
        p for p in PLANS_DIR.glob("*.plan.md")
        if str(p) not in before or p.stat().st_mtime > before[str(p)]
    ]
    if not fresh:
        return None
    return str(max(fresh, key=lambda p: p.stat().st_mtime))


def current_pr() -> tuple[int | None, str | None]:
    out = subprocess.run(
        ["gh", "pr", "view", "--json", "number,url"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if out.returncode != 0:
        return None, None
    d = json.loads(out.stdout)
    return d.get("number"), d.get("url")


def review_contract(report_path: Path) -> tuple[str | None, str | None]:
    """Read the canonical verdict and verified GitHub publication from a review report."""
    if not report_path.exists():
        return None, None
    report = report_path.read_text()
    verdict = re.search(
        r"^verdict:\s*(READY TO MERGE|NEEDS FIXES|REVIEW INCOMPLETE)\s*$", report, re.M
    )
    publication = re.search(r"^publication:\s*(https://\S+)\s*$", report, re.M)
    return (verdict.group(1) if verdict else None, publication.group(1) if publication else None)


def review_open_findings(report_path: Path) -> int | None:
    """Read the count of findings that still require a delivery-owner disposition."""
    if not report_path.exists():
        return None
    match = re.search(r"^open_findings:\s*(\d+)\s*$", report_path.read_text(), re.M)
    return int(match.group(1)) if match else None


def publication_exists(pr_number: int, publication_url: str) -> bool:
    """Verify the recorded review publication is still attached to this PR on GitHub."""
    out = subprocess.run(
        ["gh", "pr", "view", str(pr_number), "--json", "comments,reviews"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if out.returncode != 0:
        return False
    try:
        return publication_url in json.dumps(json.loads(out.stdout))
    except json.JSONDecodeError:
        return False


def _excludes() -> list[str]:
    return [f":(exclude){p}" for p in LOOP_ARTIFACTS]


def _dirty() -> str:
    """Porcelain status, excluding the loop's own artifacts so we never sweep them in."""
    return git("status", "--porcelain", "--", ".", *_excludes())


def checkpoint_commit(state: dict) -> None:
    """Commit what prp-commit left behind, but NEVER the loop's own artifacts."""
    if not _dirty():
        return
    subprocess.run(["git", "add", "-A", "--", ".", *_excludes()], cwd=ROOT)
    commit = subprocess.run(
        ["git", "commit", "-m", "chore: prp-loop checkpoint"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if commit.returncode != 0 or _dirty():
        halt(state, f"checkpoint commit failed: {(commit.stderr or commit.stdout)[:300]}")


def check_green(state: dict, result: str) -> tuple[bool, str]:
    """Decide whether validations pass. --validate is authoritative if provided."""
    cmd = state.get("validate_cmd")
    if cmd:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, shell=True)
        return proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]
    # The stage is told to END its message with the sentinel; require it at the end so a
    # mere echo of the instruction in the body never counts as green.
    if result.rstrip().endswith(GREEN):
        return True, ""
    if "VALIDATION: FAILED" in result:
        return False, result.split("VALIDATION: FAILED", 1)[-1][:2000]
    return False, result[-2000:] or "(the stage returned no result)"


# ---------- stages: prepare queues the stage's first action ----------
def prepare_plan(state: dict) -> None:
    set_pending(
        state, "plan", "work",
        f"Use the prp-plan skill to create an implementation plan for: {state['feature']}",
        plan_before=plan_snapshot(),
    )


def implement_prompt(state: dict) -> str:
    plan = state["artifacts"]["plan_path"]
    base_arg = f" --base {state['base']}" if state.get("base") else ""
    return (
        f"Use the prp-implement skill to execute the plan at {plan}{base_arg}. "
        "Run ALL validations and commit your work. End your message with exactly "
        f"'{GREEN}' if every validation passes, otherwise end with 'VALIDATION: FAILED' "
        "followed by the failing output."
    )


def prepare_implement(state: dict) -> None:
    set_pending(state, "implement", "work", implement_prompt(state), iteration=1)


def prepare_pr(state: dict) -> None:
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if not branch or branch in PROTECTED_BRANCHES or branch == (state.get("base") or ""):
        halt(state, f"refusing to open a PR from base/protected branch '{branch}'")
    state["artifacts"]["branch"] = branch
    base_arg = f" --base {state['base']}" if state.get("base") else ""
    plan = state["artifacts"]["plan_path"]
    set_pending(
        state, "pr", "work",
        f"Use the prp-pr skill to push the current branch and open a pull request{base_arg}. "
        f"Read the plan at {plan} and pass its Source Issue and verified Plan Publication URL "
        "into the PR description when present.",
    )


def review_report_path(state: dict) -> Path:
    return REVIEW_DIR / f"pr-{state['artifacts']['pr_number']}-review.md"


def prepare_review(state: dict) -> None:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    review_report_path(state).unlink(missing_ok=True)  # never trust a stale report
    set_pending(
        state, "review", "work",
        f"Use the prp-review skill to review PR #{state['artifacts']['pr_number']}. Publish the "
        "complete canonical report to GitHub and verify its publication URL.",
    )


def fix_prompt(state: dict) -> str:
    a = state["artifacts"]
    return (
        f"Use the prp-implement skill in review-correction mode for PR #{a['pr_number']}. "
        f"Read the complete review report at {a['review_report']} and the original plan at "
        f"{a['plan_path']}. Disposition every finding under the skill's fix-now and follow-up "
        "rules, run ALL validations, and commit any repository changes. End your message with "
        f"exactly '{GREEN}' when everything passes, otherwise 'VALIDATION: FAILED' + the output."
    )


def prepare_fix(state: dict) -> None:
    a = state["artifacts"]
    if not a.get("review_report"):
        legacy_report = review_report_path(state)
        legacy_verdict, _ = review_contract(legacy_report)
        if legacy_verdict == "NEEDS FIXES":
            a["review_report"] = str(legacy_report)
    if not a.get("review_report") or not Path(a["review_report"]).exists():
        halt(state, "fix pass has no complete canonical review report")
    head_before = git("rev-parse", "HEAD")
    if not head_before:
        halt(state, "could not resolve HEAD before the fix pass")
    state["fix_head_before"] = head_before
    set_pending(state, "fix", "work", fix_prompt(state), iteration=1)


PREPARE = {
    "plan": prepare_plan,
    "implement": prepare_implement,
    "pr": prepare_pr,
    "review": prepare_review,
    "fix": prepare_fix,
}


# ---------- stages: report applies an action's result and its gates ----------
def report_plan(state: dict, pending: dict, result: str) -> None:
    plan = newest_plan(pending.get("plan_before", {}))
    if not plan:
        halt(state, f"plan stage produced no new .plan.md under {PLANS_DIR}/")
    state["artifacts"]["plan_path"] = plan
    record(state, "plan", "ok")
    complete_stage(state, "plan", "implement")


def retry_prompt(state: dict, stage: str, failures: str) -> str:
    a = state["artifacts"]
    plan = a.get("plan_path")
    plan_ref = f" against the plan at {plan}" if plan else ""
    handoff = ""
    if stage == "fix":
        handoff = (
            f"Continue the review correction for PR #{a['pr_number']}. Re-read the complete "
            f"review report at {a['review_report']} and the original plan at {plan}; do not "
            "rely on a findings summary.\n\n"
        )
    return (
        f"Continue working on the current branch{plan_ref}. The previous attempt's "
        f"validations did not pass:\n{failures}\n\n{handoff}"
        "Fix the failures, re-run ALL validations, and commit. End your message with "
        f"exactly '{GREEN}' when everything passes, otherwise 'VALIDATION: FAILED' "
        "followed by the failing output."
    )


def report_work(state: dict, pending: dict, result: str) -> None:
    """implement and fix: iterate until green, then commit what is left."""
    stage, i = pending["stage"], pending["iteration"]
    green, failures = check_green(state, result)
    if not green:
        if i >= state["max_implement_iterations"]:
            halt(state, f"{stage} not green after {state['max_implement_iterations']} iterations")
        set_pending(state, stage, "work", retry_prompt(state, stage, failures), iteration=i + 1)
        return
    record(state, stage, f"green@{i}")
    if _dirty():
        set_pending(state, stage, "commit", "Use the prp-commit skill to commit all current changes.")
        return
    finish_work(state, stage)


def report_commit(state: dict, pending: dict, result: str) -> None:
    checkpoint_commit(state)
    finish_work(state, pending["stage"])


def finish_work(state: dict, stage: str) -> None:
    a = state["artifacts"]
    if stage == "implement":
        num, url = current_pr()
        if not num:
            complete_stage(state, "implement", "pr")
            return
        a["branch"] = git("rev-parse", "--abbrev-ref", "HEAD")
        a["pr_number"], a["pr_url"] = num, url
        record(state, "pr", f"#{num}")
        complete_stage(state, "implement", "review")
        return
    if git("rev-parse", "HEAD") != state.get("fix_head_before"):
        push = subprocess.run(["git", "push"], cwd=ROOT, capture_output=True, text=True)
        if push.returncode != 0:
            halt(state, f"git push failed: {push.stderr[:300]}")
        record(state, "fix", "pushed")
    else:
        record(state, "fix", "evidence-only disposition")
    complete_stage(state, "fix", "review")


def report_pr(state: dict, pending: dict, result: str) -> None:
    num, url = current_pr()
    if not num:
        halt(state, "pr stage did not produce a discoverable PR (gh pr view failed)")
    state["artifacts"]["pr_number"], state["artifacts"]["pr_url"] = num, url
    record(state, "pr", f"#{num}")
    complete_stage(state, "pr", "review")


def report_review(state: dict, pending: dict, result: str) -> None:
    num = state["artifacts"]["pr_number"]
    report_path = review_report_path(state)
    if not report_path.exists():
        halt(state, f"review stage did not write the canonical report {report_path}")
    verdict, publication = review_contract(report_path)
    if not verdict:
        halt(state, f"review report has no canonical verdict: {report_path}")
    if not publication or not publication_exists(num, publication):
        halt(state, f"review report has no verified GitHub publication: {report_path}")
    state["artifacts"]["review_report"] = str(report_path)
    state["artifacts"]["review_publication"] = publication

    open_findings = review_open_findings(report_path)
    if verdict == "READY TO MERGE" and open_findings in (None, 0):
        record(state, "review", "clean")
        complete_stage(state, "review", "done")
        return
    if verdict == "REVIEW INCOMPLETE":
        halt(state, f"review incomplete; inspect the published report at {report_path}")

    record(state, "review", "needs-disposition" if verdict == "READY TO MERGE" else "needs-fixes")
    if state["cycle"] >= state["max_cycles"]:
        halt(state, f"review still dirty after {state['max_cycles']} cycles; PR #{num} left open for review")
    state["cycle"] += 1
    complete_stage(state, "review", "fix")


REPORT = {
    ("plan", "work"): report_plan,
    ("implement", "work"): report_work,
    ("implement", "commit"): report_commit,
    ("pr", "work"): report_pr,
    ("review", "work"): report_review,
    ("fix", "work"): report_work,
    ("fix", "commit"): report_commit,
}


# ---------- actions ----------
def action(state: dict) -> dict:
    """Describe what the driving session must do next."""
    common = {
        "loop_id": state["loop_id"],
        "state_file": str(STATE_FILE),
        "cycle": state["cycle"],
        "pr_url": state.get("artifacts", {}).get("pr_url"),
    }
    if state["status"] == "halted":
        return {"action": "halted", "reason": state.get("halt_reason"), **common}
    if state["status"] == "done":
        return {"action": "done", "stopped_by_until": state.get("stopped_by_until"), **common}
    return {"action": "agent", **state["pending"], **common}


def next_action(state: dict) -> dict:
    if state["status"] == "running" and not state.get("pending"):
        if state["stage"] == "done":
            state["status"] = "done"
            save_state(state)
        else:
            PREPARE[state["stage"]](state)
    return action(state)


def report(state: dict) -> dict:
    pending = state.get("pending")
    if state["status"] != "running" or not pending:
        return next_action(state)
    path = Path(pending["result_file"])
    result = path.read_text() if path.exists() else ""
    REPORT[(pending["stage"], pending["step"])](state, pending, result)
    return next_action(state)


def status(state: dict) -> dict:
    pending = state.get("pending") or {}
    return {
        "status": state["status"],
        "stage": state["stage"],
        "cycle": state["cycle"],
        "max_cycles": state["max_cycles"],
        "pending": {k: pending.get(k) for k in ("id", "stage", "step", "iteration", "dispatched_at")}
        if pending else None,
        "halt_reason": state.get("halt_reason"),
        "artifacts": state.get("artifacts", {}),
        "state_file": str(STATE_FILE),
    }


def start(argv: list[str]) -> dict:
    ap = argparse.ArgumentParser(description="PRP loop state machine (plan->implement+PR->review).")
    ap.add_argument("feature", nargs="*", help="Feature description, or path to a PRD/plan.")
    ap.add_argument("--base", help="Base branch (default: auto-detected by the skills).")
    ap.add_argument("--max-cycles", type=int, default=3, help="Max review->fix cycles (default 3).")
    ap.add_argument("--max-implement-iterations", type=int, default=10,
                    help="Max implement/fix iterations per stage (default 10).")
    ap.add_argument("--clean-bar", help=argparse.SUPPRESS)  # retired; canonical review verdict owns the bar
    ap.add_argument("--validate", dest="validate_cmd",
                    help="Authoritative shell command for green (exit 0 = pass). "
                         "If omitted, falls back to the VALIDATION: GREEN sentinel.")
    ap.add_argument("--until", dest="until_stage", choices=STAGE_NAMES,
                    help="Stop after the named stage completes. '--until implement' stops after "
                         "the implementation is green, committed, and opened as a PR.")
    ap.add_argument("--resume", action="store_true", help="Resume from the existing state file.")
    ap.add_argument("--owner", default=os.environ.get("CLAUDE_CODE_SESSION_ID", ""),
                    help="Session driving the loop; scopes the plugin's Stop hook "
                         "(default: the session id the harness exports, if any).")
    args = ap.parse_args(argv)

    if not STATE_FILE.exists() and LEGACY_STATE_FILE.exists():
        sys.exit(
            f"legacy loop state found at {LEGACY_STATE_FILE}; finish it with the previous "
            f"version or move it to {STATE_FILE}"
        )

    state = load_state()
    if args.resume:
        if not state:
            sys.exit("no state file to resume from")
        if state["stage"] != "done":
            state["status"] = "running"
            state.pop("halt_reason", None)
        if args.until_stage:  # allow narrowing/overriding the stop point on resume
            state["until"] = args.until_stage
        state["owner"] = args.owner
        state["pending"] = None  # the session that dispatched it is gone; rerun the stage
        save_state(state)
        return next_action(state)

    if state and state.get("status") in ("running", "halted"):
        sys.exit(
            f"a loop with status '{state.get('status')}' exists "
            f"({STATE_FILE}); use --resume or delete it"
        )
    if not args.feature:
        sys.exit("a feature description is required to start a new loop")
    state = {
        "loop_id": f"prp-loop-{now()}",
        "feature": " ".join(args.feature),
        "stage": "plan",
        "cycle": 0,
        "max_cycles": args.max_cycles,
        "max_implement_iterations": args.max_implement_iterations,
        "validate_cmd": args.validate_cmd,
        "until": args.until_stage,
        "base": args.base,
        "owner": args.owner,
        "status": "running",
        "pending": None,
        "artifacts": {},
        "history": [],
        "started_at": now(),
    }
    save_state(state)
    return next_action(state)


def main() -> None:
    argv = sys.argv[1:]
    command = argv[0] if argv and argv[0] in COMMANDS else None
    try:
        if command is None:
            out = start(argv)
        else:
            state = load_state()
            if not state:
                sys.exit(f"no loop state at {STATE_FILE}; start a loop first")
            if command == "next":
                out = next_action(state)
            elif command == "dispatched":
                if state.get("pending"):
                    state["pending"]["dispatched_at"] = now()
                    save_state(state)
                out = next_action(state)
            elif command == "report":
                out = report(state)
            else:
                out = status(state)
    except Halted:
        out = action(load_state())
    except Exception as e:  # noqa: BLE001 - a gate that raises halts with state preserved
        state = load_state()
        if not state or state.get("status") != "running":
            raise
        stage = state["stage"]
        try:
            halt(state, f"stage '{stage}' raised: {e}")
        except Halted:
            out = action(state)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
