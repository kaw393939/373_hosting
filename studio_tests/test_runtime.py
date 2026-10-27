"""Safety and evidence tests for the bounded calculator operation."""

import json
import io
import subprocess
import ssl
import urllib.error

import pytest

from studio_tools import remote, runtime

LOCAL = {
    "host": "local",
    "url": "http://127.0.0.1:18090",
    "network": "web",
    "sudo": False,
}
HOSTED = {
    **LOCAL,
    "host": "student@203.0.113.10",
    "url": "https://calculator.example.org",
}
RELEASE = runtime.release_selection()


def container(**overrides):
    """Create only the fields the runtime is allowed to inspect."""
    return {
        "id": "a" * 64,
        "name": "/existing",
        "image_id": "sha256:" + "b" * 64,
        "state": "running",
        "project": "existing",
        "owner": None,
        "lesson": None,
        "ports": {},
        "rules": [],
        "networks": ["web"],
        "router_names": [],
        **overrides,
    }


def image_info(**overrides):
    """Model a known image and let mismatch tests alter one boundary."""
    return {
        "image_id": "sha256:" + "b" * 64,
        "repo_digests": [RELEASE["image"]],
        "commit": RELEASE["commit"],
        "architecture": "amd64",
        "os": "linux",
        **overrides,
    }


def fake_http(_origin, path, payload=None):
    """Provide distinct status contracts rather than one universal successful reply."""
    if path == "/health":
        return 200, {
            "status": "ok",
            "environment": "production",
            "commit": RELEASE["commit"],
        }
    if payload["operation"] == "divide":
        return 400, {"detail": {"code": "division_by_zero"}}
    if isinstance(payload["a"], str):
        return 422, {"detail": []}
    return 200, {"result": 42}


def stub_docker(monkeypatch, records, *, network="web"):
    """Record Docker invocations while providing read-only prerequisite responses."""
    calls = []

    def docker(_config, *arguments, **_kwargs):
        calls.append(arguments)
        return network if arguments[:2] == ("network", "inspect") else "ready"

    monkeypatch.setattr(remote, "_docker", docker)
    monkeypatch.setattr(remote, "_snapshot", lambda _config: records)
    return calls


@pytest.mark.parametrize(
    "change",
    [
        {"host": "-oProxyCommand=touch /tmp/no"},
        {"host": "student@host;id"},
        {"host": "student@host $(id)"},
        {"network": "web;id"},
        {"network": "host"},
        {"sudo": "yes"},
        {"url": "https://name:password@example.org"},
        {"url": "https://example.org/path"},
        {"url": "https://example.org/?token=no"},
        {"url": "http://example.org:18090"},
        {"url": "http://127.0.0.1:22"},
        {"host": "student@203.0.113.10"},
    ],
)
def test_invalid_configuration_stops_before_any_command(monkeypatch, change):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Invalid configuration reached a process")

    monkeypatch.setattr(subprocess, "run", forbidden)
    with pytest.raises(ValueError):
        runtime.plan({**LOCAL, **change})


def test_plan_is_read_only_and_local_preview_has_no_public_route(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Plan performed a command")

    monkeypatch.setattr(subprocess, "run", forbidden)
    result = runtime.plan(LOCAL)
    service = result["compose"]["services"]["calculator"]
    assert result["mutates"] is False
    assert result["mode"] == "local-preview"
    assert service["ports"] == ["127.0.0.1:18090:8000"]
    assert "traefik.enable" not in service["labels"]
    assert "volumes" not in service
    assert "networks" not in result["compose"]


def test_hosted_plan_uses_one_existing_network_without_second_proxy():
    result = runtime.plan(HOSTED)
    assert set(result["compose"]["services"]) == {"calculator"}
    service = result["compose"]["services"]["calculator"]
    assert "ports" not in service
    assert service["read_only"] and service["cap_drop"] == ["ALL"]
    assert service["user"] == "10001:10001"
    assert service["security_opt"] == ["no-new-privileges:true"]
    assert result["compose"]["networks"]["hosting"] == {"external": True, "name": "web"}
    assert not any(key.endswith(".tls") for key in service["labels"])


def test_unknown_studio_project_is_not_replaced(monkeypatch, tmp_path):
    calls = stub_docker(
        monkeypatch, [container(project=remote.PROJECT, owner="someone-else")]
    )
    with pytest.raises(RuntimeError, match="Another configuration"):
        remote.launch(LOCAL, RELEASE, tmp_path)
    assert not any("pull" in call or "up" in call or "down" in call for call in calls)
    assert not list(tmp_path.iterdir())


def test_missing_proxy_network_stops_before_writes(monkeypatch, tmp_path):
    calls = stub_docker(monkeypatch, [], network="")
    with pytest.raises(RuntimeError, match="network was not verified"):
        remote.launch(HOSTED, RELEASE, tmp_path)
    assert not any("pull" in call or "up" in call for call in calls)
    assert not list(tmp_path.iterdir())


def test_foreign_listener_is_never_stopped(monkeypatch):
    occupied = container(
        ports={"8000/tcp": [{"HostIp": "0.0.0.0", "HostPort": "18090"}]}
    )
    calls = stub_docker(monkeypatch, [occupied])
    with pytest.raises(RuntimeError, match="another container"):
        remote.doctor(LOCAL, RELEASE)
    assert not any("stop" in call or "down" in call for call in calls)


def test_existing_wrong_image_route_is_not_replaced(monkeypatch, tmp_path):
    existing = container(rules=["Host(`calculator.example.org`)"])
    calls = stub_docker(monkeypatch, [existing])
    monkeypatch.setattr(remote, "_image_info", lambda *_: image_info(commit="0" * 40))
    with pytest.raises(RuntimeError, match="approved digest and commit"):
        remote.launch(HOSTED, RELEASE, tmp_path)
    assert not any("pull" in call or "up" in call for call in calls)


def test_existing_calculator_cannot_be_adopted_with_wrong_network(monkeypatch):
    existing = container(rules=["Host(`calculator.example.org`)"], networks=["another"])
    stub_docker(monkeypatch, [existing])
    monkeypatch.setattr(remote, "_image_info", lambda *_: image_info())
    with pytest.raises(RuntimeError, match="another proxy network"):
        remote.doctor(HOSTED, RELEASE)


def test_existing_router_name_cannot_be_overwritten_for_another_host(monkeypatch):
    existing = container(
        router_names=[remote.ROUTER], rules=["Host(`other.example.org`)"]
    )
    calls = stub_docker(monkeypatch, [existing])
    with pytest.raises(RuntimeError, match="router name is already in use"):
        remote.doctor(HOSTED, RELEASE)
    assert not any("up" in call for call in calls)


def test_class_ssh_alias_is_accepted_without_allowing_options():
    assert (
        remote.validate_config({**HOSTED, "host": "my-class-server"})["host"]
        == "my-class-server"
    )


def test_exact_existing_calculator_is_adopted_without_deployment(monkeypatch, tmp_path):
    existing = container(rules=["Host(`calculator.example.org`)"])
    calls = stub_docker(monkeypatch, [existing])
    monkeypatch.setattr(remote, "_image_info", lambda *_: image_info())
    monkeypatch.setattr(remote, "_http_json", fake_http)
    report = remote.launch(HOSTED, RELEASE, tmp_path.resolve())
    assert report["provenance"] == "adopted-existing"
    assert report["new_launch"] is False
    assert report["checks"]["negative_division_by_zero"]["status"] == 400
    assert report["checks"]["negative_numeric_string"]["status"] == 422
    assert not any("pull" in call or "up" in call for call in calls)
    assert (tmp_path / "report.json").stat().st_mode & 0o777 == 0o600


def test_stale_public_health_cannot_pass_image_check_alone(monkeypatch):
    def stale(origin, path, payload=None):
        status, body = fake_http(origin, path, payload)
        return status, {**body, "commit": "0" * 40} if path == "/health" else body

    monkeypatch.setattr(remote, "_http_json", stale)
    with pytest.raises(RuntimeError, match="Health does not identify"):
        remote._http_checks(HOSTED, RELEASE)


def test_invalid_input_acceptance_fails_even_when_valid_case_passes(monkeypatch):
    def accepts_everything(origin, path, payload=None):
        status, body = fake_http(origin, path, payload)
        return (status, body) if path == "/health" else (200, {"result": 42})

    monkeypatch.setattr(remote, "_http_json", accepts_everything)
    with pytest.raises(RuntimeError, match="did not reject"):
        remote._http_checks(HOSTED, RELEASE)


def test_preservation_detects_changed_unrelated_image():
    unrelated = container(id="c" * 64)
    selected = container()
    after = [{**unrelated, "image_id": "different"}, selected]
    with pytest.raises(RuntimeError, match="unrelated container"):
        remote._preservation([unrelated, selected], after, selected)


def test_symlinked_runtime_destination_is_rejected(tmp_path):
    target = tmp_path / "private"
    target.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(target)
    with pytest.raises(ValueError, match="symbolic link"):
        remote.safe_directory(alias)


def test_interactive_doctor_uses_normal_sudo_without_installing_helper(monkeypatch):
    calls = []
    report = {"status": "ready", "mode": "hosted", "target": HOSTED["host"]}

    def ssh(config, command, **kwargs):
        calls.append((config, command, kwargs))
        return subprocess.CompletedProcess(
            [], 0, "[sudo] password: \n" + json.dumps(report), ""
        )

    monkeypatch.setattr(runtime, "_ssh", ssh)
    assert runtime.doctor({**HOSTED, "sudo": True}) == report
    assert calls[0][1].startswith("sudo python3 -c ")
    assert calls[0][2] == {"interactive": True}
    assert "StrictHostKeyChecking=no" not in calls[0][1]


def test_bad_release_cannot_select_arbitrary_container():
    with pytest.raises(ValueError, match="approved full image digest"):
        remote.validate_release({**RELEASE, "image": "ubuntu:latest"})


def test_sudo_report_is_owned_by_invoking_operator(monkeypatch, tmp_path):
    ownership = []
    monkeypatch.setattr(remote.os, "geteuid", lambda: 0)
    monkeypatch.setenv("SUDO_UID", "1234")
    monkeypatch.setenv("SUDO_GID", "1235")
    monkeypatch.setattr(
        remote.os,
        "chown",
        lambda path, uid, gid: ownership.append((path.name, uid, gid)),
    )
    remote._save_report(tmp_path.resolve(), {"status": "passed"})
    assert ownership == [("report.json", 1234, 1235)]
    assert (tmp_path / "report.json").stat().st_mode & 0o777 == 0o600


def test_interactive_remote_tls_failure_is_not_reported_as_ssh_access(monkeypatch):
    class Process:
        stdout = io.StringIO(
            "[sudo] password: \n"
            "Studio check stopped: HTTPS certificate verification failed\n"
        )

        def __enter__(self):
            return self

        def __exit__(self, *_arguments):
            return False

        def wait(self):
            return 1

    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: Process())
    with pytest.raises(
        RuntimeError, match="Remote check stopped: HTTPS certificate"
    ) as caught:
        runtime._ssh(HOSTED, "reviewed-helper", interactive=True)
    assert "SSH connection failed" not in str(caught.value)


def test_remote_transport_failure_does_not_echo_unselected_stderr(monkeypatch):
    def failed(*_args, **_kwargs):
        raise subprocess.CalledProcessError(
            255, [], stderr="unselected transport output"
        )

    monkeypatch.setattr(subprocess, "run", failed)
    with pytest.raises(RuntimeError, match="SSH connection failed") as caught:
        runtime._ssh(HOSTED, "reviewed-helper")
    assert "unselected transport output" not in str(caught.value)


def test_new_route_retries_certificate_and_proxy_readiness(monkeypatch):
    clock = [0.0]
    calls = []
    attempts = iter(["certificate", "proxy", "ready"])
    monkeypatch.setattr(remote.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        remote.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds)
    )

    def waiting(origin, path, **kwargs):
        calls.append((origin, path, kwargs))
        attempt = next(attempts)
        if attempt == "certificate":
            raise urllib.error.URLError(
                ssl.SSLCertVerificationError("certificate pending")
            )
        if attempt == "proxy":
            return 503, {}
        return fake_http(origin, path)

    monkeypatch.setattr(remote, "_http_json", waiting)
    remote._wait_new_route(HOSTED, RELEASE)
    assert len(calls) == 3
    assert clock[0] == 4
    assert all(call[1] == "/health" for call in calls)


def test_new_route_wait_is_bounded_and_never_accepts_untrusted_tls(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(remote, "TLS_READY_TIMEOUT", 5)
    monkeypatch.setattr(remote.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        remote.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds)
    )

    def untrusted(*_args, **_kwargs):
        raise urllib.error.URLError(ssl.SSLCertVerificationError("self-signed"))

    monkeypatch.setattr(remote, "_http_json", untrusted)
    with pytest.raises(RuntimeError, match="Certificate checks were not bypassed"):
        remote._wait_new_route(HOSTED, RELEASE)
    assert clock[0] == 5


def test_new_route_wrong_commit_is_not_retried(monkeypatch):
    calls = []

    def stale(*_args, **_kwargs):
        calls.append(True)
        return 200, {"status": "ok", "environment": "production", "commit": "0" * 40}

    monkeypatch.setattr(remote, "_http_json", stale)
    with pytest.raises(RuntimeError, match="expected production commit"):
        remote._wait_new_route(HOSTED, RELEASE)
    assert len(calls) == 1


def test_verify_existing_route_does_not_wait_or_bypass_certificate_failure(monkeypatch):
    existing = container(rules=["Host(`calculator.example.org`)"])
    stub_docker(monkeypatch, [existing])
    monkeypatch.setattr(remote, "_image_info", lambda *_: image_info())

    def forbidden(*_args, **_kwargs):
        raise AssertionError(
            "Existing-route verification must not invoke launch readiness"
        )

    def untrusted(*_args, **_kwargs):
        raise urllib.error.URLError(ssl.SSLCertVerificationError("self-signed"))

    monkeypatch.setattr(remote, "_wait_new_route", forbidden)
    monkeypatch.setattr(remote, "_http_json", untrusted)
    with pytest.raises(urllib.error.URLError):
        remote.verify(HOSTED, RELEASE)
