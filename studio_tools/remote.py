"""Small, bounded calculator operations; also runs as a copied SSH helper.

Only selected Docker fields are read. This helper never provisions a host,
changes its proxy, installs an updater, or handles an authentication secret.
"""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import ssl
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

PROJECT = "is373-studio-calculator"
ROUTER = "is373-studio-calculator"
LESSON = "STUDIO-001"
OWNER_LABEL = "org.is373.studio.owner"
LESSON_LABEL = "org.is373.studio.lesson"
HOSTNAME = re.compile(
    r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+" + r"[a-z]{2,63}$"
)
NETWORK = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,62}$")
SSH_TARGET = re.compile(
    r"[A-Za-z_][A-Za-z0-9_-]{0,31}@"
    + r"[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$"
)
SSH_ALIAS = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,252}$")
IMAGE = re.compile(r"(?:docker\.io/)?kaw393939/is373_ci_cd@sha256:[0-9a-f]{64}$")
TLS_READY_TIMEOUT = 60
TLS_RETRY_INTERVAL = 2


def validate_config(config):
    """Normalize the small public configuration before performing any operation."""
    if not isinstance(config, dict):
        raise ValueError("Studio configuration must be a JSON object")
    host = config.get("host", "local")
    if not isinstance(host, str) or not (
        host == "local" or SSH_TARGET.fullmatch(host) or SSH_ALIAS.fullmatch(host)
    ):
        raise ValueError("Host must be local, a safe SSH alias, or USER@HOST")
    network = config.get("network", "hosting-web")
    if (
        not isinstance(network, str)
        or not NETWORK.fullmatch(network)
        or network in {"host", "none", "bridge"}
    ):
        raise ValueError("Use the name of the existing private proxy network")
    use_sudo = config.get("sudo", False)
    if not isinstance(use_sudo, bool):
        raise ValueError("sudo must be true or false")
    origin = _validate_origin(config.get("url", ""), host)
    return {"host": host, "url": origin, "network": network, "sudo": use_sudo}


def _validate_origin(origin, host):
    """Keep public HTTPS and local-only HTTP as distinct supported modes."""
    if not isinstance(origin, str) or any(character.isspace() for character in origin):
        raise ValueError("URL must be an origin without credentials or a path")
    try:
        parsed = urllib.parse.urlsplit(origin)
        port = parsed.port
    except ValueError as error:
        raise ValueError("Invalid URL port") from error
    if any((parsed.username, parsed.password, parsed.query, parsed.fragment)):
        raise ValueError("Use an origin without credentials, a query or fragment")
    if parsed.path not in {"", "/"} or not parsed.hostname:
        raise ValueError("Use an origin without credentials, a path, query or fragment")
    if parsed.scheme == "http":
        if host != "local" or parsed.hostname != "127.0.0.1":
            raise ValueError("Plain HTTP is only allowed for a local 127.0.0.1 preview")
        if port is None or not 1024 <= port <= 65535:
            raise ValueError("Local preview needs an explicit port from 1024 to 65535")
        origin = f"http://127.0.0.1:{port}"
    elif parsed.scheme == "https":
        if not HOSTNAME.fullmatch(parsed.hostname) or port not in {None, 443}:
            raise ValueError(
                "Hosted mode needs a DNS hostname on normal HTTPS port 443"
            )
        origin = f"https://{parsed.hostname}"
    else:
        raise ValueError("Use HTTPS for a hosted site or HTTP on local 127.0.0.1")
    return origin


def validate_release(release):
    """Accept only the supplied digest-pinned calculator, never arbitrary images."""
    if not isinstance(release, dict):
        raise ValueError("Calculator release must be a JSON object")
    image = release.get("image", release.get("image_ref", ""))
    commit = release.get("commit", "")
    if not isinstance(image, str) or not IMAGE.fullmatch(image):
        raise ValueError("Calculator release needs its approved full image digest")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Calculator release needs its full source commit")
    return {**release, "image": image, "commit": commit}


def mode(config):
    """Return an explicit distinction between preview and public hosting."""
    return "local-preview" if config["url"].startswith("http:") else "hosted"


def owner_id(config, release):
    """Bind a managed project to this origin, network and release selection."""
    public = {
        "url": config["url"],
        "network": config["network"],
        "image": release["image"],
    }
    return hashlib.sha256(json.dumps(public, sort_keys=True).encode()).hexdigest()[:20]


def compose_model(config, release):
    """Describe one hardened calculator without changing existing infrastructure."""
    config, release = validate_config(config), validate_release(release)
    labels = {LESSON_LABEL: LESSON, OWNER_LABEL: owner_id(config, release)}
    service = {
        "image": release["image"],
        "user": "10001:10001",
        "read_only": True,
        "cap_drop": ["ALL"],
        "security_opt": ["no-new-privileges:true"],
        "pids_limit": 128,
        "mem_limit": "256m",
        "cpus": 1,
        "tmpfs": ["/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777"],
        "environment": {"APP_ENV": "production"},
        "restart": "unless-stopped",
        "logging": {
            "driver": "json-file",
            "options": {"max-size": "10m", "max-file": "3"},
        },
        "labels": labels,
    }
    model = {"name": PROJECT, "services": {"calculator": service}}
    if mode(config) == "local-preview":
        port = urllib.parse.urlsplit(config["url"]).port
        service["ports"] = [f"127.0.0.1:{port}:8000"]
    else:
        hostname = urllib.parse.urlsplit(config["url"]).hostname
        router = ROUTER
        labels.update(
            {
                "traefik.enable": "true",
                "traefik.docker.network": config["network"],
                f"traefik.http.routers.{router}.rule": f"Host(`{hostname}`)",
                f"traefik.http.routers.{router}.entrypoints": "websecure",
                f"traefik.http.routers.{router}.service": router,
                f"traefik.http.services.{router}.loadbalancer.server.port": "8000",
            }
        )
        service["networks"] = ["hosting"]
        model["networks"] = {"hosting": {"external": True, "name": config["network"]}}
    return model


def _docker(config, *arguments, timeout=90):
    """Run Docker without a shell, returning output only to the local verifier."""
    command = ["docker", *arguments]
    if config["sudo"] and os.geteuid() != 0:
        command = ["sudo", "-n", *command]
    try:
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, timeout=timeout
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeError(
            "Docker operation failed. Check Docker access in your terminal; "
            "--sudo needs your normal administrator authentication. "
            "No password is read or stored by the studio."
        ) from error
    return result.stdout.strip()


def _snapshot(config):
    """Read selected identity, routing and port fields, never full inspection output."""
    identifiers = _docker(config, "ps", "-aq").split()
    records = []
    template = "\t".join(
        [
            "{{json .Id}}",
            "{{json .Name}}",
            "{{json .Image}}",
            "{{json .State.Status}}",
            '{{json (index .Config.Labels "com.docker.compose.project")}}',
            f'{{{{json (index .Config.Labels "{OWNER_LABEL}")}}}}',
            f'{{{{json (index .Config.Labels "{LESSON_LABEL}")}}}}',
            "{{json .HostConfig.PortBindings}}",
            '"{{range $name,$_ := .NetworkSettings.Networks}}{{$name}} {{end}}"',
        ]
    )
    for identifier in identifiers:
        fields = _docker(config, "inspect", "--format", template, identifier).split(
            "\t"
        )
        if len(fields) != 9:
            raise RuntimeError(
                "Docker selected-field inspection returned an unexpected shape"
            )
        values = [json.loads(value) for value in fields[:8]]
        record = dict(
            zip(
                (
                    "id",
                    "name",
                    "image_id",
                    "state",
                    "project",
                    "owner",
                    "lesson",
                    "ports",
                ),
                values,
            )
        )
        record["networks"] = json.loads(fields[8]).split()
        # Only router labels are selected; middleware/password labels are excluded.
        router_template = (
            "{{range $key,$value := .Config.Labels}}"
            '{{if eq (printf "%.21s" $key) "traefik.http.routers."}}'
            "{{json $key}} {{json $value}}{{println}}{{end}}{{end}}"
        )
        routes = _docker(config, "inspect", "--format", router_template, identifier)
        record["rules"] = []
        record["router_names"] = []
        for line in routes.splitlines():
            key, remainder = json.JSONDecoder().raw_decode(line)
            record["router_names"].append(
                key.removeprefix("traefik.http.routers.").split(".", 1)[0]
            )
            if key.endswith(".rule"):
                record["rules"].append(json.loads(line[remainder:].strip()))
        records.append(record)
    return records


def _image_info(config, reference):
    """Read public image identity and source labels without runtime environments."""
    template = "\t".join(
        [
            "{{json .Id}}",
            "{{json .RepoDigests}}",
            '{{json (index .Config.Labels "org.opencontainers.image.revision")}}',
            "{{json .Architecture}}",
            "{{json .Os}}",
        ]
    )
    values = [
        json.loads(value)
        for value in _docker(
            config, "image", "inspect", "--format", template, reference
        ).split("\t")
    ]
    if len(values) != 5:
        raise RuntimeError("Docker image identity returned an unexpected shape")
    return dict(
        zip(("image_id", "repo_digests", "commit", "architecture", "os"), values)
    )


def _assert_image(info, release):
    """Refuse a similarly named or stale calculator image."""
    digest = release["image"].split("@", 1)[1]
    if info["commit"] != release["commit"] or not any(
        reference.endswith("@" + digest) for reference in info.get("repo_digests") or []
    ):
        raise RuntimeError(
            "Running calculator image does not match the approved digest and commit"
        )


def _port_available(port):
    """Check local host-process collisions without interrupting the listener."""
    try:
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", port))
    except OSError as error:
        raise RuntimeError(
            f"Local preview port {port} is occupied; nothing was stopped"
        ) from error


def _preflight(config, release):
    """Reject unknown ownership and routing collisions before pulling or writing."""
    _docker(config, "version", "--format", "{{.Server.Version}}")
    _docker(config, "compose", "version", "--short")
    records = _snapshot(config)
    managed = [record for record in records if record["project"] == PROJECT]
    for record in managed:
        if record["owner"] != owner_id(config, release) or record["lesson"] != LESSON:
            raise RuntimeError(
                "Another configuration owns this studio project; nothing changed"
            )
    if len(managed) > 1:
        raise RuntimeError(
            "Unexpected services in the studio project; review them before continuing"
        )
    adopted = None
    if mode(config) == "hosted":
        adopted = _hosted_candidate(config, release, records, managed)
    else:
        port = urllib.parse.urlsplit(config["url"]).port
        for record in records:
            if record["state"] != "running" or record in managed:
                continue
            if any(
                binding.get("HostPort") == str(port)
                for bindings in (record["ports"] or {}).values()
                for binding in bindings or []
            ):
                raise RuntimeError(
                    f"Port {port} belongs to another container; nothing was stopped"
                )
        if not any(record["state"] == "running" for record in managed):
            _port_available(port)
    return records, managed, adopted


def _hosted_candidate(config, release, records, managed):
    """Check existing network and global router names before adding a route."""
    adopted = None
    network = _docker(
        config, "network", "inspect", "--format", "{{.Name}}", config["network"]
    )
    if network != config["network"]:
        raise RuntimeError(
            "The proxy network was not verified; no network will be created"
        )
    hostname = urllib.parse.urlsplit(config["url"]).hostname
    quoted = (f"`{hostname}`", f'"{hostname}"', f"'{hostname}'")
    matches = [
        record
        for record in records
        if record["state"] == "running"
        and any(any(host in rule for host in quoted) for rule in record["rules"])
    ]
    foreign = [record for record in matches if record not in managed]
    if len(foreign) > 1 or (foreign and managed):
        raise RuntimeError("Conflicting existing Host rules; nothing was changed")
    if foreign:
        _assert_image(_image_info(config, foreign[0]["image_id"]), release)
        if config["network"] not in foreign[0]["networks"]:
            raise RuntimeError("The existing calculator uses another proxy network")
        adopted = foreign[0]
    if not adopted and any(
        record not in managed
        and record["state"] == "running"
        and ROUTER in record.get("router_names", [])
        for record in records
    ):
        raise RuntimeError("The studio router name is already in use; nothing changed")
    return adopted


def doctor(config, release):
    """Report read-only prerequisite/ownership checks, not blanket server security."""
    config, release = validate_config(config), validate_release(release)
    records, managed, adopted = _preflight(config, release)
    action = (
        "adopt-existing" if adopted else "reuse-managed" if managed else "launch-new"
    )
    return {
        "status": "ready",
        "mode": mode(config),
        "target": config["host"],
        "url": config["url"],
        "action": action,
        "mutates": False,
        "container_count": len(records),
        "requires_sudo": config["sudo"],
        "limitations": [
            "Selected Docker/routing checks do not certify the whole server."
        ],
    }


def _http_json(origin, path, payload=None, *, timeout=8):
    """Check the requested origin with ordinary TLS and no successful redirects."""
    url = origin + path
    request = urllib.request.Request(
        url,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        if response.geturl() != url:
            raise RuntimeError(
                "A redirected response cannot verify the selected application origin"
            )
        raw = response.read(100_001)
        if len(raw) > 100_000:
            raise RuntimeError(
                "Application check returned an unexpectedly large response"
            )
        try:
            return response.status, json.loads(raw)
        except (ValueError, UnicodeError) as error:
            if response.status in {404, 502, 503}:
                return response.status, {}
            raise RuntimeError(
                "Application check did not return the expected JSON"
            ) from error


def _assert_health(status, health, release):
    """A reachable endpoint must still identify the selected production release."""
    if (
        status != 200
        or not isinstance(health, dict)
        or any(
            health.get(key) != value
            for key, value in {
                "status": "ok",
                "environment": "production",
                "commit": release["commit"],
            }.items()
        )
    ):
        raise RuntimeError("Health does not identify the expected production commit")


def _wait_new_route(config, release):
    """Allow a new proxy route/ACME certificate to become ready with trust intact."""
    deadline = time.monotonic() + TLS_READY_TIMEOUT
    reason = "the new HTTPS route is not ready"
    print(
        f"Waiting up to {TLS_READY_TIMEOUT}s for trusted HTTPS on the new route.",
        flush=True,
    )
    while remaining := deadline - time.monotonic():
        if remaining <= 0:
            break
        try:
            status, health = _http_json(
                config["url"], "/health", timeout=min(8, remaining)
            )
        except (
            urllib.error.URLError,
            ssl.SSLError,
            TimeoutError,
            ConnectionError,
        ) as error:
            cause = getattr(error, "reason", error)
            reason = (
                "certificate verification has not succeeded"
                if isinstance(cause, ssl.SSLCertVerificationError)
                else "the HTTPS connection has not succeeded"
            )
        else:
            if status == 200:
                _assert_health(status, health, release)
                return
            if status not in {404, 502, 503}:
                raise RuntimeError(f"New HTTPS route returned unexpected HTTP {status}")
            reason = f"the new route still returns HTTP {status}"
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(TLS_RETRY_INTERVAL, remaining))
    raise RuntimeError(
        f"Calculator started, but trusted HTTPS was not ready: {reason}. "
        "Check the hostname, DNS and existing proxy's certificate resolver, "
        "then run verify. Certificate checks were not bypassed."
    )


def _http_checks(config, release):
    """Exercise one valid calculation and two distinct invalid-input contracts."""
    status, health = _http_json(config["url"], "/health")
    _assert_health(status, health, release)
    positive_status, positive = _http_json(
        config["url"], "/api/calculate", {"a": 6, "b": 7, "operation": "multiply"}
    )
    zero_status, _ = _http_json(
        config["url"], "/api/calculate", {"a": 6, "b": 0, "operation": "divide"}
    )
    string_status, _ = _http_json(
        config["url"], "/api/calculate", {"a": "6", "b": 7, "operation": "multiply"}
    )
    if positive_status != 200 or positive.get("result") != 42:
        raise RuntimeError("The valid 6 × 7 calculation did not return 42")
    if zero_status != 400 or string_status != 422:
        raise RuntimeError(
            "The API did not reject division by zero and numeric strings as specified"
        )
    return health, {
        "health_identity": "passed",
        "positive_multiply": {"status": positive_status, "result": 42},
        "negative_division_by_zero": {"status": zero_status},
        "negative_numeric_string": {"status": string_status},
        "trusted_public_https": mode(config) == "hosted",
    }


def _preservation(before, after, selected):
    """Compare selected identities/states, without claiming a whole-host audit."""
    others = {
        record["id"]: (record["image_id"], record["state"], record["ports"])
        for record in before
        if record["id"] != selected["id"]
    }
    current = {record["id"]: record for record in after}
    unchanged = all(
        identifier in current
        and (
            current[identifier]["image_id"],
            current[identifier]["state"],
            current[identifier]["ports"],
        )
        == expected
        for identifier, expected in others.items()
    )
    if not unchanged:
        raise RuntimeError(
            "An unrelated container's selected identity/state changed during the check"
        )
    return {
        "checked_count": len(others),
        "unchanged": True,
        "scope": "container identity, state and published ports",
    }


def _report(config, release, selected, before, provenance):
    """Gather the selected running identity and actual request results."""
    if selected["state"] != "running":
        raise RuntimeError("The selected calculator is not running")
    image = _image_info(config, selected["image_id"])
    _assert_image(image, release)
    if provenance == "launched" and mode(config) == "hosted":
        _wait_new_route(config, release)
    health, checks = _http_checks(config, release)
    after = _snapshot(config)
    preservation = _preservation(before, after, selected)
    return {
        "status": "passed",
        "mode": mode(config),
        "target": config["host"],
        "url": config["url"],
        "project": PROJECT,
        "provenance": provenance,
        "new_launch": provenance == "launched",
        "expected": {"image": release["image"], "commit": release["commit"]},
        "actual": {
            **image,
            "environment": health["environment"],
            "container_id": selected["id"],
        },
        "checks": checks,
        "preservation": preservation,
        "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "limitations": [
            "This is a supplied image, not the learner's build or CI/CD pipeline.",
            "API checks do not prove a human review or whole-server security.",
            *(
                ["A local preview does not verify public DNS or HTTPS."]
                if mode(config) == "local-preview"
                else []
            ),
        ],
    }


def safe_directory(workdir):
    """Refuse symlinked runtime destinations before writing generated files."""
    path = Path(workdir).absolute()
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError("Studio runtime directory must not be a symbolic link")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def _save_report(workdir, report):
    """Write selected nonsecret evidence inside the private runtime directory."""
    path = safe_directory(workdir) / "report.json"
    if path.is_symlink():
        raise ValueError("Refusing a symbolic-link report destination")
    path.write_text(json.dumps(report, indent=2) + "\n")
    # Let the invoking operator retrieve evidence after an ordinary sudo run.
    if os.geteuid() == 0 and os.getenv("SUDO_UID") and os.getenv("SUDO_GID"):
        os.chown(path, int(os.environ["SUDO_UID"]), int(os.environ["SUDO_GID"]))
    path.chmod(0o600)


def launch(config, release, workdir):
    """Launch the calculator, or verify an existing route without replacing it."""
    config, release = validate_config(config), validate_release(release)
    before, managed, adopted = _preflight(config, release)
    if adopted:
        report = _report(config, release, adopted, before, "adopted-existing")
        _save_report(workdir, report)
        return report
    if managed and managed[0]["state"] == "running":
        report = _report(config, release, managed[0], before, "already-managed")
        _save_report(workdir, report)
        return report
    directory = safe_directory(workdir)
    manifest = directory / "compose.json"
    if manifest.is_symlink():
        raise ValueError("Refusing a symbolic-link Compose destination")
    manifest.write_text(json.dumps(compose_model(config, release), indent=2) + "\n")
    manifest.chmod(0o600)
    command = ("compose", "--project-name", PROJECT, "-f", str(manifest))
    print(
        "Pulling the calculator image; existing hosting services stay in place.",
        flush=True,
    )
    _docker(config, *command, "pull", timeout=300)
    _docker(config, *command, "up", "-d", "--wait", "--wait-timeout", "60", timeout=90)
    after = _snapshot(config)
    selected = [record for record in after if record["project"] == PROJECT]
    if len(selected) != 1 or selected[0]["owner"] != owner_id(config, release):
        raise RuntimeError("The new calculator's ownership could not be verified")
    report = _report(config, release, selected[0], before, "launched")
    _save_report(directory, report)
    return report


def verify(config, release, workdir=None):
    """Repeat identity and request checks without starting or replacing containers."""
    config, release = validate_config(config), validate_release(release)
    before, managed, adopted = _preflight(config, release)
    selected = adopted or (managed[0] if managed else None)
    if selected is None:
        raise RuntimeError(
            "No matching calculator is running; launch it before verification"
        )
    provenance = "adopted-existing" if adopted else "already-managed"
    report = _report(config, release, selected, before, provenance)
    if workdir is not None:
        _save_report(workdir, report)
    return report


def cleanup_preview(config, release, workdir):
    """Remove only this owned local fixture; never expose remote cleanup commands."""
    config, release = validate_config(config), validate_release(release)
    if config["host"] != "local" or mode(config) != "local-preview":
        raise ValueError("Automatic cleanup is restricted to an owned local preview")
    _, managed, _ = _preflight(config, release)
    if not managed:
        return
    manifest = Path(workdir).absolute() / "compose.json"
    if not manifest.is_file() or manifest.is_symlink():
        raise ValueError("The owned preview's saved manifest is required for cleanup")
    expected = compose_model(config, release)
    if json.loads(manifest.read_text()) != expected:
        raise ValueError("The saved preview manifest changed; review it before cleanup")
    _docker(config, "compose", "--project-name", PROJECT, "-f", str(manifest), "down")


def main():
    """Execute a reviewed bundle; never accept arbitrary shell/deployment commands."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("doctor", "launch", "verify"))
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--bundle-base64")
    parser.add_argument("--workdir", type=Path)
    args = parser.parse_args()
    try:
        if args.bundle_base64:
            bundle = json.loads(base64.b64decode(args.bundle_base64, validate=True))
        elif args.bundle:
            bundle = json.loads(args.bundle.read_text())
        else:
            raise ValueError("A reviewed studio bundle is required")
        config, release = validate_config(bundle["config"]), validate_release(
            bundle["release"]
        )
        workdir = args.workdir or Path.home() / ".is373-studio" / "calculator"
        if args.operation == "doctor":
            report = doctor(config, release)
        elif args.operation == "launch":
            report = launch(config, release, workdir)
        else:
            report = verify(config, release, workdir)
        print(json.dumps(report, indent=2), flush=True)
    except (ValueError, KeyError, RuntimeError, OSError) as error:
        parser.exit(1, f"Studio check stopped: {error}\n")


if __name__ == "__main__":
    main()
