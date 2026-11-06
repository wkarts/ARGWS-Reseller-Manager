"""Test the frozen browser from an empty directory, independent of developer caches."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    args = parser.parse_args()
    executable = args.executable.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="reseller offline browser ") as directory:
        root = Path(directory)
        result_file = root / "result.json"
        environment = os.environ.copy()
        # Deliberately point to a nonexistent external cache. The frozen hook must
        # select the embedded copy instead, including on machines without Playwright.
        environment["PLAYWRIGHT_BROWSERS_PATH"] = str(root / "empty-browser-cache")
        environment["RESMAN_BROWSER_ENABLED"] = "0"  # old template must not break upgrades
        completed = subprocess.run([str(executable), "--browser-self-test", "--result", str(result_file)],
            cwd=root, env=environment, timeout=120, check=False)
        result = json.loads(result_file.read_text(encoding="utf-8")) if result_file.exists() else {}
        if completed.returncode or result.get("status") != "ok" or result.get("frozen") is not True:
            raise RuntimeError("Integrated browser self-test failed: " + json.dumps(result))
        assert result["engine"] == "chromium" and result["network"] == "offline"
        assert result["browser_channel"] == "chromium", "Não usar Headless Shell"
        print("BROWSER SMOKE PASSED: frozen executable, bundled Chromium, empty cache, offline render")


if __name__ == "__main__":
    main()
