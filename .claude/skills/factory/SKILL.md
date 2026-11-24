---
name: factory
description: Run the AI software factory. Start a feature job, take the next backlog item, or approve a finished job. Use when the user asks to build a feature through the factory, run /factory next, or approve a job.
---

# Factory

> The bootstrap prompt below is quoted verbatim from the video
> "Build Your Own AI Software Factory with Claude Code" (ZazenCodes,
> https://youtu.be/ctoaIC4LHmI?t=290s). Everything after it is the factory
> this prompt built, reconstructed from the video.

Build a simple, visual "software factory" in this repo using a Claude Code skill, subagents, and markdown files. Keep it small: a viewer should understand the whole thing in a few minutes. Inspect the repo first so the agents know its language, test command, and conventions.

## The orchestrator

The factory is one skill, /factory. Whichever Claude Code session runs it becomes the orchestrator: it runs the loop below, spawns every agent, and is the only writer of factory/board.json.

## The loop (edit this to change the factory)

```
feature
   |
   v
spec-writer (opus)
   |
   v
builder (opus) <----+
   |                |
   +--> security (opus)
   +--> ux (sonnet)
   +--> ui design (sonnet)
   +--> code (sonnet)
   |                |
   +---- rework -----+
   |
   v
approver (opus) --> MERGE into main
              \--> ESCALATE to human review
```

1. **Spec.** Spawn the `specwriter` subagent (Opus). It reads the feature
   request, inspects the repo, and writes `factory/jobs/<id>/spec.md` with
   acceptance criteria. No code changes in this step.
2. **Build.** Spawn the `builder` subagent (Opus) in the job worktree on
   branch `factory/<id>`. It implements the whole feature from the spec,
   validates it with the repo's validation command, and writes
   `factory/jobs/<id>/build.md` listing what changed and how it was checked.
3. **Review.** Spawn the four review subagents in parallel, one per round:
   `review-security` (Opus), `review-ux` (Sonnet), `review-ui` (Sonnet),
   `review-code` (Sonnet). Each writes
   `factory/jobs/<id>/round-<n>/review-<name>.md` ending with exactly one
   line: `VERDICT: PASS` or `VERDICT: CHANGES_REQUIRED`, plus findings.
4. **Rework.** If any reviewer says `CHANGES_REQUIRED` and the round number
   is below `MAX_ROUNDS`, resume the same builder with the findings
   (SendMessage) and run a new review round. `MAX_RESUMES = 2`, so a job
   gets at most three review rounds. If round 3 still has changes, the
   orchestrator writes an `ESCALATE` `decision.md` itself and the job goes
   to `needs-human`. Change `MAX_RESUMES` in `factory/config.json` if you
   meant two rounds total.
5. **Approve.** Spawn the `approver` subagent (Opus). It reads the spec, the
   build notes and every review, then writes
   `factory/jobs/<id>/decision.md` with `DECISION: MERGE` or
   `DECISION: ESCALATE` and its reasons. It escalates anything touching
   Stripe, course access, certificates, auth, `firestore.rules`, deploy or
   hosting config, sending email, production data, or new dependencies, and
   any spec assumption that is really a business decision.
6. **Merge.** On `DECISION: MERGE`, merge the job branch into main with
   `git merge --no-ff` and delete the branch afterwards. Merging only runs
   when the main checkout is clean and on main; `factory/board.json` and
   `factory/jobs/` changes never block a merge. On `DECISION: ESCALATE`,
   the job waits in `needs-human` until a human runs `/factory approve <id>`.

## Commands

- `/factory <feature description>` — start a new job from a feature request.
- `/factory next` — take the next item from `factory/backlog.md` and start it.
- `/factory approve <job-id>` — merge a `needs-human` (or `ready`) job into
  main with `--no-ff`, delete its branch and worktree.
- `/factory rework <job-id> <note>` — save the note as `rework-<k>.md` and
  start a new builder for the job (the original builder may belong to an
  earlier session).
- `/factory status` — show every job, its phase, and what is waiting on a human.

## Rules the orchestrator never breaks

- Jobs run in separate git worktrees, so several jobs can run in parallel,
  one worktree per job. Never run two jobs in the same checkout.
- The builder works in a git worktree at `.worktrees/<job-id>` on branch
  `factory/<job-id>`, so parallel jobs never touch each other's files.
- The orchestrator is the only writer of `factory/board.json`. Agents write
  only their own markdown files under `factory/jobs/<job-id>/`.
- Job state (`factory/board.json`, `factory/jobs/`) is gitignored: it
  survives branch switches and never ends up in a commit. `AGENTS.md` holds
  a one-line pointer to this skill.
- Commits get short one-line messages with no AI attribution.

## Repo conventions (adapt this block to your repo)

These are the conventions of the demo target in this repo (`demo-site/`, a
static HTML site). The video's own repo used Vue + Firebase with Node 22,
`npm run build`, `npm run lint`, `<script setup>`, the `@/` alias, no
semicolons and single quotes; keep the same shape here and change the
details, not the pattern.

- Language: plain HTML, CSS and JavaScript. No build step, no framework.
- Validation: `python3 -m pytest tests/ -q` and `node --check` on changed
  JavaScript files.
- Code style: two-space indentation, single quotes in JavaScript,
  no semicolons only where the file already does so.
- Never touch `demo-site/content.json` lesson text except through a factory
  job, and never unpaywall a video: only lesson text may become public.

## To use it

1. Restart Claude Code so it loads the new agents, then run `/factory next`.
2. To watch, run `cd factory && python3 -m http.server`, then open
   `localhost:8000/dashboard.html`.
3. Without Claude Code, the same loop runs in dry-run mode:
   `python3 scripts/factory.py new --dry-run "feature description"`.
   See `README.md` for the live requirements.
