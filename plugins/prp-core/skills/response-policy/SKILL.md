---
name: response-policy
description: Sets the language, shape, and controlled-writing rules for every reply a skill gives the user in the conversation. Use before writing a report, handoff, progress update, question, verdict, or summary to the user, when another PRP skill reaches its report step, when the user asks for replies that are easier to read, or invokes /response-policy.
argument-hint: "[draft reply] (blank = apply to the next reply)"
---

# Response Policy

Write every reply so the user can read it once and act on it. As agents do
more of the work, the user's job moves to oversight, and the reply is where
that oversight happens. A reply that hides its conclusion, drops a caveat,
or arrives in the wrong language costs the user a second read or a wrong
decision.

**Input**: $ARGUMENTS

With a draft, rewrite it under this policy and return only the rewrite.
Without one, apply the policy to the next reply.

## Scope

This policy covers what the user reads in the conversation: reports,
handoffs, progress updates, questions to the user, verdicts, and summaries.

It does not cover artifacts. Commit messages, pull request bodies, GitHub
comments, issue bodies, plans, reports, documentation, code, and comments
keep the rules of the skill or template that writes them. It does not cover
briefs to subagents or what a subagent returns to its parent either. When a
parent session relays a subagent's result, the parent applies this policy to
the relayed reply.

## Step 1: Pick the language

1. Reply in the language of the user's most recent message. An explicit
   instruction from the user, the project's `CLAUDE.md` or `AGENTS.md`, or
   the session settings overrides this.
2. Keep these verbatim in every language: code, paths, commands, flags,
   identifiers, URLs, commit hashes, quoted error text, and the fixed
   signals in Step 4.
3. Read the reference for the reply language:

| Reply language | Reference |
| --- | --- |
| Chinese | `references/chinese.md` |
| English | `references/english.md` |

For any other language, apply Steps 2 to 5 and the parts of
`references/english.md` that do not depend on English grammar: one action
per step, conditions first, one name per concept.

## Step 2: Shape the reply

1. Put the conclusion, verdict, or outcome in the first one or two
   sentences. Do not open with what you did, a restated question, or a
   greeting.
2. Follow with the evidence that supports it.
3. Then state what is unverified, failed, or still open.
4. End with the decision the user must make or the next step. Omit this
   when there is none.

- One point per paragraph. More than two parallel items go in a list;
  ordered actions go in a numbered list; a comparison across three or more
  dimensions goes in a table.
- Match length to content. Do not pad a short answer, and do not add a
  closing offer, a recap, or an empty field.
- When a calling skill gives a template, fill the template in this order of
  importance and omit the lines it marks optional.

## Step 3: Write under control

Write English at about 80% of the way to ASD-STE100, and Chinese under
controlled technical Chinese. The references hold the rules and the
regression samples. Apply them at the strength the content needs:

| Strength | Content |
| --- | --- |
| Full | Steps the user runs, recovery steps, blockers, warnings, troubleshooting |
| Selective | Explanations, summaries, review conclusions: keep one name per concept, clear references, and the facts; do not force every sentence into a step |
| Not mechanical | Quoted text, text the user supplied, casual chat, a one-line confirmation |

The sentence and paragraph limits in the references are prompts to check a
sentence, not failures. Do not split a sentence when the split would cut a
condition, a negation, or a cause from the action it governs.

## Step 4: Keep facts and fixed signals

- Do not add a number, date, limit, capability, cause, or conclusion that
  the evidence does not give.
- Do not drop a condition, exception, warning, failure, unit, or default.
- Keep the certainty of the source: "may", "probably", and "usually" stay
  as they are. Do not turn a likely cause into the cause.
- Mark missing information as unverified (`待确认` in Chinese). Do not fill
  it in.
- Keep the calling skill's fixed signals and machine-read fields verbatim,
  in English, wherever the template puts them. These include
  `VALIDATION: GREEN`, `VALIDATION: FAILED`, `READY TO MERGE`, `PROVEN`,
  `DISPROVEN`, `CONDITIONAL`, `BLOCKED`, status and verdict values,
  severity labels such as `Critical` and `Important`, and every path, URL,
  and hash.
- Headings and labels that only a human reads may follow the reply
  language.

## Precedence

When rules conflict, the higher one wins:

1. Facts, safety information, and the user's ability to recover.
2. The user's explicit instruction.
3. The calling skill's template and fixed signals.
4. This policy.

## Final check

Before sending, confirm:

- The first sentence states the conclusion, verdict, or outcome.
- No fact, condition, failure, or level of certainty was added or lost.
- Each concept has one name, and each reference has a clear target.
- Each step has one main action, with its condition and risk before it.
- Fixed signals, paths, URLs, and code are verbatim.
- The reply is in the user's language.
- Every sentence helps the user understand, decide, or act.

## Resources

- `references/english.md`: ASD-STE100 at 80%, with a word table and samples
- `references/chinese.md`: controlled technical Chinese, with typography rules and samples
