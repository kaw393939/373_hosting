"""Read evidence and GitHub state without treating activity as understanding."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "runtime" / "studio"
LESSON = "STUDIO-001"
INSTRUCTOR = "kaw393939/373_hosting"
CHECKPOINTS = (
    "Prediction",
    "Check interpretation",
    "Browser observation",
    "Keep decision",
)
REQUIRED_JOBS = {"validate", "integration-contract", "studio"}


def save_json(path, value):
    """Write local evidence atomically, keeping configuration out of Git."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(path)


def load_config():
    """Explain the next setup step when no local target has been agreed."""
    path = STATE / "config.json"
    if not path.exists():
        raise ValueError(
            "No target yet. Ask your coach to help run configure; "
            "see studio/lesson-01.md."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def repository():
    """Require the class SSH remote and extract its GitHub repository."""
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    match = re.fullmatch(
        r"git@github\.com:([\w.-]+/[\w.-]+?)(?:\.git)?\s*", result.stdout
    )
    if not match:
        raise ValueError(
            "Use your own GitHub SSH clone: git@github.com:USERNAME/REPOSITORY.git"
        )
    return match.group(1)


def github(path):
    """Read GitHub; optional existing token supports private copies, never printed."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "IS373-Studio"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request("https://api.github.com/" + path, headers=headers)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def issue_number(url, repo, kind="issues"):
    """Reject other students' evidence, pull requests used as issues and unsafe URLs."""
    match = re.fullmatch(
        r"https://github\.com/" + re.escape(repo) + "/" + kind + r"/([1-9]\d*)", url
    )
    if not match:
        raise ValueError(f"Use an actual {kind} URL in your repository: {repo}")
    return int(match.group(1))


def fingerprint(config):
    """Invalidate runtime evidence when the selected deployment target changes."""
    selection = {name: config.get(name) for name in ("host", "url", "network", "sudo")}
    return hashlib.sha256(json.dumps(selection, sort_keys=True).encode()).hexdigest()


def record_runtime(config, report):
    """Keep a dated observation, rather than a claim of continuously live health."""
    report = dict(report)
    report["observed_at"] = datetime.now(timezone.utc).isoformat()
    report["target_fingerprint"] = fingerprint(config)
    report["url"] = config["url"]
    save_json(STATE / "verified.json", report)
    return report


def learner_sections(text):
    """Find missing contribution records, without scoring their meaning."""
    sections = {}
    pending = re.compile(
        r"^(pending|not yet evidenced|not recorded|not reviewed|"
        r"earlier conversation unavailable)\b",
        re.I,
    )
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    for name in (*CHECKPOINTS, "Review"):
        match = re.search(
            r"^## " + re.escape(name) + r"\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S
        )
        value = match.group(1).strip() if match else ""
        lines = [
            line.strip().lstrip("-*+> ").strip("*_` ")
            for line in value.splitlines()
            if line.strip()
        ]
        lines = [line for line in lines if line]
        sections[name] = bool(lines) and not pending.match(lines[0])
    return sections


def github_evidence(config, repo):
    """Verify actual lesson issue and PR/check state, recording access gaps honestly."""
    result = {"issue": False, "pr": False, "ci": False, "merged": False, "details": []}
    if not config.get("issue_url"):
        result["details"].append(
            "Create your lesson issue, then record its URL with issue --url."
        )
        return result
    try:
        number = issue_number(config["issue_url"], repo)
        issue = github(f"repos/{repo}/issues/{number}")
        if issue.get("pull_request") or "<!-- studio:STUDIO-001 -->" not in (
            issue.get("body") or ""
        ):
            raise ValueError("The issue must use the STUDIO-001 lesson template.")
        result.update(
            issue=True, issue_state=issue["state"], issue_created_at=issue["created_at"]
        )
        if not config.get("pr_url"):
            result["details"].append(
                "After your reviewed record is committed, "
                "link its actual PR with issue --pr."
            )
            return result
        number = issue_number(config["pr_url"], repo, "pull")
        pull = github(f"repos/{repo}/pulls/{number}")
        issue_ref = (
            rf"(?:(?<![\w/#])#|https://github\.com/{re.escape(repo)}/issues/)"
            rf"{issue['number']}(?![\w/?#])"
        )
        if not re.search(issue_ref, pull.get("body") or ""):
            raise ValueError("The PR must reference your actual lesson issue.")
        result.update(
            pr=True,
            merged=bool(pull.get("merged_at")),
            pr_sha=pull["head"]["sha"],
            publication_shas=[
                value
                for value in (pull["head"]["sha"], pull.get("merge_commit_sha"))
                if value
            ],
        )
        commit = pull.get("merge_commit_sha") or pull["head"]["sha"]
        checks = github(f"repos/{repo}/commits/{commit}/check-runs?per_page=100")
        latest = {}
        for check in sorted(checks.get("check_runs", []), key=lambda row: row["id"]):
            latest[check["name"]] = check
        result["ci"] = all(
            latest.get(name, {}).get("conclusion") == "success"
            for name in REQUIRED_JOBS
        )
        result["checks"] = {
            name: latest.get(name, {}).get("conclusion", "not found")
            for name in sorted(REQUIRED_JOBS)
        }
        if not result["ci"]:
            result["details"].append(
                "Required CI is pending, missing or failed; inspect the linked PR."
            )
    except (ValueError, KeyError, OSError, urllib.error.URLError) as error:
        result["details"].append(
            f"GitHub evidence not verified: {error}. "
            "Your coach can help with access; do not paste a token."
        )
    return result


def publication_state(remote):
    """Bind local records to the actual PR revision, including clean tracked files."""
    result = {"tracked": False, "clean": False, "revision_matches": False}
    try:

        def git(*arguments):
            return subprocess.run(
                ["git", *arguments],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()

        git(
            "ls-files",
            "--error-unmatch",
            "LEARNING.md",
            "SPEC.md",
            "studio/evidence.json",
        )
        result["tracked"] = True
        result["clean"] = not git("status", "--porcelain")
        result["revision_matches"] = git("rev-parse", "HEAD") in remote.get(
            "publication_shas", []
        )
    except (OSError, subprocess.CalledProcessError):
        pass
    return result


def status(config, repo, online=True):
    """Compute progress from evidence; a closed issue alone is insufficient."""
    release = json.loads((ROOT / "studio" / "calculator-release.json").read_text())
    report = (
        json.loads((STATE / "verified.json").read_text())
        if (STATE / "verified.json").exists()
        else {}
    )
    checks = report.get("checks", {})
    digest = release["image"].split("@", 1)[1]
    runtime = bool(
        report.get("status") == "passed"
        and report.get("mode") == "hosted"
        and report.get("target_fingerprint") == fingerprint(config)
        and report.get("expected", {}).get("image") == release["image"]
        and report.get("expected", {}).get("commit") == release["commit"]
        and report.get("actual", {}).get("commit") == release["commit"]
        and report.get("actual", {}).get("environment") == "production"
        and any(
            item.endswith("@" + digest)
            for item in report.get("actual", {}).get("repo_digests", [])
        )
        and checks.get("health_identity") == "passed"
        and checks.get("trusted_public_https") is True
        and checks.get("positive_multiply") == {"status": 200, "result": 42}
        and checks.get("negative_division_by_zero") == {"status": 400}
        and checks.get("negative_numeric_string") == {"status": 422}
        and report.get("preservation", {}).get("unchanged") is True
    )
    learning = (ROOT / "LEARNING.md").read_text(encoding="utf-8")
    sections = learner_sections(learning)
    remote = (
        github_evidence(config, repo)
        if online
        else {"details": ["GitHub not checked (--offline)."]}
    )
    exported = ROOT / "studio" / "evidence.json"
    published = False
    if exported.exists() and report:
        published = json.loads(exported.read_text()) == public_report(report)
    publication = publication_state(remote)
    ready = (
        all(publication.values())
        and runtime
        and published
        and all(sections.values())
        and all(remote.get(key) for key in ("issue", "pr", "ci", "merged"))
        and remote.get("issue_state") == "closed"
    )
    return {
        "lesson": LESSON,
        "runtime_observation": runtime,
        "observation_time": report.get("observed_at"),
        "evidence_exported": published,
        "publication": publication,
        "learner_records": sections,
        "github": remote,
        "ready_for_instructor_review": ready,
        "scope": (
            "Recorded evidence and latest selected GitHub checks; "
            "no automatic grade, authorship or understanding certification."
        ),
    }


def public_report(report):
    """Publish an explicit allowlist, excluding SSH details and raw host output."""
    names = (
        "status",
        "mode",
        "provenance",
        "new_launch",
        "expected",
        "actual",
        "checks",
        "preservation",
        "limitations",
        "observed_at",
        "url",
    )
    result = {name: report[name] for name in names if name in report}
    if "actual" in result:
        allowed = (
            "image_id",
            "repo_digests",
            "commit",
            "environment",
            "container_id",
            "architecture",
            "os",
        )
        result["actual"] = {
            name: result["actual"][name] for name in allowed if name in result["actual"]
        }
    return result


def display(result):
    """Show one useful next checkpoint, always accompanying icons with text."""
    print("STUDIO-001 · Launch the calculator")
    print(
        ("✅ Recorded" if result["runtime_observation"] else "🟡 Needed")
        + ": hosted runtime verification"
    )
    if result["observation_time"]:
        print(
            "   Observed: "
            + result["observation_time"]
            + " (not continuous monitoring)"
        )
    for name, present in result["learner_records"].items():
        print(
            ("✅ Recorded" if present else "🟡 Needed")
            + ": "
            + name
            + " (record presence only)"
        )
    for detail in result["github"]["details"]:
        print("🟡 " + detail)
    if result["ready_for_instructor_review"]:
        print(
            "✅ Evidence ready for instructor review. "
            "This is not a grade or certification of understanding."
        )
    elif not result["learner_records"]["Prediction"]:
        print(
            "👉 Next: predict the request path with your coach before the launch plan."
        )
    elif not result["runtime_observation"]:
        print(
            "👉 Next: ask your coach to help configure, plan, "
            "launch and verify your actual hosted calculator."
        )
    else:
        missing = next(
            (
                name
                for name, present in result["learner_records"].items()
                if not present
            ),
            None,
        )
        if missing:
            print(
                "👉 Next: discuss "
                + missing.lower()
                + " with your coach; use an actual observation or explanation."
            )
        elif not result["evidence_exported"]:
            print(
                "👉 Next: review the sanitized runtime report, "
                "then run report before committing."
            )
        elif not all(result["publication"].values()):
            print(
                "👉 Next: commit and publish your reviewed records, then use the "
                "clean revision from your linked PR. Your coach can help. "
                "Local unpublished changes cannot complete the lesson."
            )
        else:
            print(
                "👉 Next: review the linked issue, PR "
                "and required checks with your coach."
            )
