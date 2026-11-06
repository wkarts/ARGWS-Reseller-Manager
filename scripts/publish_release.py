"""Publish validated, self-contained CI assets; never rebuild or overwrite a release."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile
from urllib.parse import quote
from urllib.request import Request, urlopen

from scripts.distribution import metadata, VERSION


def run(*command: str, allow_missing: bool = False) -> str | None:
    result = subprocess.run(command, text=True, capture_output=True, timeout=600)
    if result.returncode:
        if allow_missing and re.search(r"HTTP 404|manifest unknown|not found", result.stderr, re.I):
            return None
        # Tools receive credentials from their environment, never command arguments.
        raise RuntimeError(f"{command[0]} failed: {result.stderr.strip()}")
    return result.stdout


def checksum(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_assets(directory: Path, version: str, sha: str, repository: str) -> list[Path]:
    """Reject missing, mixed-SHA, incomplete-browser or corrupted distributions."""
    if not VERSION.fullmatch(version):
        raise ValueError("VERSION inválido")
    metadata(repository, "refs/heads/main", sha, version, "runtime")
    prefix = f"reseller-manager-{version}"
    assets: list[Path] = []
    for suffix in ("windows-x64", "deploy", "deploy-browser"):
        name = f"{prefix}-{suffix}.zip"
        matches = list(directory.rglob(name))
        if len(matches) != 1 or matches[0].is_symlink():
            raise ValueError(f"Artefato obrigatório ausente ou duplicado: {name}")
        archive = matches[0]
        sidecars = [p for p in (archive.with_suffix(".sha256"), archive.with_suffix(".zip.sha256")) if p.is_file()]
        if len(sidecars) != 1:
            raise ValueError(f"Checksum obrigatório: {name}")
        sidecar = sidecars[0]
        if sidecar.read_text(encoding="ascii").strip() != f"{checksum(archive)}  {name}":
            raise ValueError(f"Checksum inválido: {name}")
        with zipfile.ZipFile(archive) as bundle:
            manifest_name = f"{prefix}-windows-x64/manifest.json" if suffix == "windows-x64" else "deployment.json"
            manifest = json.loads(bundle.read(manifest_name))
            if manifest.get("version") != version or manifest.get("source_sha") != sha:
                raise ValueError(f"Versão/SHA de origem divergente: {name}")
            if suffix == "windows-x64":
                if manifest.get("browser_bundled") is not True or any(manifest.get(k) != "passed" for k in ("browser_smoke", "http_smoke")):
                    raise ValueError("Windows sem Chromium integrado e testado")
                files = bundle.namelist()
                if not any(n.endswith("/ResellerManager.exe") for n in files) or not any("/.local-browsers/" in n and n.endswith("chrome.exe") for n in files):
                    raise ValueError("Executáveis Windows/Chromium ausentes no ZIP")
            else:
                expected = f"ghcr.io/{repository.lower()}:sha-{sha[:12]}" + ("-browser" if suffix.endswith("-browser") else "")
                if manifest.get("browser") is not True or manifest.get("image") != expected:
                    raise ValueError(f"Deploy sem navegador ou sem imagem do SHA testado: {name}")
                if not {"compose.yaml", ".env", ".env.example", "README.md"}.issubset(bundle.namelist()):
                    raise ValueError("Deploy incompleto")
        assets.extend((archive, sidecar))
    return assets


def find_release(repository: str, tag: str) -> dict | None:
    # The by-tag endpoint is not reliable for unpublished drafts. Listing with
    # the write-scoped token includes drafts and supports interrupted uploads.
    pages = json.loads(run("gh", "api", "--paginate", "--slurp", f"repos/{repository}/releases?per_page=100"))
    matches = [item for page in pages for item in page if item["tag_name"] == tag]
    if len(matches) > 1:
        raise ValueError("Mais de um rascunho para a versão; reconcilie sem sobrescrever releases")
    return matches[0] if matches else None


def tag_sha(repository: str, tag: str) -> str | None:
    text = run("gh", "api", f"repos/{repository}/git/ref/tags/{tag}", allow_missing=True)
    if text is None:
        return None
    obj = json.loads(text)["object"]
    for _ in range(5):
        if obj["type"] == "commit":
            return obj["sha"]
        if obj["type"] != "tag":
            break
        obj = json.loads(run("gh", "api", f"repos/{repository}/git/tags/{obj['sha']}"))["object"]
    raise ValueError("Tag não aponta para um commit válido")


def image_digest(image: str, *, optional: bool = False) -> str | None:
    text = run("docker", "buildx", "imagetools", "inspect", image, "--format", "{{json .Manifest}}", allow_missing=optional)
    if text is None:
        return None
    digest = json.loads(text).get("digest", "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("Digest GHCR inválido")
    return digest


def promote_images(repository: str, version: str, sha: str) -> None:
    """Copy the exact tested digests to version tags, refusing conflicting tags."""
    image = "ghcr.io/" + repository.lower()
    pending = []
    for suffix in ("", "-browser"):
        source = f"{image}:sha-{sha[:12]}{suffix}"
        target = f"{image}:{version}{suffix}"
        digest = image_digest(source)
        existing = image_digest(target, optional=True)
        if existing is not None and existing != digest:
            raise ValueError(f"Tag GHCR existente aponta para outro digest: {target}. Incremente VERSION.")
        pending.append((target, digest, existing is None))
    for target, digest, missing in pending:
        if missing:
            run("docker", "buildx", "imagetools", "create", "--prefer-index=false", "--tag", target, f"{image}@{digest}")
        if image_digest(target) != digest:
            raise RuntimeError("Digest promovido diverge da imagem testada")


def upload_asset(repository: str, release_id: int, asset: Path) -> dict:
    """Envia o binário diretamente pelo ID imutável do rascunho, sem lookup por tag."""
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError("GH_TOKEN indisponível para upload da release")
    url = (f"https://uploads.github.com/repos/{repository}/releases/{release_id}/assets"
           f"?name={quote(asset.name, safe='')}")
    size = asset.stat().st_size
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/octet-stream",
        "Content-Length": str(size),
        "User-Agent": "Reseller-Manager-Release",
    }
    with asset.open("rb") as stream:
        request = Request(url, data=stream, headers=headers, method="POST")
        with urlopen(request, timeout=600) as response:
            if response.status != 201:
                raise RuntimeError("Upload do GitHub não retornou HTTP 201")
            uploaded = json.loads(response.read())
    if (uploaded.get("name") != asset.name or uploaded.get("state") != "uploaded"
            or uploaded.get("size") != size
            or uploaded.get("digest", "sha256:" + checksum(asset)) != "sha256:" + checksum(asset)):
        raise RuntimeError(f"Metadados do anexo divergentes: {asset.name}")
    return uploaded


def publish(repository: str, ref: str, sha: str, version: str, assets: list[Path]) -> None:
    if ref not in ("refs/heads/main", "refs/tags/v" + version):
        raise ValueError("Release permitida somente em main ou tag vVERSION, nunca em PR/develop")
    tag = "v" + version
    existing_sha = tag_sha(repository, tag)
    if existing_sha is not None and existing_sha != sha:
        raise ValueError("A versão já pertence a outro commit. Incremente VERSION; nenhuma tag será movida.")
    release = find_release(repository, tag)
    if release and not release["draft"]:
        if existing_sha != sha:
            raise ValueError("Release publicada sem tag correspondente")
        print(f"Release {tag} já publicada neste SHA; preservada sem alterações.")
        return
    if release and release.get("target_commitish") != sha and existing_sha != sha:
        raise ValueError("Rascunho de release pertence a outro commit")
    # Validate all existing image tags before touching published release assets.
    promote_images(repository, version, sha)
    if not release:
        notes = (f"# Reseller Manager {version}\n\n"
                 f"Origem validada: `{sha}`.\n\n"
                 "Windows x64 e Docker/Dockge incluem Playwright e Chromium. Não é necessário instalar Python, Node.js ou navegador na máquina de uso.\n\n"
                 "Baixe o ZIP Windows e extraia a pasta inteira; execute `ResellerManager.exe`. No Docker/Dockge, use o ZIP de deploy, que contém `compose.yaml` e `.env`. Os deploys referenciam a imagem do SHA testado.\n\n"
                 "A release só é publicada depois dos testes, builds nativos e abertura real do Chromium embarcado. Os arquivos SHA-256 acompanham cada ZIP.\n\n"
                 "Os contratos reais do kOfficePanel continuam sujeitos à homologação; esta release não comprova login ou renovação no fornecedor.\n")
        # A resposta da criação contém o ID definitivo do rascunho.
        # Não consultar imediatamente a listagem: drafts podem demorar a aparecer.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "release.json"
            payload = {"tag_name": tag, "name": f"Reseller Manager {version}",
                       "target_commitish": sha, "draft": True, "prerelease": "-" in version,
                       "body": notes}
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            release = json.loads(run("gh", "api", "--method", "POST",
                                     f"repos/{repository}/releases", "--input", str(path)))
        if (not isinstance(release, dict) or
                type(release.get("id")) is not int or release["id"] <= 0 or
                release.get("draft") is not True or
                release.get("tag_name") != tag or
                release.get("target_commitish") != sha):
            raise RuntimeError("GitHub retornou rascunho inválido; não publicar sem anexos")
    # Somente o ID do rascunho é usado nos uploads, inclusive imediatamente após
    # a criação, quando uma busca por tag pode retornar 404.
    current = json.loads(run("gh", "api", f"repos/{repository}/releases/{release['id']}"))
    if (current.get("id") != release["id"] or current.get("draft") is not True
            or current.get("tag_name") != tag or current.get("target_commitish") != sha):
        raise RuntimeError("Rascunho alterado durante a publicação; interrompendo")
    remote_assets = {item["name"]: item for item in current.get("assets", [])}
    for path in assets:
        previous = remote_assets.get(path.name)
        expected_digest = "sha256:" + checksum(path)
        if previous and previous.get("state") == "uploaded" and previous.get("size") == path.stat().st_size and previous.get("digest") == expected_digest:
            continue
        if previous:
            if type(previous.get("id")) is not int or previous["id"] <= 0:
                raise RuntimeError(f"ID inválido no anexo existente: {path.name}")
            run("gh", "api", "--method", "DELETE", f"repos/{repository}/releases/assets/{previous['id']}")
        upload_asset(repository, release["id"], path)
    current = json.loads(run("gh", "api", f"repos/{repository}/releases/{release['id']}"))
    if not current["draft"]:
        raise RuntimeError("A release mudou durante o upload; interrompendo")
    uploaded = {item["name"]: item for item in current["assets"]}
    for path in assets:
        item = uploaded.get(path.name, {})
        if item.get("state") != "uploaded" or item.get("size") != path.stat().st_size:
            raise RuntimeError(f"Upload incompleto: {path.name}")
        if item.get("digest") and item["digest"] != "sha256:" + checksum(path):
            raise RuntimeError(f"Checksum remoto divergente: {path.name}")
    run("gh", "api", "--method", "PATCH", f"repos/{repository}/releases/{release['id']}",
        "-F", "draft=false", "-f", "make_latest=" + ("false" if "-" in version else "true"))
    print(f"Release publicada: {tag}; {len(assets)} assets; SHA {sha}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"), required=not os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--ref", default=os.environ.get("GITHUB_REF"), required=not os.environ.get("GITHUB_REF"))
    parser.add_argument("--sha", default=os.environ.get("GITHUB_SHA"), required=not os.environ.get("GITHUB_SHA"))
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--version", default=Path("VERSION").read_text().strip())
    args = parser.parse_args()
    assets = validate_assets(args.artifacts, args.version, args.sha, args.repository)
    publish(args.repository, args.ref, args.sha, args.version, assets)


if __name__ == "__main__":
    main()
