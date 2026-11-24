# AI Software Factory

A simple, visual software factory built with Claude Code — a rebuild of
the system from the video **"Build Your Own AI Software Factory with
Claude Code"** (ZazenCodes, 28:02, https://youtu.be/ctoaIC4LHmI).

Give it a feature request. A team of agents writes the spec, builds the
whole feature, reviews it four ways, reworks it until the reviews pass,
and then either merges it into `main` or hands it to a human for review.
All state is markdown files and one JSON board; a dashboard shows the
whole system at a glance.

## The loop

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

| Step | Agent | Model | Output |
|---|---|---|---|
| Spec | `specwriter` | Opus | `factory/jobs/<id>/spec.md` |
| Build | `builder` | Opus | Code on `factory/<id>` + `build.md` |
| Review | `review-security` | Opus | `round-<n>/review-security.md` |
| Review | `review-ux` | Sonnet | `round-<n>/review-ux.md` |
| Review | `review-ui` | Sonnet | `round-<n>/review-ui.md` |
| Review | `review-code` | Sonnet | `round-<n>/review-code.md` |
| Approve | `approver` | Opus | `decision.md`: `MERGE` or `ESCALATE` |

A job gets at most three review rounds (`MAX_RESUMES = 2` in
`factory/config.json`). If round 3 still has changes, the orchestrator
writes an `ESCALATE` decision itself and the job waits for a human.

## Diagrams

The video's diagrams, redrawn in Mermaid — see
[docs/DIAGRAMS.md](docs/DIAGRAMS.md):

- the full video mind map, the factory line, and the basic agentic
  loop, all verbatim from the on-screen frames;
- a history timeline, a job lifecycle, a state-files data flow, and a
  job-001 sequence diagram, reconstructed from the narration.

GitHub renders the `.mmd` files in `docs/diagrams/` natively.

## Quickstart

### In Claude Code (live, as in the video)

1. Open this repo in Claude Code and restart it so it loads the new
   agents from `.claude/agents/`.
2. Run `/factory` and describe your feature, or `/factory next` to take
   the next item from `factory/backlog.md`.
3. Watch the board: `cd factory && python3 -m http.server 8000`, then
   open http://localhost:8000/dashboard.html.
4. When a job lands in `needs-human`, merge it with
   `/factory approve <job-id>`.

### Without Claude Code (dry-run)

The same loop runs end to end with simulated agents:

```sh
python3 scripts/factory.py new --dry-run "Obsidian course unpaywall"
python3 scripts/factory.py status
python3 scripts/factory.py approve 001-obsidian-course-unpaywall
```

Dry-run exercises everything the live loop does — worktree, branch, job
files, board, review rounds, decision, merge — except the agents
themselves. For the demo site it also applies a real deterministic patch
for known feature kinds (unpaywall, copy button, 404 page, reading time).
`build.md` always says when an output was simulated.

### Live requirements

- Claude Code CLI installed and authenticated (`claude --version`).
- A Claude Pro or Max plan (the video runs everything inside the plan;
  no API tokens are used anywhere in this repo).
- Git, Python 3.10+, and `python3 -m http.server` for the dashboard.

## Commands

| Command | What it does |
|---|---|
| `python3 scripts/factory.py new "feature" [--dry-run]` | Start a job from a feature request |
| `python3 scripts/factory.py next [--dry-run]` | Start the next unchecked `factory/backlog.md` item |
| `python3 scripts/factory.py approve <job-id>` | Merge a `needs-human` (or `ready`) job into `main` with `--no-ff`, delete its branch and worktree |
| `python3 scripts/factory.py rework <job-id> "note"` | Save a human rework note as `rework-<k>.md` |
| `python3 scripts/factory.py status` | Show every job, its phase, and its review verdicts |
| `python3 scripts/factory.py dashboard` | How to serve the dashboard |

Inside Claude Code the same commands are `/factory …`, `/factory next`,
`/factory approve …`, `/factory rework …`.

## Repo layout

```
.claude/
  skills/factory/SKILL.md   The orchestrator skill (the video's bootstrap prompt, verbatim)
  agents/                   specwriter, builder, 4 reviewers, approver
factory/
  config.json               Models, max rounds, escalation list, worktree dir
  backlog.md                Three starter items from the video
  board.example.json        Empty board template (board.json itself is gitignored)
  dashboard.html            Self-contained board: 6 columns, review chips, job drawer
  jobs/                     Runtime state, gitignored (created per job)
scripts/
  factory.py                CLI orchestrator: new / next / approve / rework / status
  factory.sh                Thin wrapper for scripts/factory.py
demo-site/                  Demo target: a static course site (25 lessons)
examples/
  jobs/001-obsidian-course-unpaywall/   The video's sample job, completed
docs/VIDEO_MAP.md           Every part traced to a video timestamp
docs/DIAGRAMS.md            Every diagram, with timestamps
docs/diagrams/              Mermaid redraws of the video's diagrams
tests/test_factory.py       Unit + end-to-end dry-run tests
```

## The demo site and the sample job

`demo-site/` stands in for the video's real site (zazencodes.com, Vue +
Firebase), which is not public. It is a static course site with 25
lessons for the "Obsidian Agent Setup" course. Each lesson has a
`publicContent` flag (lesson text public or not) and `videoPaywalled`
(always `true`: videos stay behind purchase).

Job `001-obsidian-course-unpaywall` is the video's first job, rebuilt
here as a completed example under `examples/jobs/`: the lesson pages stop
being paywalled, only the videos stay paywalled. All four reviews pass,
and the approver still escalates — course access is on the escalation
list — exactly as in the video. Run it live yourself with:

```sh
python3 scripts/factory.py new --dry-run "Obsidian course unpaywall"
```

## Decisions (from the video, t=440s)

- **Max 2 rounds.** "Max 2 rounds" means the builder can be resumed
  twice, so a job gets at most three review rounds. Change `MAX_RESUMES`
  in `factory/config.json` if you meant two rounds total.
- **Your checkout, then worktrees.** The first version built in the same
  checkout; the final version runs each job in a git worktree at
  `.worktrees/<job-id>` on branch `factory/<job-id>`, so several jobs run
  in parallel without touching each other's files.
- **Rework.** `/factory rework` saves your note as `rework-<k>.md` and
  starts a new builder, since the original builder may belong to an
  earlier session. Within a run, each new round resumes the same builder.
- **What the approver escalates.** Anything touching Stripe, course
  access, certificates, auth, `firestore.rules`, deploy or hosting
  config, sending email, production data, or new dependencies — and any
  spec assumption that is really a business decision. (In this demo repo
  the list is adapted with `course` and `unpaywall`, because the demo
  target is itself a course site; see `factory/config.json`.)
- **Merging.** Jobs merge locally with `--no-ff` and the branch is
  deleted afterwards. Merging only runs when the main checkout is clean
  and on main; `factory/board.json` and `factory/jobs/` changes never
  block a merge, because the factory rewrites them on every run.
- **State is markdown.** The metadata feeding the dashboard is plain
  markdown files. You can read them in any editor, and future agents or
  systems can use them too. `factory/board.json` and `factory/jobs/` are
  gitignored, so job state survives branch switches and never lands in a
  commit.

## What is verbatim, what is reconstructed

- **Verbatim:** the bootstrap prompt in `.claude/skills/factory/SKILL.md`,
  read off the video frame at t=290s, including the one-sentence spec and
  the orchestrator paragraph. The decisions text (t=440s) and the job 001
  build summary (t=898s) are also quoted from the screen.
- **Reconstructed:** the seven agent files, `scripts/factory.py`, the
  dashboard code, and the job 001 spec and review texts. The video shows
  these agents working but never shows their full prompt text, so each
  file was written from the role the video describes for that agent.
- **Adapted:** the demo site and its repo conventions replace the video's
  Vue + Firebase site. See `docs/VIDEO_MAP.md` for the full mapping.

## History in one paragraph

The software factory was first described by Bob Beamer at GE in 1968: a
computer-driven programming environment with standardized tools plus
historical information for management and measurement. The 2000s added
reusable patterns, models, and frameworks; the 2010s and 2020s added real
CI/CD pipelines and GitHub Actions. The new part is automating relatively
unstructured cognitive work between defined stages — including writing all
the code — with agents.

## Cost

Subagents cost more tokens: every handoff passes context back and forth.
The video runs everything inside the Claude plan, with no API tokens.
Treat token cost as the price of the quality the loop buys, and keep the
factory small — that is the whole point of the design.

## Future ideas (from the video, t=1445s)

- Use GitHub Issues as the factory input, so anyone can submit a feature.
- Trigger the factory from Slack or other tools.
- Connect app metrics (for example Sentry) so production bugs flow into
  the factory with context.
- Keep watching after deploy: if a shipped feature breaks something, the
  factory can roll it back as part of the same loop.

## Tests

```sh
python3 -m pytest tests/ -q
```

The suite covers slug and job-id allocation, escalation detection, the
dry-run builder patches, and two full end-to-end dry-run loops in a
throwaway git repo: job 001 (escalates on course access, then merges on
approve) and a 404-page job (auto-merges).
