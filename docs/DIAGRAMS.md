# Diagrams

Every diagram from the video **"Build Your Own AI Software Factory
with Claude Code"** (ZazenCodes, 28:02,
https://youtu.be/ctoaIC4LHmI), redrawn in Mermaid. Each diagram is one
`.mmd` file in `docs/diagrams/`; GitHub renders `.mmd` files natively,
so click any file to see it.

**Verbatim** means the diagram is drawn on screen in the video and was
redrawn from the frame. **Reconstructed** means the video states the
content (in narration, in the mind map, or in the bootstrap prompt) but
never draws it as a diagram — the layout is ours, the facts are the
video's.

## 1. The video mind map — `mindmap.mmd`

- **Video:** on screen t=0:41-3:46
- **Status:** verbatim
- The whole video on one map: goals, what a software factory is, a
  short history, agentic software factory 101, the Claude Code demo,
  the factory line, the orchestrator, files holding the state, the
  dashboard, build and run steps, commands, and limitations and next
  steps. The full high-quality PNG is offered in the video's
  newsletter; this is the same content as text.

## 2. The factory line — `factory-line.mmd`

- **Video:** on screen t=1:05-1:50 (the "The factory line" node)
- **Status:** verbatim
- The loop itself: Spec writer (Opus) → Builder (Opus) → four reviews
  in parallel (Security on Opus; UX, UI design, Code on Sonnet) →
  Approver (Opus) → low risk merges to main, escalate waits for a
  human. On CHANGES the orchestrator resumes the builder, at most
  twice. The same loop is the ASCII diagram in `README.md` and the
  editable spec in `.claude/skills/factory/SKILL.md`.

## 3. The basic agentic loop — `basic-loop.mmd`

- **Video:** on screen t=3:15 (inside the "Agentic software factory
  101" node)
- **Status:** verbatim
- The generic loop the video's factory is one instance of: trigger →
  sandbox → agent → checks → PR → (human) merge. The surrounding node
  also lists the triggers, diagnostics, isolation, verification, pull
  request, human gates, and audit trail — all captured in
  `mindmap.mmd`.

## 4. A short history of the software factory — `history-timeline.mmd`

- **Video:** t=2:16-3:02
- **Status:** reconstructed from narration
- The video shows this as a bullet list inside the mind map, not as a
  timeline. Same facts, laid out on a timeline: 1968 Bob Bemer at GE
  proposes the idea; 1969 Hitachi opens the first software factory;
  2000s factory as an assembly kit; 2010s-2020s factory as a delivery
  pipeline (CI/CD, GitHub Actions); now agentic factories.

## 5. Job lifecycle — `job-lifecycle.mmd`

- **Video:** dashboard columns on screen t=18:05; loop rules in the
  bootstrap prompt t=4:50; narration t=5:12-5:40
- **Status:** reconstructed from narration
- One job's states across the board: Backlog → Spec → Build → Review
  → Approve → Merged, with Needs human as the side state. CHANGES
  sends the job back to Build (max 2 resumes, so at most 3 review
  rounds); if round 3 still has changes, the orchestrator escalates
  the job itself. A human merges a needs-human job with
  `/factory approve`, or sends it back with `/factory rework`.

## 6. Files hold the state — `state-files.mmd`

- **Video:** mind-map node "Files hold the state", t=1:05; rules in
  the bootstrap prompt t=4:50
- **Status:** reconstructed from narration
- How state flows: agents get context from files, not the
  conversation, and each agent writes only its own file under
  `factory/jobs/<job-id>/`. The orchestrator spawns every agent and
  is the only writer of `factory/board.json`; the dashboard polls that
  file. `factory/backlog.md` feeds `/factory next`.

## 7. Run the factory, job 001 end to end — `run-job-sequence.mmd`

- **Video:** mind-map node "2. Run the factory", t=1:05; job 001 run
  on screen t=17:12-22:10
- **Status:** reconstructed from narration
- The video's first job as a sequence: the human runs
  `/factory "Obsidian course unpaywall"`, the specwriter and builder
  run, all four round-1 reviews pass, the approver still escalates
  because course access is on the escalation list, the job waits in
  needs-human, and `/factory approve` merges it with `--no-ff`, four
  commits ahead on main.

## How to view and edit

- **On GitHub:** open any file in `docs/diagrams/` — GitHub renders
  Mermaid natively.
- **Locally:** paste a file into https://mermaid.live, or render with
  the Mermaid CLI:

  ```sh
  npx -y @mermaid-js/mermaid-cli mmdc -i docs/diagrams/factory-line.mmd -o /tmp/factory-line.svg
  ```

- **Editing:** change the `.mmd` file; keep labels in double quotes
  when they contain `()`, `:` or `-->`, and re-render to check the
  syntax before committing. The diagrams were validated with
  `mermaid.parse()` (Mermaid 11) before this commit.
