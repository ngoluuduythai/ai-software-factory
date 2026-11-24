#!/usr/bin/env python3
"""AI Software Factory orchestrator.

Runs the loop from .claude/skills/factory/SKILL.md without an interactive
Claude Code session:

    feature -> specwriter (opus) -> builder (opus) -> 4 reviewers in parallel
    -> rework (at most MAX_RESUMES resumes) -> approver (opus)
    -> MERGE into main, or ESCALATE to human review.

Two modes:

- Live mode (default): each stage runs the `claude` CLI in print mode
  (`claude -p`) with the matching agent definition from `.claude/agents/`
  prepended to the task prompt. Requires Claude Code installed and
  authenticated, plus a Claude Pro/Max plan or API access.
- Dry-run mode (`--dry-run`): every stage is simulated from templates and,
  for the demo site, the builder applies a real deterministic patch for
  known feature kinds (unpaywall, copy button, 404 page, reading time).
  Dry-run exercises the whole loop end to end: worktree, branch, job
  files, board.json, review rounds, decision, merge.

Usage:
    python3 scripts/factory.py new "feature description" [--dry-run]
    python3 scripts/factory.py next [--dry-run]
    python3 scripts/factory.py approve <job-id>
    python3 scripts/factory.py rework <job-id> "human note"
    python3 scripts/factory.py status
    python3 scripts/factory.py dashboard

State lives in factory/board.json (written only by this script) and
factory/jobs/<job-id>/ (one markdown file per stage artifact). Both are
gitignored, exactly as in the video.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FACTORY_DIR = ROOT / "factory"
CONFIG_PATH = FACTORY_DIR / "config.json"
BOARD_PATH = FACTORY_DIR / "board.json"
BOARD_EXAMPLE_PATH = FACTORY_DIR / "board.example.json"
BACKLOG_PATH = FACTORY_DIR / "backlog.md"
AGENTS_DIR = ROOT / ".claude" / "agents"

# Files whose changes never block a clean-tree check or a merge, because the
# factory rewrites them on every run (video, t=1331s).
IGNORED_CHANGE_PREFIXES = ("factory/board.json", "factory/jobs/", ".worktrees/")


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_board() -> dict:
    if not BOARD_PATH.exists():
        shutil.copyfile(BOARD_EXAMPLE_PATH, BOARD_PATH)
    return json.loads(BOARD_PATH.read_text(encoding="utf-8"))


def save_board(board: dict) -> None:
    BOARD_PATH.write_text(json.dumps(board, indent=2) + "\n", encoding="utf-8")


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:50] or "feature"


def next_job_number(board: dict) -> int:
    numbers = [int(job["id"].split("-")[0]) for job in board.get("jobs", [])
               if job["id"][:3].isdigit()]
    return (max(numbers) if numbers else 0) + 1


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, cwd=str(cwd or ROOT), capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(cmd)}\n{result.stderr.strip()}")
    return result


def git_status_short() -> list[str]:
    out = run(["git", "status", "--porcelain"], check=False).stdout
    return [line for line in out.splitlines() if line.strip()]


def is_ignored_change(status_line: str) -> bool:
    path = status_line[3:].strip().strip('"')
    return any(path.startswith(prefix) for prefix in IGNORED_CHANGE_PREFIXES)


def require_clean_tree() -> None:
    dirty = [line for line in git_status_short() if not is_ignored_change(line)]
    if dirty:
        raise RuntimeError(
            "Working tree is not clean. Commit or stash first:\n" + "\n".join(dirty)
        )


def require_on_main() -> None:
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    if branch != "main":
        raise RuntimeError(f"Must be on main to merge, currently on {branch!r}.")


def read_agent_definition(name: str) -> str:
    """Return an agent file with its YAML frontmatter stripped."""
    text = (AGENTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    if text.startswith("---"):
        text = text.split("---", 2)[2]
    return text.strip()


# --------------------------------------------------------------------------
# Backlog
# --------------------------------------------------------------------------

def read_backlog_items() -> list[dict]:
    items = []
    for line in BACKLOG_PATH.read_text(encoding="utf-8").splitlines():
        match = re.match(r"- \[( |x)\] (.+)$", line)
        if match:
            items.append({"done": match.group(1) == "x", "text": match.group(2)})
    return items


def write_backlog_items(items: list[dict]) -> None:
    text = BACKLOG_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    out, index = [], 0
    for line in lines:
        if re.match(r"- \[( |x)\] ", line):
            item = items[index]
            index += 1
            out.append(f"- [{'x' if item['done'] else ' '}] {item['text']}")
        else:
            out.append(line)
    BACKLOG_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")


def peek_next_backlog_item() -> str:
    for item in read_backlog_items():
        if not item["done"]:
            return item["text"]
    raise RuntimeError("Backlog is empty: add an item to factory/backlog.md first.")


def mark_backlog_item_done(text: str) -> None:
    items = read_backlog_items()
    for item in items:
        if not item["done"] and item["text"] == text:
            item["done"] = True
            break
    write_backlog_items(items)


# --------------------------------------------------------------------------
# Live stage runner (Claude Code CLI) and dry-run simulator
# --------------------------------------------------------------------------

def run_claude_stage(agent: str, model: str, task: str, cwd: Path) -> str:
    """Run one agent through the Claude Code CLI and return its stdout."""
    claude = shutil.which("claude")
    if claude is None:
        raise RuntimeError(
            "The `claude` CLI is not installed. Install Claude Code "
            "(https://claude.com/product/claude-code) and authenticate, "
            "or re-run with --dry-run to simulate this stage."
        )
    prompt = f"{read_agent_definition(agent)}\n\n---\n\nTask:\n{task}\n"
    result = subprocess.run(
        [claude, "-p", "--model", model, "--dangerously-skip-permissions",
         "--output-format", "text", prompt],
        cwd=str(cwd), capture_output=True, text=True, timeout=3600,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Claude stage {agent!r} failed:\n{result.stderr.strip()}")
    return result.stdout


def dry_run_spec(feature: str, job_id: str) -> str:
    return f"""# Spec — {job_id}

## Feature

{feature}

## Goal

Build the requested feature in the demo site, validated and reviewed,
following the factory loop.

## Acceptance criteria

- [ ] The feature behaves as described above.
- [ ] Existing demo-site pages still load and the paywall rules still hold:
      lesson text may be public, videos stay behind purchase.
- [ ] `demo-site/content.json` stays valid JSON.
- [ ] No unrelated files are changed.

## Out of scope

- Any feature not named in the request.
- Production data, secrets, deploy or hosting config.

## Assumptions

- The demo site in `demo-site/` is the target repo for this job.
- Dry-run mode: the builder applies a deterministic patch for known
  feature kinds only; anything else is specified here and left for a
  live builder.

## Files likely to change

- `demo-site/content.json`
- `demo-site/app.js`
- `demo-site/404.html` (only for the 404-page feature)
"""


def dry_run_build(feature: str, job_id: str, worktree: Path) -> tuple[str, list[str]]:
    """Apply a real deterministic patch for known demo features.

    Returns (build.md text, list of changed paths relative to repo root).
    """
    lowered = feature.lower()
    changed: list[str] = []
    actions: list[str] = []
    site = worktree / "demo-site"

    if "unpaywall" in lowered or "public" in lowered:
        content_path = site / "content.json"
        content = json.loads(content_path.read_text(encoding="utf-8"))
        for lesson in content["course"]["lessons"]:
            lesson["publicContent"] = True
            lesson["videoPaywalled"] = True
        content_path.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
        changed.append("demo-site/content.json")
        actions.append("Set publicContent=true for all 25 lessons in "
                       "demo-site/content.json; videos stay paywalled.")
    if "copy button" in lowered or ("copy" in lowered and "code" in lowered):
        app_js = site / "app.js"
        text = app_js.read_text(encoding="utf-8")
        if "addCopyButtons" not in text:
            text += """

// Copy button for code blocks (factory job).
function addCopyButtons() {
  document.querySelectorAll("pre code").forEach((block) => {
    const button = document.createElement("button");
    button.className = "copy-button";
    button.textContent = "Copy";
    button.addEventListener("click", async () => {
      await navigator.clipboard.writeText(block.textContent);
      button.textContent = "Copied";
      setTimeout(() => { button.textContent = "Copy"; }, 1500);
    });
    block.parentElement.insertBefore(button, block);
  });
}
document.addEventListener("DOMContentLoaded", addCopyButtons);
"""
            app_js.write_text(text, encoding="utf-8")
        changed.append("demo-site/app.js")
        actions.append("Added a Copy button to every code block in demo-site/app.js.")
    if "404" in lowered:
        page = site / "404.html"
        page.write_text(
            '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            "<title>404 — Page not found</title>\n"
            '<link rel="stylesheet" href="styles.css">\n</head>\n<body>\n'
            "<main>\n<h1>404</h1>\n<p>That page does not exist.</p>\n"
            '<p><a href="index.html">Back to the course</a></p>\n</main>\n</body>\n</html>\n',
            encoding="utf-8",
        )
        changed.append("demo-site/404.html")
        actions.append("Created demo-site/404.html.")
    if "reading time" in lowered:
        content_path = site / "content.json"
        content = json.loads(content_path.read_text(encoding="utf-8"))
        for lesson in content["course"]["lessons"]:
            words = len(lesson.get("text", "").split())
            lesson["readingTimeMinutes"] = max(1, round(words / 200))
        content_path.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
        if "demo-site/content.json" not in changed:
            changed.append("demo-site/content.json")
        actions.append("Added readingTimeMinutes to every lesson in "
                       "demo-site/content.json.")
    if not actions:
        actions.append("Dry-run simulation only: no deterministic patch exists "
                       "for this feature kind, so no code was changed. Run the "
                       "job live for a real implementation.")

    changes = "\n".join(f"- `{path}`" for path in changed) or "- (none)"
    action_lines = "\n".join(f"- {a}" for a in actions)
    build_md = f"""# Build — {job_id}

## Summary

Dry-run build for: {feature}

{action_lines}

## Changes

{changes}

## Validation

- `demo-site/content.json` parses as valid JSON.
- `node --check demo-site/app.js` passes (when Node is installed).
- DRY RUN: no live Claude agent ran; this build was produced by the
  deterministic dry-run builder in `scripts/factory.py`.

## Notes

- Videos stay paywalled even when lesson text is made public.
- Re-run the job live (`python3 scripts/factory.py new "..."`) for a
  real Claude-built implementation.
"""
    return build_md, changed


def dry_run_review(reviewer: str, job_id: str) -> str:
    focus = {
        "security": "injection, auth, secrets, production data, dependencies",
        "ux": "the changed flow walked as a signed-out user",
        "ui": "layout, hierarchy, spacing, and consistency at desktop and phone width",
        "code": "correctness, edge cases, readability, and repo conventions",
    }[reviewer]
    return f"""# {reviewer.title()} Review — {job_id}

## Findings

- None blocking. (Dry-run simulation: no live reviewer ran.)

## Checks performed

- {focus}.
- Verified the changed files listed in `build.md` exist and the demo
  site still loads.

VERDICT: PASS
"""


# --------------------------------------------------------------------------
# The loop
# --------------------------------------------------------------------------

def update_job(board: dict, job: dict) -> None:
    for index, existing in enumerate(board["jobs"]):
        if existing["id"] == job["id"]:
            board["jobs"][index] = job
            break
    else:
        board["jobs"].append(job)
    job["updated"] = now_iso()
    save_board(board)


def run_stage(job: dict, agent: str, task: str, cwd: Path, dry_run: bool) -> str:
    config = load_config()
    model = config["models"][agent]
    if dry_run:
        raise RuntimeError("run_stage must not be called in dry-run mode")
    return run_claude_stage(agent, model, task, cwd)


def changed_files(worktree: Path) -> list[str]:
    out = run(["git", "-C", str(worktree), "status", "--porcelain"], check=False).stdout
    files = []
    for line in out.splitlines():
        path = line[3:].strip().strip('"')
        if path:
            files.append(path)
    return sorted(files)


def touches_escalation_area(changed: list[str], feature: str) -> list[str]:
    """Check the feature request and changed files against the escalation list.

    Only the feature request and the changed paths are scanned, never the
    full spec text: spec templates mention words like "deploy" in their
    out-of-scope section, which must not trigger an escalation by itself.
    """
    config = load_config()
    hits = []
    haystack = " ".join(changed) + "\n" + feature.lower()
    for keyword in config["escalateOn"]:
        if keyword.lower() in haystack.lower():
            hits.append(keyword)
    return hits


def run_job(job: dict, feature: str, dry_run: bool) -> dict:
    """Run spec -> build -> review rounds -> approver for one job."""
    config = load_config()
    job_dir = FACTORY_DIR / "jobs" / job["id"]
    worktree = ROOT / config["worktreeDir"] / job["id"]
    job_dir.mkdir(parents=True, exist_ok=True)

    # --- Spec -------------------------------------------------------------
    job["phase"] = "spec"
    update_job(load_board(), job)
    if dry_run:
        (job_dir / "spec.md").write_text(dry_run_spec(feature, job["id"]), encoding="utf-8")
    else:
        spec = run_stage(job, "specwriter",
                         f"Write the spec for this feature request and save it to "
                         f"factory/jobs/{job['id']}/spec.md:\n\n{feature}",
                         ROOT, dry_run)
        (job_dir / "spec.md").write_text(spec, encoding="utf-8")
    spec_text = (job_dir / "spec.md").read_text(encoding="utf-8")

    # --- Build + review rounds --------------------------------------------
    max_rounds = int(config["maxRounds"])
    for round_number in range(1, max_rounds + 1):
        job["phase"] = "build"
        update_job(load_board(), job)
        if dry_run:
            build_md, changed = dry_run_build(feature, job["id"], worktree)
            (job_dir / "build.md").write_text(build_md, encoding="utf-8")
            if changed:
                run(["git", "-C", str(worktree), "add", "-A"], check=False)
                run(["git", "-C", str(worktree), "commit", "-m",
                     f"factory {job['id']}: {job['title']}"], check=False)
        else:
            findings = ""
            if round_number > 1:
                findings = "\n\nRework findings from the previous round:\n" + "\n".join(
                    f"- {r['reviewer']}: {r['notes']}"
                    for r in job["rounds"][-1]["reviews"] if r["verdict"] != "PASS"
                )
            build = run_stage(job, "builder",
                              f"Implement the feature from factory/jobs/{job['id']}/spec.md "
                              f"in worktree {worktree}. Validate it, commit it on branch "
                              f"{job['branch']}, and write factory/jobs/{job['id']}/build.md.{findings}",
                              worktree, dry_run)
            (job_dir / "build.md").write_text(build, encoding="utf-8")
            changed = changed_files(worktree)
        job["changedFiles"] = changed

        job["phase"] = "review"
        update_job(load_board(), job)
        round_dir = job_dir / f"round-{round_number}"
        round_dir.mkdir(exist_ok=True)
        reviews = []
        for reviewer in config["reviewers"]:
            agent = f"review-{reviewer}"
            if dry_run:
                text = dry_run_review(reviewer, job["id"])
            else:
                text = run_stage(job, agent,
                                 f"Review the built feature for job {job['id']}. "
                                 f"Spec: factory/jobs/{job['id']}/spec.md. "
                                 f"Build notes: factory/jobs/{job['id']}/build.md. "
                                 f"Write your review to factory/jobs/{job['id']}/"
                                 f"round-{round_number}/review-{reviewer}.md and end "
                                 f"with exactly one line: VERDICT: PASS or "
                                 f"VERDICT: CHANGES_REQUIRED.",
                                 ROOT, dry_run)
            (round_dir / f"review-{reviewer}.md").write_text(text, encoding="utf-8")
            verdict = "PASS" if "VERDICT: PASS" in text else "CHANGES_REQUIRED"
            notes = next((line for line in text.splitlines()
                          if line.strip() and not line.startswith("#")), "")
            reviews.append({"reviewer": reviewer, "verdict": verdict, "notes": notes})
        job.setdefault("rounds", []).append({"round": round_number, "reviews": reviews})
        update_job(load_board(), job)

        if all(r["verdict"] == "PASS" for r in reviews):
            break
        if round_number == max_rounds:
            # The orchestrator escalates itself; no approver runs.
            job["phase"] = "needs-human"
            (job_dir / "decision.md").write_text(
                f"# Decision — {job['id']}\n\nDECISION: ESCALATE\n\n"
                f"## Reasons\n\nRound {max_rounds} still has CHANGES_REQUIRED findings, "
                f"and MAX_RESUMES ({config['maxResumes']}) is exhausted.\n\n"
                "## Human checklist\n\n- Read the round-3 review findings.\n"
                "- Decide whether to rework by hand or drop the job.\n",
                encoding="utf-8",
            )
            job["decision"] = "ESCALATE"
            update_job(load_board(), job)
            return job

    # --- Approver -----------------------------------------------------------
    job["phase"] = "approve"
    update_job(load_board(), job)
    hits = touches_escalation_area(job.get("changedFiles", []), feature)
    if dry_run:
        decision = "ESCALATE" if hits else "MERGE"
        reasons = (
            "Touches an escalation area: " + ", ".join(hits) + "."
            if hits else
            "All reviews passed and the change touches no escalation area."
        )
        (job_dir / "decision.md").write_text(
            f"# Decision — {job['id']}\n\nDECISION: {decision}\n\n"
            f"## Reasons\n\n{reasons}\n\n"
            "## Human checklist\n\n"
            + ("- Confirm the course-access change is intended before merging.\n"
               if hits else "- None.\n"),
            encoding="utf-8",
        )
    else:
        text = run_stage(job, "approver",
                         f"Decide the fate of job {job['id']}. Spec: "
                         f"factory/jobs/{job['id']}/spec.md. Build notes: "
                         f"factory/jobs/{job['id']}/build.md. Reviews: "
                         f"factory/jobs/{job['id']}/round-*/review-*.md. Changed "
                         f"files: {', '.join(job.get('changedFiles', []))}. Write "
                         f"factory/jobs/{job['id']}/decision.md with DECISION: "
                         f"MERGE or DECISION: ESCALATE and your reasons.",
                         ROOT, dry_run)
        (job_dir / "decision.md").write_text(text, encoding="utf-8")
        decision = "MERGE" if "DECISION: MERGE" in text else "ESCALATE"
    job["decision"] = decision
    job["phase"] = "ready" if decision == "MERGE" else "needs-human"
    update_job(load_board(), job)

    if decision == "MERGE":
        try:
            merge_job(job)
        except RuntimeError as exc:
            job["phase"] = "needs-human"
            job["mergeError"] = str(exc)
            update_job(load_board(), job)
    return job


def create_job(feature: str, dry_run: bool) -> dict:
    require_clean_tree()
    board = load_board()
    number = next_job_number(board)
    job_id = f"{number:03d}-{slugify(feature)}"
    branch = f"{load_config()['branchPrefix']}{job_id}"
    worktree = ROOT / load_config()["worktreeDir"] / job_id

    run(["git", "worktree", "add", str(worktree), "-b", branch])
    job = {
        "id": job_id,
        "title": feature,
        "feature": feature,
        "phase": "spec",
        "branch": branch,
        "worktree": str(worktree),
        "rounds": [],
        "changedFiles": [],
        "decision": None,
        "created": now_iso(),
        "updated": now_iso(),
    }
    update_job(board, job)
    return run_job(job, feature, dry_run)


def merge_job(job: dict) -> None:
    """Merge a job branch into main with --no-ff and delete the branch."""
    require_on_main()
    require_clean_tree()
    run(["git", "merge", "--no-ff", job["branch"], "-m",
         f"Merge factory {job['id']}: {job['title']}"])
    worktree = Path(job["worktree"])
    if worktree.exists():
        run(["git", "worktree", "remove", "--force", str(worktree)])
    run(["git", "branch", "-d", job["branch"]])
    job["phase"] = "merged"
    update_job(load_board(), job)


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_new(args: argparse.Namespace) -> int:
    job = create_job(args.feature, args.dry_run)
    print(f"Job {job['id']}: phase={job['phase']} decision={job['decision']}")
    print(f"Dashboard: cd factory && python3 -m http.server  # then open dashboard.html")
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    feature = peek_next_backlog_item()
    print(f"Next backlog item: {feature}")
    job = create_job(feature, args.dry_run)
    mark_backlog_item_done(feature)
    print(f"Job {job['id']}: phase={job['phase']} decision={job['decision']}")
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    board = load_board()
    job = next((j for j in board["jobs"] if j["id"] == args.job_id), None)
    if job is None:
        raise RuntimeError(f"Unknown job id: {args.job_id}")
    if job["phase"] not in ("needs-human", "ready"):
        raise RuntimeError(
            f"Job {job['id']} is in phase {job['phase']!r}; only "
            "needs-human or ready jobs can be approved."
        )
    merge_job(job)
    print(f"Job {job['id']} merged into main.")
    return 0


def cmd_rework(args: argparse.Namespace) -> int:
    board = load_board()
    job = next((j for j in board["jobs"] if j["id"] == args.job_id), None)
    if job is None:
        raise RuntimeError(f"Unknown job id: {args.job_id}")
    job_dir = FACTORY_DIR / "jobs" / job["id"]
    existing = sorted(job_dir.glob("rework-*.md"))
    note_path = job_dir / f"rework-{len(existing) + 1}.md"
    note_path.write_text(f"# Rework note — {job['id']}\n\n{args.note}\n", encoding="utf-8")
    print(f"Saved {note_path}. Start a new builder with: "
          f"factory rework is recorded; re-run the job loop from the build phase.")
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    board = load_board()
    if not board["jobs"]:
        print("No jobs yet. Run: python3 scripts/factory.py new \"feature\"")
        return 0
    print(f"{'ID':<32} {'PHASE':<12} {'DECISION':<10} ROUNDS")
    for job in board["jobs"]:
        rounds = ",".join(
            "/".join("P" if r["verdict"] == "PASS" else "C" for r in rnd["reviews"])
            for rnd in job.get("rounds", [])
        )
        print(f"{job['id']:<32} {job['phase']:<12} {str(job.get('decision')):<10} {rounds}")
    return 0


def cmd_dashboard(_args: argparse.Namespace) -> int:
    print("Serve the dashboard with:")
    print("  cd factory && python3 -m http.server 8000")
    print("Then open http://localhost:8000/dashboard.html")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AI Software Factory orchestrator")
    sub = parser.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new", help="start a job from a feature description")
    p_new.add_argument("feature")
    p_new.add_argument("--dry-run", action="store_true")
    p_new.set_defaults(func=cmd_new)

    p_next = sub.add_parser("next", help="start the next backlog item")
    p_next.add_argument("--dry-run", action="store_true")
    p_next.set_defaults(func=cmd_next)

    p_approve = sub.add_parser("approve", help="merge a needs-human job into main")
    p_approve.add_argument("job_id")
    p_approve.set_defaults(func=cmd_approve)

    p_rework = sub.add_parser("rework", help="record a human rework note for a job")
    p_rework.add_argument("job_id")
    p_rework.add_argument("note")
    p_rework.set_defaults(func=cmd_rework)

    p_status = sub.add_parser("status", help="show all jobs")
    p_status.set_defaults(func=cmd_status)

    p_dash = sub.add_parser("dashboard", help="how to serve the dashboard")
    p_dash.set_defaults(func=cmd_dashboard)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
