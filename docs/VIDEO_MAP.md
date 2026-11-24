# Video Map

Every part of this repo traced to the video "Build Your Own AI Software
Factory with Claude Code" (ZazenCodes, 28:02,
https://youtu.be/ctoaIC4LHmI). Timestamps are from the video; quotes marked
**verbatim** were read off the screen or the spoken transcript.

## Pipeline

| Video | What the video shows | Where it lives here |
|---|---|---|
| t=1:05 | The loop: feature → spec (Opus) → builder (Opus) → security (Opus), UX (Sonnet), UI design (Sonnet), code (Sonnet) → back to builder → approver (Opus) → merge or human review | `.claude/skills/factory/SKILL.md`, `scripts/factory.py` |
| t=2:16 | History: Bob Beamer at GE, 1968; 2000s reusable patterns; 2010s/2020s CI/CD and GitHub Actions; now the agentic factory | `README.md` |
| t=4:50 | The bootstrap prompt, pasted into Claude Code with Opus 5.5, high effort, bypass permissions | `.claude/skills/factory/SKILL.md` (verbatim) |
| t=7:20 | Decisions: max 2 rounds, your checkout, rework, approver escalation, merging with `--no-ff` | `factory/config.json`, `README.md` |
| t=8:32 | Backlog with three starter items; dashboard; `AGENTS.md` one-line pointer; `factory/` gitignored | `factory/backlog.md`, `factory/dashboard.html`, `AGENTS.md`, `.gitignore` |
| t=10:20 | Job 001: "Obsidian course unpaywall" — lesson pages public, only videos paywalled; clean-tree prerequisite | `examples/jobs/001-obsidian-course-unpaywall/`, `scripts/factory.py` |
| t=11:04 | Specwriter subagent writes the spec | `.claude/agents/specwriter.md` |
| t=12:20 | Four review subagents run; UX and UI pass | `.claude/agents/review-*.md` |
| t=12:54 | Approver escalates; job waits in `needs-human` | `.claude/agents/approver.md` |
| t=13:30 | `/factory approve 001-...` merges it; four commits ahead on main | `scripts/factory.py approve` |
| t=14:58 | `factory/board.json` and `factory/jobs/` are gitignored; state survives branch switches | `.gitignore` |
| t=16:10 | Git worktree support, so several jobs run in parallel | `scripts/factory.py`, `.worktrees/` |
| t=17:12 | Three jobs in parallel in separate tmux panes; Sonnet orchestrator, Opus subagents | `README.md` |
| t=24:05 | Future ideas: GitHub Issues as input, Slack trigger, Sentry metrics, post-deploy monitoring and rollback | `README.md` |
| t=25:58 | Cost: subagents cost more tokens; everything inside the Claude plan, no API tokens | `README.md` |

## Verbatim vs reconstructed

- **Verbatim (read off the video frame):** the bootstrap prompt in
  `.claude/skills/factory/SKILL.md`, including the one-sentence spec
  ("Build a simple, visual \"software factory\" in this repo using a
  Claude Code skill, subagents, and markdown files…"), the orchestrator
  paragraph, and the loop diagram (t=290s). The decisions text on the
  t=440s frame (dashboard shape, backlog items, gitignore, repo
  conventions, max 2 rounds, checkout, rework, escalation list, merging,
  "To use it" steps) is also quoted in the skill and README.
- **Verbatim (spoken):** the job 001 build summary shown on the dashboard
  ("Obsidian Agent Setup now sets \"publicContent\": true. All 25 lessons
  load their full markdown for everyone…"), used in
  `examples/jobs/001-obsidian-course-unpaywall/build.md` (t=898s).
- **Reconstructed:** the seven agent files, the `scripts/factory.py`
  orchestrator, the dashboard code, and the job 001 spec and review
  texts. The video shows these agents working but never shows their full
  prompt text on screen, so each file was written from the role the video
  describes for that agent and is marked as reconstructed in its header
  or in the README.
- **Adapted, not from the video:** the demo site (`demo-site/`) stands in
  for the video's real site (zazencodes.com, Vue + Firebase), which is not
  public. The repo conventions in the skill are the demo site's, with the
  video's Vue/Firebase conventions kept as the template to adapt.
