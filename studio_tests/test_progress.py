"""Completion records must not turn missing evidence into a passing claim."""

import json
import subprocess
from unittest.mock import patch

import pytest

from studio_tools import progress


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(progress, "ROOT", tmp_path)
    monkeypatch.setattr(progress, "STATE", tmp_path / "runtime" / "studio")
    (tmp_path / "studio").mkdir()
    (tmp_path / "studio" / "calculator-release.json").write_text(
        json.dumps({"image": "registry/image@sha256:" + "a" * 64, "commit": "b" * 40})
    )
    (tmp_path / "LEARNING.md").write_text(
        "\n".join(f"## {name}\nPending\n" for name in (*progress.CHECKPOINTS, "Review"))
    )
    return tmp_path


def target():
    return {
        "host": "student@host",
        "url": "https://calculator.example.org",
        "network": "web",
        "sudo": False,
    }


def report():
    return {
        "status": "passed",
        "mode": "hosted",
        "provenance": "launched",
        "expected": {"image": "registry/image@sha256:" + "a" * 64, "commit": "b" * 40},
        "actual": {
            "commit": "b" * 40,
            "environment": "production",
            "repo_digests": ["registry/image@sha256:" + "a" * 64],
        },
        "checks": {
            "health_identity": "passed",
            "trusted_public_https": True,
            "positive_multiply": {"status": 200, "result": 42},
            "negative_division_by_zero": {"status": 400},
            "negative_numeric_string": {"status": 422},
        },
        "preservation": {"unchanged": True},
    }


def test_no_records_do_not_complete_studio(workspace):
    result = progress.status(target(), "student/studio", online=False)
    assert not result["runtime_observation"]
    assert not result["ready_for_instructor_review"]
    assert not any(result["learner_records"].values())


@pytest.mark.parametrize(
    "change",
    [
        {"mode": "local-preview"},
        {"status": "failed"},
        {"actual": {"commit": "c" * 40, "environment": "production"}},
        {"preservation": {"unchanged": False}},
    ],
)
def test_preview_failure_stale_release_or_unrelated_change_cannot_complete(
    workspace, change
):
    evidence = report() | change
    progress.record_runtime(target(), evidence)
    assert not progress.status(target(), "student/studio", online=False)[
        "runtime_observation"
    ]


def test_changed_target_invalidates_recorded_runtime(workspace):
    progress.record_runtime(target(), report())
    changed = target() | {"url": "https://other.example.org"}
    assert not progress.status(changed, "student/studio", online=False)[
        "runtime_observation"
    ]


def test_closed_issue_is_not_enough_without_runtime_and_learner_records(workspace):
    remote = {
        "issue": True,
        "issue_state": "closed",
        "pr": True,
        "merged": True,
        "ci": True,
        "details": [],
    }
    with patch.object(progress, "github_evidence", return_value=remote):
        assert not progress.status(target(), "student/studio")[
            "ready_for_instructor_review"
        ]


def test_complete_evidence_still_means_review_readiness_not_understanding(workspace):
    evidence = progress.record_runtime(target(), report())
    progress.save_json(
        workspace / "studio" / "evidence.json", progress.public_report(evidence)
    )
    (workspace / "LEARNING.md").write_text(
        "# Test fixture, not a real learner\n"
        + "\n".join(
            f"## {name}\nActual labeled fixture contribution; assistance disclosed.\n"
            for name in (*progress.CHECKPOINTS, "Review")
        )
    )
    remote = {
        "issue": True,
        "issue_state": "closed",
        "pr": True,
        "merged": True,
        "ci": True,
        "details": [],
    }
    with patch.object(progress, "github_evidence", return_value=remote):
        result = progress.status(target(), "student/studio")
    assert not result["ready_for_instructor_review"]
    with (
        patch.object(progress, "github_evidence", return_value=remote),
        patch.object(
            progress,
            "publication_state",
            return_value={"tracked": True, "clean": True, "revision_matches": True},
        ),
    ):
        result = progress.status(target(), "student/studio")
    assert result["ready_for_instructor_review"]
    assert "no automatic grade" in result["scope"]


def test_pending_unavailable_or_missing_sections_remain_missing():
    text = "## Prediction\nEarlier conversation unavailable\n## Review\nNot yet evidenced\n"
    assert not any(progress.learner_sections(text).values())


def test_export_does_not_include_private_top_level_fields():
    evidence = report() | {
        "ssh_host": "private-alias",
        "raw_inspect": {"secret": "never publish"},
    }
    exported = progress.public_report(evidence)
    assert "ssh_host" not in exported
    assert "raw_inspect" not in exported


def test_export_limits_actual_image_fields_even_if_future_report_grows():
    evidence = report()
    evidence["actual"]["environment_variables"] = {"SECRET": "never publish"}
    assert "environment_variables" not in progress.public_report(evidence)["actual"]


def test_open_issue_cannot_be_reported_as_finished(workspace):
    evidence = progress.record_runtime(target(), report())
    progress.save_json(
        workspace / "studio" / "evidence.json", progress.public_report(evidence)
    )
    (workspace / "LEARNING.md").write_text(
        "\n".join(
            f"## {name}\nRecorded fixture contribution.\n"
            for name in (*progress.CHECKPOINTS, "Review")
        )
    )
    remote = {
        "issue": True,
        "issue_state": "open",
        "pr": True,
        "merged": True,
        "ci": True,
        "details": [],
    }
    with patch.object(progress, "github_evidence", return_value=remote):
        assert not progress.status(target(), "student/studio")[
            "ready_for_instructor_review"
        ]


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/other/repo/issues/1",
        "https://github.com/student/studio/pull/1",
        "http://github.com/student/studio/issues/1",
        "https://github.com/student/studio/issues/1?token=secret",
    ],
)
def test_other_repository_wrong_kind_or_unsafe_issue_link_is_rejected(url):
    with pytest.raises(ValueError):
        progress.issue_number(url, "student/studio")


def test_github_checks_are_bound_to_pr_commit_and_required_names():
    answers = [
        {
            "number": 1,
            "state": "closed",
            "created_at": "2026-10-27T00:00:00Z",
            "body": "<!-- studio:STUDIO-001 -->",
        },
        {
            "body": "Refs #1",
            "head": {"sha": "b" * 40},
            "merge_commit_sha": "c" * 40,
            "merged_at": "2026-10-27T01:00:00Z",
        },
        {
            "check_runs": [
                {"id": i, "name": name, "conclusion": "success"}
                for i, name in enumerate(progress.REQUIRED_JOBS)
            ]
        },
    ]
    config = target() | {
        "issue_url": "https://github.com/student/studio/issues/1",
        "pr_url": "https://github.com/student/studio/pull/2",
    }
    with patch.object(progress, "github", side_effect=answers) as request:
        result = progress.github_evidence(config, "student/studio")
    assert result["ci"]
    assert "/commits/" + "c" * 40 + "/check-runs" in request.call_args.args[0]


def test_latest_failed_check_is_not_hidden_by_an_earlier_success():
    answers = [
        {
            "number": 1,
            "state": "open",
            "created_at": "2026-10-27T00:00:00Z",
            "body": "<!-- studio:STUDIO-001 -->",
        },
        {
            "body": "Refs #1",
            "head": {"sha": "b" * 40},
            "merge_commit_sha": "c" * 40,
            "merged_at": None,
        },
        {
            "check_runs": [
                {"id": i, "name": name, "conclusion": "success"}
                for i, name in enumerate(progress.REQUIRED_JOBS)
            ]
            + [{"id": 99, "name": "studio", "conclusion": "failure"}]
        },
    ]
    config = target() | {
        "issue_url": "https://github.com/student/studio/issues/1",
        "pr_url": "https://github.com/student/studio/pull/2",
    }
    with patch.object(progress, "github", side_effect=answers):
        assert not progress.github_evidence(config, "student/studio")["ci"]


def test_inaccessible_github_is_reported_as_unverified():
    config = target() | {"issue_url": "https://github.com/student/studio/issues/1"}
    with patch.object(progress, "github", side_effect=OSError("access unavailable")):
        result = progress.github_evidence(config, "student/studio")
    assert not result["issue"]
    assert "not verified" in result["details"][0]


@pytest.mark.parametrize(
    "pending",
    [
        "**Pending.**",
        "- Pending",
        "> Not recorded",
        "`Pending`",
        "---\nPending",
        "***",
        "  <!--\n hidden note\n -->\nPending",
    ],
)
def test_formatted_missing_records_remain_missing(pending):
    assert not progress.learner_sections("## Prediction\n" + pending)["Prediction"]


def test_publication_requires_tracked_clean_records_at_the_linked_pr(workspace):
    def git(*arguments):
        return subprocess.run(
            ["git", *arguments],
            cwd=workspace,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init", "-b", "main")
    git("config", "user.name", "Studio fixture")
    git("config", "user.email", "fixture@example.org")
    (workspace / "SPEC.md").write_text("# Fixture")
    (workspace / "studio" / "evidence.json").write_text("{}")
    git("add", ".")
    git("commit", "-m", "Reviewed fixture")
    remote = {"publication_shas": [git("rev-parse", "HEAD")]}
    assert all(progress.publication_state(remote).values())
    (workspace / "LEARNING.md").write_text("Unpublished learner edit")
    assert not progress.publication_state(remote)["clean"]
    git("add", ".")
    git("commit", "-m", "Unlinked new revision")
    assert not progress.publication_state(remote)["revision_matches"]
    (workspace / "new-record.md").write_text("Untracked")
    assert not progress.publication_state(remote)["clean"]


@pytest.mark.parametrize(
    "body",
    ["Refs other/repo#1", "Refs https://github.com/other/repo/issues/1", "Refs #10"],
)
def test_foreign_or_different_issue_reference_does_not_link_own_issue(body):
    answers = [
        {
            "number": 1,
            "state": "open",
            "created_at": "now",
            "body": "<!-- studio:STUDIO-001 -->",
        },
        {"body": body, "head": {"sha": "b" * 40}},
    ]
    config = target() | {
        "issue_url": "https://github.com/student/studio/issues/1",
        "pr_url": "https://github.com/student/studio/pull/2",
    }
    with patch.object(progress, "github", side_effect=answers):
        result = progress.github_evidence(config, "student/studio")
    assert not result["pr"]
