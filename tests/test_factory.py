"""Tests for the factory orchestrator (scripts/factory.py).

Run from the repo root:  python3 -m pytest tests/ -q
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import factory as factory_mod


def test_slugify():
    assert factory_mod.slugify("Obsidian Course Unpaywall!") == "obsidian-course-unpaywall"
    assert factory_mod.slugify("Add a 404 page") == "add-a-404-page"
    assert factory_mod.slugify("!!!") == "feature"


def test_next_job_number():
    assert factory_mod.next_job_number({"jobs": []}) == 1
    board = {"jobs": [{"id": "001-a"}, {"id": "003-c"}]}
    assert factory_mod.next_job_number(board) == 4


def test_escalation_detection():
    assert factory_mod.touches_escalation_area(
        ["demo-site/content.json"], "Obsidian course unpaywall") == ["course", "unpaywall"]
    assert factory_mod.touches_escalation_area(
        ["src/billing.py"], "change Stripe billing") == ["stripe", "billing"]
    assert factory_mod.touches_escalation_area(
        ["demo-site/app.js"], "fix a typo") == []
    # Template boilerplate must not escalate: the checker scans only the
    # feature request and changed files, never the full spec text.
    assert factory_mod.touches_escalation_area(
        ["demo-site/app.js"], "Add a 404 page") == []


def test_dry_run_review_verdicts():
    for reviewer in ["security", "ux", "ui", "code"]:
        assert "VERDICT: PASS" in factory_mod.dry_run_review(reviewer, "001-x")


def test_dry_run_build_unpaywall(tmp_path):
    worktree = tmp_path / "wt"
    site = worktree / "demo-site"
    site.mkdir(parents=True)
    content = {"course": {"lessons": [
        {"id": "lesson-01", "publicContent": False, "videoPaywalled": True},
        {"id": "lesson-02", "publicContent": False, "videoPaywalled": True},
    ]}}
    (site / "content.json").write_text(json.dumps(content))
    (site / "app.js").write_text("// app\n")
    build_md, changed = factory_mod.dry_run_build(
        "Obsidian course unpaywall", "001-x", worktree)
    updated = json.loads((site / "content.json").read_text())
    assert all(lesson["publicContent"] for lesson in updated["course"]["lessons"])
    assert all(lesson["videoPaywalled"] for lesson in updated["course"]["lessons"])
    assert "demo-site/content.json" in changed
    assert "publicContent" in build_md


def test_dry_run_build_unknown_feature_is_honest(tmp_path):
    worktree = tmp_path / "wt"
    (worktree / "demo-site").mkdir(parents=True)
    build_md, changed = factory_mod.dry_run_build(
        "Teleport the user to the moon", "002-x", worktree)
    assert changed == []
    assert "no code was changed" in build_md


@pytest.fixture()
def git_repo(tmp_path, monkeypatch):
    """A throwaway git repo with the factory tree copied in."""
    repo = tmp_path / "repo"
    shutil_copy = __import__("shutil").copytree(ROOT, repo, ignore=__import__("shutil").ignore_patterns(
        ".git", "__pycache__", ".worktrees", "factory/jobs", "factory/board.json"))
    monkeypatch.setattr(factory_mod, "ROOT", repo)
    monkeypatch.setattr(factory_mod, "FACTORY_DIR", repo / "factory")
    monkeypatch.setattr(factory_mod, "CONFIG_PATH", repo / "factory" / "config.json")
    monkeypatch.setattr(factory_mod, "BOARD_PATH", repo / "factory" / "board.json")
    monkeypatch.setattr(factory_mod, "BOARD_EXAMPLE_PATH", repo / "factory" / "board.example.json")
    monkeypatch.setattr(factory_mod, "BACKLOG_PATH", repo / "factory" / "backlog.md")
    monkeypatch.setattr(factory_mod, "AGENTS_DIR", repo / ".claude" / "agents")
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@factory.local"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Factory Test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True)
    return repo


def test_next_takes_backlog_item(git_repo):
    import argparse
    assert factory_mod.cmd_next(argparse.Namespace(dry_run=True)) == 0
    items = factory_mod.read_backlog_items()
    assert items[0]["done"] is True
    assert items[1]["done"] is False
    board = json.loads((git_repo / "factory" / "board.json").read_text())
    assert board["jobs"][0]["id"].startswith("001-")
    assert "reading" in board["jobs"][0]["title"].lower()
    content = json.loads((git_repo / "demo-site" / "content.json").read_text())
    assert all("readingTimeMinutes" in lesson for lesson in content["course"]["lessons"])


def test_full_dry_run_loop_and_merge(git_repo):
    repo = git_repo
    job = factory_mod.create_job("Obsidian course unpaywall", dry_run=True)
    assert job["id"] == "001-obsidian-course-unpaywall"
    assert job["phase"] == "needs-human"  # course access escalates
    assert job["decision"] == "ESCALATE"
    job_dir = repo / "factory" / "jobs" / job["id"]
    assert (job_dir / "spec.md").exists()
    assert (job_dir / "build.md").exists()
    assert (job_dir / "decision.md").exists()
    assert (job_dir / "round-1" / "review-code.md").exists()
    board = json.loads((repo / "factory" / "board.json").read_text())
    assert board["jobs"][0]["phase"] == "needs-human"

    factory_mod.merge_job(job)
    assert job["phase"] == "merged"
    log = subprocess.run(["git", "log", "--oneline"], cwd=repo, capture_output=True,
                         text=True, check=True).stdout
    assert "Merge factory 001-obsidian-course-unpaywall" in log
    branches = subprocess.run(["git", "branch"], cwd=repo, capture_output=True,
                              text=True, check=True).stdout
    assert "factory/001-obsidian-course-unpaywall" not in branches
    assert not (repo / ".worktrees" / job["id"]).exists()


def test_full_dry_run_auto_merge(git_repo):
    job = factory_mod.create_job("Add a 404 page", dry_run=True)
    assert job["phase"] == "merged"
    assert job["decision"] == "MERGE"
    assert (git_repo / "demo-site" / "404.html").exists()
