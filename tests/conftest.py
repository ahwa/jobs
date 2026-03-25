import pytest
import threading
import http.server
import socket
from functools import partial
from pathlib import Path

SITE_DIR = (Path(__file__).parent.parent / "site").resolve()


class _SilentHandler(http.server.SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler with request logging suppressed."""
    def log_message(self, format, *args):
        pass


@pytest.fixture(scope="session")
def http_server():
    """Serve site/ over localhost HTTP so fetch('data.json') works."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", 0))
        port = s.getsockname()[1]

    handler = partial(_SilentHandler, directory=str(SITE_DIR))
    server = http.server.HTTPServer(("localhost", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://localhost:{port}"
    server.shutdown()


@pytest.fixture
def app_page(page, http_server):
    """Load the app and wait for data.json to finish rendering."""
    page.goto(f"{http_server}/index.html")
    # statTotalJobs shows '—' until data loads; wait for a real value
    page.wait_for_function(
        "() => { const el = document.getElementById('statTotalJobs'); "
        "return el && el.textContent.trim() !== '\u2014'; }"
    )
    return page
