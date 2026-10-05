---
name: prp-loop
description: Drives the resumable PRP pipeline from this session as a self-continuing loop, running each stage (plan, implementation, PR, review, corrections) in a fresh visible subagent while a bundled state machine owns the gates, bounds, and persisted state. Use only when the user explicitly asks to "run the full PRP loop", "loop until the review is clean", resume a saved loop, or invokes /prp-loop. Use prp-issue for ordinary end-to-end delivery.
argument-hint: "<feature description> [--base <branch>] [--max-cycles N] [--max-implement-iterations N] [--validate \"<cmd>\"] [--until <stage>] | --resume"
---

# PRP Loop

One invocation runs `plan → implement (commit + PR) → review` and loops `review → fix` until the PR review is clean or a bound is hit. This session is the driver. Every stage runs in a fresh subagent whose progress stays visible, and `scripts/prp_loop.py` decides everything else, keeping the state in `.prp/state/prp-loop.state.json` under the checkout root.

## Contract

- The script decides; you dispatch. Never run a stage's work yourself, edit the state file, judge green, or skip a gate.
- Run exactly one stage subagent at a time, and give it the action's `prompt` verbatim. Do not add to it, trim it, or summarize the plan or report it names.
- Keep going until an action is `done` or `halted`. Do not stop to report progress between stages.
- The stage skills are invoked by name inside each subagent and never modified.

## Run it

`LOOP` below stands for `uv run <absolute path of this skill's directory>/scripts/prp_loop.py`. Every command prints one JSON action.

1. Start a new loop with the user's feature description and options, or resume a saved one with `--resume` and an optional `--until`:

   ```bash
   LOOP "<feature description>" [options]
   LOOP --resume [--until <stage>]
   ```

2. Commit to the loop's end state before the first stage. The objective is that `LOOP status` reports status `done` or `halted`: a terminal loop, not a clean review. If your environment can hold a persistent objective that keeps you working across turns, set it to exactly that, and mark it achieved only when `LOOP status` confirms it.

3. While the action is `"agent"`:
   1. Dispatch one fresh subagent, with its own context rather than a copy of this conversation, and `prompt` as its entire task. Launch it on the model and effort the `agent-policy` skill gives the action's `stage`: `plan` is Planning and design, `implement` Feature implementation, `pr` Mechanical edit, `review` Routine review or High-risk review by the diff's risk, and `fix` Bounded implementation, or Feature implementation when the accepted findings span modules.
   2. Run `LOOP dispatched`.
   3. Wait until that subagent has finished. A wait that times out is not completion; wait again. If the subagent runs in the background and you are resumed when it finishes, you may end your turn while it runs.
   4. Run `LOOP report`, even when the subagent failed or wrote no result file. The script applies the gates and prints the next action.

4. On `done` or `halted`, give the user the outcome, the PR URL, the halt reason if any, and the state file path. Write it under the `response-policy` skill.

When you lose track (after compaction, an interruption, or a reminder to continue), run `LOOP next`. It returns the same pending action until it is reported. An action with `dispatched_at` whose subagent is still running needs waiting, not a second dispatch. When the session that dispatched it is gone, resume the loop instead; resuming reruns the interrupted stage from its start.

## Options

Defaults: `--max-cycles 3`, `--max-implement-iterations 10`, base branch auto-detected by the stage skills. `--validate "<cmd>"` gives the loop an authoritative green check (exit 0 = pass) in place of the `VALIDATION: GREEN` sentinel.

`--until <stage>` (`plan` | `implement` | `pr` | `review` | `fix`) halts once that stage completes. `--until implement` stops after validations are green and the implementation skill has committed and opened its PR, with no review. `--resume --until <stage>` narrows or moves the stop point.

## What the stages do

1. **plan**: `prp-plan` writes the plan under the project's PRP store at `$PRP_DIR/plans/<feature>.plan.md`.
2. **implement**: `prp-implement` executes and validates the plan, commits the work, and opens the PR, retried in a fresh subagent with the failing output up to `--max-implement-iterations`. Anything left uncommitted goes through `prp-commit`, then a checkpoint commit.
3. **pr compatibility**: if the implementation did not open a PR, `prp-pr` does so once.
4. **review**: `prp-review` runs its default review, writes the canonical report, and publishes it to GitHub; the script verifies the verdict and the publication.
5. **cycle**: when the verdict needs fixes, the complete report, the plan, and the live PR feed a fresh `prp-implement` correction pass, the script pushes, and the PR is re-reviewed, up to `--max-cycles`. Ready to merge ends the loop; review incomplete halts it.

## Safety

- Stage subagents act with this session's permissions. For an unattended run, start the session with permissions that do not stop for approvals; otherwise a stage waits for you.
- The review stage's subagent dispatches its own reviewer subagents, so the environment must allow a subagent to start subagents.
- The script refuses to open a PR from `main`, `master`, `development`, `develop`, or the base branch.
- It halts with state preserved when implement or fix is not green after the iteration limit, the review is still dirty after `--max-cycles`, the review is incomplete or unpublished, a push fails, or a gate raises.
- Installed with its plugin, a stop hook keeps the session that owns the loop working until the loop is terminal, releases it while a dispatched stage runs, and lets it stop after three continuations without any state change. The script records the owner itself. Without the plugin, these instructions alone keep the loop going.
