"""Real supplied-image browser checks on an isolated local Docker fixture only."""

import os
import socket
import uuid

import pytest
from playwright.sync_api import expect

from studio_tools import remote, runtime

pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def calculator(tmp_path_factory):
    """Opt in to Docker; never read a remote target or touch the public class server."""
    if os.getenv("STUDIO_DOCKER_E2E") != "1":
        pytest.skip(
            "Run the prepared browser check to use its isolated local Docker fixture"
        )
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    config = {
        "host": "local",
        "url": f"http://127.0.0.1:{port}",
        "network": "web",
        "sudo": False,
    }
    release = runtime.release_selection()
    directory = tmp_path_factory.mktemp("calculator-browser").resolve()
    original_project = remote.PROJECT
    remote.PROJECT = "is373-studio-test-" + uuid.uuid4().hex[:12]
    try:
        report = remote.launch(config, release, directory)
        assert report["new_launch"] is True
        assert report["mode"] == "local-preview"
        assert report["checks"]["trusted_public_https"] is False
        yield config["url"]
    finally:
        remote.cleanup_preview(config, release, directory)
        remote.PROJECT = original_project


def test_positive_browser_and_api_results_agree(page, calculator):
    page.goto(calculator)
    expect(page.locator("#api-status")).to_have_text("API available")
    page.get_by_label("First number", exact=True).fill("6")
    page.get_by_label("Second number", exact=True).fill("7")
    page.get_by_label("Operation", exact=True).select_option("multiply")
    page.get_by_role("button", name="Calculate").click()
    expect(page.locator("#browser-result")).to_have_text("42")
    expect(page.locator("#api-result")).to_have_text("42")
    expect(page.locator("#comparison")).to_have_text("Results match")


def test_invalid_division_has_useful_error_without_false_match(page, calculator):
    page.goto(calculator)
    page.get_by_label("First number", exact=True).fill("6")
    page.get_by_label("Second number", exact=True).fill("0")
    page.get_by_label("Operation", exact=True).select_option("divide")
    page.get_by_role("button", name="Calculate").click()
    expect(page.locator("#error")).to_have_text("Cannot divide by zero.")
    expect(page.locator("#comparison")).not_to_have_text("Results match")
    expect(page.locator("#api-result")).to_have_text("—")
