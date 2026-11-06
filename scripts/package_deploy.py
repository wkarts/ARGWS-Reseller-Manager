"""Package only compose.yaml, safe defaults and instructions, never live .env/data."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
IMAGE = re.compile(r"ghcr\.io/[a-z0-9_.-]+/[a-z0-9_./-]+(?::[A-Za-z0-9_.-]+|@sha256:[a-f0-9]{64})")


def build_package(output: Path, image: str, browser: bool = False, source_sha: str = "unknown") -> Path:
    if not IMAGE.fullmatch(image):
        raise ValueError("Use uma imagem GHCR com tag/digest explícito, sem credenciais.")
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?", version):
        raise ValueError("VERSION inválido.")
    env = (ROOT / "deploy/.env.example").read_text(encoding="utf-8")
    env = re.sub(r"^RESMAN_IMAGE=.*$", "RESMAN_IMAGE=" + image, env, flags=re.MULTILINE)
    env = re.sub(r"^RESMAN_BROWSER_ENABLED=.*$", "RESMAN_BROWSER_ENABLED=1", env, flags=re.MULTILINE)
    files = {
        "compose.yaml": (ROOT / "deploy/compose.yaml").read_bytes(),
        ".env": env.encode("utf-8"),
        ".env.example": env.encode("utf-8"),
        "README.md": (ROOT / "deploy/README.md").read_bytes(),
        "deployment.json": (json.dumps({"version": version, "image": image,
            "browser": True, "compatibility_alias": browser, "source_sha": source_sha,
            "note": "A criação do pacote não comprova a publicação da imagem nem a homologação do fornecedor."},
            ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    }
    output.mkdir(parents=True, exist_ok=True)
    archive = output / (f"reseller-manager-{version}-deploy" + ("-browser" if browser else "") + ".zip")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, data in files.items():
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o600 if name == ".env" else 0o644) << 16
            bundle.writestr(info, data)
    archive.with_suffix(archive.suffix + ".sha256").write_text(
        hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n", encoding="ascii")
    return archive


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image")
    parser.add_argument("--browser", action="store_true")
    parser.add_argument("--source-sha", default=os.getenv("GITHUB_SHA", "unknown"))
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts")
    args = parser.parse_args()
    version = (ROOT / "VERSION").read_text().strip()
    repository = os.getenv("GITHUB_REPOSITORY", "wkarts/ARGWS-Reseller-Manager").lower()
    image = args.image or f"ghcr.io/{repository}:{version}" + ("-browser" if args.browser else "")
    try:
        print(build_package(args.output, image, args.browser, args.source_sha))
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
