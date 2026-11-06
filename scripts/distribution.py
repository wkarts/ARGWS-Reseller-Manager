"""Deterministic GHCR names/tags. No API calls or publication side effects."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?")


def metadata(repository: str, ref: str, sha: str, version: str, target: str) -> dict:
    if not REPOSITORY.fullmatch(repository):
        raise ValueError("Repositório inválido: use owner/name.")
    if not re.fullmatch(r"[0-9a-fA-F]{40}", sha):
        raise ValueError("Informe o SHA completo de origem.")
    if not VERSION.fullmatch(version):
        raise ValueError("VERSION deve ser SemVer sem prefixo v nem build metadata.")
    if target not in {"runtime", "browser"}:
        raise ValueError("Target inválido.")
    suffix = "-browser" if target == "browser" else ""
    image = "ghcr.io/" + repository.lower()
    immutable_tag = "sha-" + sha.lower()[:12] + suffix
    tags = [immutable_tag]
    channel = "preview"
    publish_allowed = False
    if ref.startswith("refs/tags/"):
        if ref != "refs/tags/v" + version:
            raise ValueError("A tag precisa corresponder exatamente a v + VERSION.")
        channel = "prerelease" if "-" in version else "stable"
        tags.insert(0, version + suffix)
        if channel == "stable":
            tags.append("latest" + suffix)
        publish_allowed = True
    elif ref == "refs/heads/main":
        # Never point stable/latest at a prerelease build.
        channel = "prerelease" if "-" in version else "stable"
        if channel == "stable":
            tags.insert(0, "latest" + suffix)
        publish_allowed = True
    elif ref == "refs/heads/develop":
        channel = "develop"
        tags.insert(0, "develop" + suffix)
        publish_allowed = True
    return {"image": image, "tags": [image + ":" + tag for tag in tags],
            "primary": image + ":" + tags[0], "channel": channel,
            "publish_allowed": publish_allowed, "target": target, "sha": sha.lower()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--target", choices=["runtime", "browser"], default="runtime")
    parser.add_argument("--require-publish", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = metadata(args.repository, args.ref, args.sha, args.version, args.target)
        if args.require_publish and not result["publish_allowed"]:
            raise ValueError("Publicação permitida apenas em main, develop e tags vVERSION.")
    except ValueError as exc:
        parser.error(str(exc))
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
