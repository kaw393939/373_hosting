#!/usr/bin/env python3
"""One prepared entry point for STUDIO-001. Run on your laptop in your clone."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import webbrowser

from studio_tools import progress, runtime

ROOT = Path(__file__).resolve().parent


def setup():
    """Install the pinned class checks in this clone, after connecting the coach."""
    if sys.version_info < (3, 12):
        raise ValueError(
            "Use the class Python 3.12 or later; ask your coach to locate it."
        )
    environment = ROOT / ".venv"
    python = environment / (
        "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
    )
    if not python.exists():
        subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True)
    subprocess.run(
        [str(python), "-m", "pip", "install", "-r", "requirements-studio.txt"],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [str(python), "-m", "playwright", "install", "chromium"], cwd=ROOT, check=True
    )
    print(
        "✅ Setup complete. Return to your coach to agree the server target. "
        "Full browser checks use local Docker or the prepared GitHub CI job."
    )


def configure(args):
    """Save only an explicit, validated target; never infer another person's host."""
    repo = progress.repository()
    if repo == progress.INSTRUCTOR:
        raise ValueError(
            "This is the instructor template. "
            "Create your own template copy and SSH-clone it first."
        )
    config = {
        "host": args.host,
        "url": args.url,
        "network": args.network,
        "sudo": args.sudo,
    }
    runtime.plan(config)
    path = progress.STATE / "config.json"
    if path.exists():
        previous = progress.load_config()
        for name in ("issue_url", "pr_url"):
            if previous.get(name):
                config[name] = previous[name]
    progress.save_json(path, config)
    print("✅ Target saved locally; no deployment or server configuration was changed.")
    print("👉 Next: python3 studio.py plan")


def lesson_issue(args):
    """Use GitHub's existing UI/connector; no extra CLI or pasted token is required."""
    repo = progress.repository()
    if repo == progress.INSTRUCTOR:
        raise ValueError(
            "Create the lesson issue in your own template copy, "
            "not the instructor repository."
        )
    if args.url or args.pr:
        config = progress.load_config()
        for value, key, kind in (
            (args.url, "issue_url", "issues"),
            (args.pr, "pr_url", "pull"),
        ):
            if value:
                progress.issue_number(value, repo, kind)
                config[key] = value
        progress.save_json(progress.STATE / "config.json", config)
        print(
            "✅ Actual evidence link saved. "
            "status verifies its GitHub contents separately."
        )
        return
    url = f"https://github.com/{repo}/issues/new?template=studio-calculator.md"
    print(
        "Create one STUDIO-001 issue using this form "
        "(or your coach's GitHub connector):"
    )
    print(url)
    if args.open:
        webbrowser.open(url)
    print(
        "Then let your coach record its real URL with: "
        "python3 studio.py issue --url ISSUE_URL"
    )


def check(fast):
    """Run prepared formatting, analysis and meaningful unit/browser checks."""
    python = (
        ROOT
        / ".venv"
        / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    )
    if not python.exists():
        raise ValueError(
            "Run python3 studio.py setup first; your coach can help with errors."
        )
    paths = ["studio.py", "studio_tools", "studio_tests"]
    commands = [
        ("Black · studio code", ["black", "--check", *paths]),
        ("Pylint · studio code", ["pylint", "studio.py", "studio_tools"]),
        (
            "pytest · hosting and studio unit/integration checks",
            ["pytest", "-q", "-m", "not e2e"],
        ),
    ]
    if not fast:
        commands.append(
            ("pytest · real image and Chromium", ["pytest", "-q", "-m", "e2e"])
        )
    failed = []
    for name, arguments in commands:
        print("\n" + name, flush=True)
        result = subprocess.run(
            [str(python), "-m", *arguments],
            cwd=ROOT,
            check=False,
            env=dict(os.environ, STUDIO_DOCKER_E2E="1") if not fast else None,
        )
        if result.returncode:
            failed.append(name)
    if failed:
        raise ValueError("Checks failed: " + "; ".join(failed))
    if fast:
        print(
            "🟡 Fast checks passed. E2E was not run; "
            "full check or required CI is still needed."
        )
    else:
        print(
            "✅ Configured checks passed. They do not prove "
            "your public deployment or learner understanding."
        )


def runtime_step(config, operation):
    """Save actual observations and show each remote report only once."""
    report = getattr(runtime, operation)(config)
    if operation in ("launch", "verify"):
        report = progress.record_runtime(config, report)
    # Interactive SSH streams the helper report and the ordinary sudo prompt.
    streamed = config["host"] != "local" and (
        operation in ("launch", "verify") or (operation == "doctor" and config["sudo"])
    )
    if not streamed:
        print(json.dumps(report, indent=2))
    elif operation in ("launch", "verify"):
        print("✅ Dated runtime observation saved locally; use report to export.")


def main():
    """Keep each command explicit and make failures useful to a learner."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("setup", help="prepare this clone's pinned checks and Chromium")
    target = commands.add_parser(
        "configure", help="save the agreed target locally; no server change"
    )
    target.add_argument(
        "--host",
        required=True,
        help="your usual SSH USER@HOST or alias; local is a preview only",
    )
    target.add_argument("--url", required=True, help="your calculator's HTTPS origin")
    target.add_argument(
        "--network", default="hosting-web", help="existing Traefik network"
    )
    target.add_argument(
        "--sudo",
        action="store_true",
        help="Docker requires sudo on this server; enter it privately in your terminal",
    )
    for name, help_text in {
        "plan": "show the proposed calculator deployment; no server change",
        "doctor": "check access and the existing proxy network",
        "launch": "launch only the agreed calculator project",
        "verify": "repeat image, HTTPS and API checks on the hosted app",
        "report": "export sanitized runtime evidence for review before publishing",
    }.items():
        commands.add_parser(name, help=help_text)
    issue = commands.add_parser(
        "issue", help="find the lesson issue form or record actual issue/PR links"
    )
    issue.add_argument("--url", help="the lesson issue URL in your own repository")
    issue.add_argument("--pr", help="the evidence PR URL in your own repository")
    issue.add_argument(
        "--open", action="store_true", help="open the form in your browser"
    )
    state = commands.add_parser(
        "status", help="show verified evidence and one missing checkpoint"
    )
    state.add_argument(
        "--offline",
        action="store_true",
        help="skip GitHub access; never reports full completion",
    )
    tests = commands.add_parser(
        "check", help="Black, Pylint, pytest and real-image Chromium checks"
    )
    tests.add_argument(
        "--fast", action="store_true", help="omit E2E locally; not a full check"
    )
    args = parser.parse_args()
    try:
        if args.command == "setup":
            setup()
        elif args.command == "configure":
            configure(args)
        elif args.command == "issue":
            lesson_issue(args)
        elif args.command == "check":
            check(args.fast)
        else:
            config = progress.load_config()
            if args.command == "status":
                progress.display(
                    progress.status(config, progress.repository(), not args.offline)
                )
            elif args.command == "report":
                report = json.loads((progress.STATE / "verified.json").read_text())
                if report.get("target_fingerprint") != progress.fingerprint(config):
                    raise ValueError(
                        "Target changed. Run verify before exporting its evidence."
                    )
                progress.save_json(
                    ROOT / "studio" / "evidence.json", progress.public_report(report)
                )
                print(
                    "✅ Sanitized runtime evidence exported to studio/evidence.json. "
                    "Review it before committing."
                )
            else:
                runtime_step(config, args.command)
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        parser.exit(
            1,
            f"🟡 {error}\n"
            "Your coach can help resolve this step; no completion has been recorded.\n",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
