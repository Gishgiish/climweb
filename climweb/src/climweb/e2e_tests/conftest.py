import os
import subprocess
import time
import urllib.request
import urllib.error
import pytest


BASE_URL = "http://127.0.0.1:8001"
MANAGE_PY = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "manage.py"
)


def _wait_for_server(url: str, timeout: int = 30) -> bool:
    """Poll *url* until it responds or *timeout* seconds elapse."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except (urllib.error.URLError, OSError):
            time.sleep(1)
    return False


@pytest.fixture(scope="session", autouse=True)
def django_server():
    """Start the Django development server for the duration of the test session.

    The server is launched on port 8001 to avoid conflicts with any existing
    development server running on the default port 8000.  The fixture waits up
    to 30 seconds for the server to become reachable before yielding control to
    the tests, and terminates the process when the session ends.

    Environment variables required (same as the dev environment):
      - DJANGO_SETTINGS_MODULE  (defaults to climweb.config.settings.dev)
    """
    env = os.environ.copy()
    env.setdefault("DJANGO_SETTINGS_MODULE", "climweb.config.settings.dev")

    proc = subprocess.Popen(
        ["python", MANAGE_PY, "runserver", "127.0.0.1:8001", "--noreload"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    if not _wait_for_server(BASE_URL):
        proc.terminate()
        proc.wait()
        raise RuntimeError(
            "Django development server did not start within 30 seconds. "
            "Check that all required environment variables are set and that "
            "the database migrations have been applied."
        )

    yield

    proc.terminate()
    proc.wait()
