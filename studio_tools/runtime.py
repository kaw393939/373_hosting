"""Local studio interface and a small, explicit SSH transport for its helper."""

import base64
import json
from pathlib import Path
import shlex
import subprocess
import sys

from studio_tools import remote

ROOT = Path(__file__).resolve().parents[1]
RELEASE_FILE = ROOT / "studio" / "calculator-release.json"
RUNTIME = ROOT / "runtime" / "studio"
REMOTE_DIR = ".is373-studio/calculator"


def release_selection():
    """Read the reviewed calculator identity from the template."""
    return remote.validate_release(json.loads(RELEASE_FILE.read_text()))


def plan(config):
    """Show a deterministic plan without SSH, Docker, writes or deployment."""
    config = remote.validate_config(config)
    release = release_selection()
    return {
        "mode": remote.mode(config),
        "target": config["host"],
        "url": config["url"],
        "project": remote.PROJECT,
        "image": release["image"],
        "commit": release["commit"],
        "compose": remote.compose_model(config, release),
        "requires_sudo": config["sudo"],
        "mutates": False,
        "command_summary": [
            "Check Docker access, existing routing and studio ownership.",
            "Pull the selected image and start only its calculator Compose project.",
            "Verify image, commit, API cases and selected container preservation.",
        ],
        "limitations": [
            "No proxy, DNS, certificates, updater or application source is installed.",
            "An existing exact calculator route is recorded as adopted; "
            "it is not a new launch.",
        ],
    }


def _bundle(config):
    """Package public deployment choices and their immutable release selection."""
    return {"config": remote.validate_config(config), "release": release_selection()}


def _ssh(config, command, *, source=None, interactive=False):
    """Use existing SSH authentication without modifying its configuration."""
    arguments = ["ssh", "-t" if interactive else "-T", "-o", "ConnectTimeout=10"]
    if not interactive:
        arguments += ["-o", "BatchMode=yes"]
    arguments += [config["host"], command]
    try:
        if interactive:
            with subprocess.Popen(
                arguments,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            ) as process:
                transcript = []
                while character := process.stdout.read(1):
                    sys.stdout.write(character)
                    sys.stdout.flush()
                    transcript.append(character)
                code = process.wait()
                if code:
                    raise subprocess.CalledProcessError(code, arguments)
                return subprocess.CompletedProcess(
                    arguments, code, "".join(transcript), ""
                )
        return subprocess.run(
            arguments,
            input=source,
            capture_output=not interactive,
            text=True,
            check=True,
            timeout=None if interactive else 120,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeError(
            "The SSH operation stopped. Use your existing class SSH connection and "
            "Docker permissions in your terminal. If selected, sudo asks there; "
            "the studio does not receive or save a password."
        ) from error


def _scp(source, destination):
    """Copy only the reviewed public helper/bundle or selected evidence."""
    try:
        subprocess.run(
            [
                "scp",
                "-q",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=10",
                str(source),
                str(destination),
            ],
            check=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeError("Studio copy failed; check your usual SSH access") from error


def doctor(config):
    """Perform selected read-only checks; do not install a remote helper."""
    bundle = _bundle(config)
    config = bundle["config"]
    if config["host"] == "local":
        return remote.doctor(config, bundle["release"])
    encoded = base64.b64encode(json.dumps(bundle).encode()).decode()
    source = (ROOT / "studio_tools" / "remote.py").read_text()
    if config["sudo"]:
        script = base64.b64encode(source.encode()).decode()
        program = f"import base64; exec(base64.b64decode('{script}'))"
        command = (
            f"sudo python3 -c {shlex.quote(program)} doctor "
            f"--bundle-base64 {shlex.quote(encoded)}"
        )
        result = _ssh(config, command, interactive=True)
        return _parse_report(result.stdout)
    command = f"python3 - doctor --bundle-base64 {shlex.quote(encoded)}"
    result = _ssh(config, command, source=source)
    return json.loads(result.stdout)


def _parse_report(transcript):
    """Find the helper's JSON report after an ordinary interactive sudo prompt."""
    decoder = json.JSONDecoder()
    for position, character in enumerate(transcript):
        if character != "{":
            continue
        try:
            report, _ = decoder.raw_decode(transcript[position:])
        except ValueError:
            continue
        if isinstance(report, dict) and all(
            key in report for key in ("status", "mode", "target")
        ):
            return report
    raise RuntimeError("The SSH helper did not return its selected JSON report")


def _remote_operation(config, operation):
    """Transfer the reviewed bundle and stream an interactive operator action."""
    bundle = _bundle(config)
    config = bundle["config"]
    directory = remote.safe_directory(RUNTIME)
    bundle_file = directory / "bundle.json"
    if bundle_file.is_symlink():
        raise ValueError("Refusing a symbolic-link bundle destination")
    bundle_file.write_text(json.dumps(bundle, indent=2) + "\n")
    bundle_file.chmod(0o600)
    # This is a fixed user-owned path, not an interpolated user-supplied command.
    _ssh(
        config,
        "test ! -L .is373-studio && test ! -L .is373-studio/calculator "
        "&& install -d -m 700 .is373-studio .is373-studio/calculator",
    )
    _scp(
        ROOT / "studio_tools" / "remote.py",
        f"{config['host']}:{REMOTE_DIR}/remote.py",
    )
    _scp(bundle_file, f"{config['host']}:{REMOTE_DIR}/bundle.json")
    prefix = "sudo " if config["sudo"] else ""
    command = (
        f"{prefix}python3 {REMOTE_DIR}/remote.py {operation} "
        f"--bundle {REMOTE_DIR}/bundle.json --workdir {REMOTE_DIR}"
    )
    _ssh(config, command, interactive=True)
    report_file = directory / "report.json"
    if report_file.is_symlink():
        raise ValueError("Refusing a symbolic-link evidence destination")
    _scp(f"{config['host']}:{REMOTE_DIR}/report.json", report_file)
    report_file.chmod(0o600)
    return json.loads(report_file.read_text())


def launch(config):
    """Launch the supplied calculator, preserving the selected hosting boundary."""
    bundle = _bundle(config)
    if bundle["config"]["host"] == "local":
        return remote.launch(bundle["config"], bundle["release"], RUNTIME)
    return _remote_operation(bundle["config"], "launch")


def verify(config):
    """Repeat actual checks, keeping local-preview and hosted evidence distinct."""
    bundle = _bundle(config)
    if bundle["config"]["host"] == "local":
        return remote.verify(bundle["config"], bundle["release"], RUNTIME)
    return _remote_operation(bundle["config"], "verify")
