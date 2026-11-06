"""Smoke a built Linux image through the actual source-free Dockge deployment."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import urllib.request
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--target", choices=["runtime", "browser"], default="runtime")
    args = parser.parse_args()
    if os.name != "posix":
        parser.error("Execute o smoke do container em um host Linux com Docker Compose v2.")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    directory = Path(tempfile.mkdtemp(prefix="reseller-dockge-smoke-"))
    project = "reseller-smoke-" + uuid4().hex[:12]
    shutil.copyfile(ROOT / "deploy/compose.yaml", directory / "compose.yaml")
    # Read neither the user's working .env nor any production data.
    (directory / ".env").write_text("RESMAN_IMAGE=" + args.image + "\nRESMAN_BIND=127.0.0.1\nRESMAN_PORT=" + str(port) + "\n", encoding="utf-8")
    environment = os.environ.copy()
    for key in tuple(environment):
        if key.startswith(("RESMAN_", "COMPOSE_")):
            environment.pop(key)
    command = ["docker", "compose", "--project-directory", str(directory), "--env-file", str(directory / ".env"), "-p", project, "-f", str(directory / "compose.yaml")]
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def compose(*arguments: str, capture: bool = False) -> subprocess.CompletedProcess:
        return subprocess.run(command + list(arguments), check=True, env=environment,
                              capture_output=capture, text=True, timeout=180)

    def get(path: str, token: str = "") -> bytes:
        headers = {"Authorization": "Bearer " + token} if token else {}
        request = urllib.request.Request(f"http://127.0.0.1:{port}" + path, headers=headers)
        with opener.open(request, timeout=10) as response:
            assert response.status == 200, path
            return response.read()

    try:
        compose("config", "--quiet")
        compose("up", "-d", "--no-build", "--pull", "never", "--wait", "--wait-timeout", "120")
        health = json.loads(get("/health"))
        assert health["service"] == "reseller-manager"
        token = compose("exec", "-T", "api", "python", "-c", "from pathlib import Path; print(Path('/data/admin.token').read_text().strip())", capture=True).stdout.strip()
        assert token and json.loads(get("/api/v1/me", token))["scope"] == "admin"
        for path in ["/", "/docs", "/openapi.json", "/static/render.js", "/static/app.js"]:
            assert get(path), path
        uid = compose("exec", "-T", "api", "python", "-c", "import os; print(os.getuid())", capture=True).stdout.strip()
        assert uid == "10001", "API must remain non-root"
        # No network and no browser cache from the builder: use the packaged runtime.
        compose("exec", "-T", "api", "python", "-m", "app.browser_support", "--result", "/tmp/browser-smoke.json", "--diagnostic")
        compose("up", "-d", "--no-deps", "--no-build", "--pull", "never", "--force-recreate", "--wait", "--wait-timeout", "120", "api")
        token_after = compose("exec", "-T", "api", "python", "-c", "from pathlib import Path; print(Path('/data/admin.token').read_text().strip())", capture=True).stdout.strip()
        assert token_after == token, "Persistent token changed on recreation"
        assert json.loads(get("/api/v1/me", token))["scope"] == "admin"
        print("DOCKER SMOKE PASSED: standalone Compose, healthcheck, non-root, auth, assets, persistence" + ", integrated Chromium")
    finally:
        try:
            compose("logs", "--no-color", "--tail", "60")
        finally:
            try:
                compose("down", "--remove-orphans")
            finally:
                # Only our generated test folder is mounted; no production path is accepted.
                if (directory / "data").is_dir():
                    code = f"import os\nfor root, dirs, files in os.walk('/data',followlinks=False):\n os.chown(root,{os.getuid()},{os.getgid()})\n for name in files:\n  path=os.path.join(root,name)\n  if not os.path.islink(path): os.chown(path,{os.getuid()},{os.getgid()})"
                    subprocess.run(["docker", "run", "--rm", "--pull", "never", "--network", "none", "--user", "0:0", "--cap-drop", "ALL", "--cap-add", "CHOWN", "--cap-add", "DAC_OVERRIDE", "--mount", f"type=bind,source={directory / 'data'},target=/data", "--entrypoint", "python", args.image, "-c", code], check=True, timeout=60)
                shutil.rmtree(directory)


if __name__ == "__main__":
    main()
