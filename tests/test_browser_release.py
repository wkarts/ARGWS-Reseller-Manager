"""Regression coverage for self-contained distributions and guarded release publication."""
from __future__ import annotations
import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest
import yaml

from app.browser_support import launch_browser
from app.errors import BridgeError
from app.settings import Settings
from scripts import publish_release as release
from tests.conftest import connection

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40
VERSION = "0.1.0"
REPO = "wkarts/ARGWS-Reseller-Manager"


@pytest.mark.parametrize("old_flag", [None, "0", "1", "false"])
def test_browser_included_without_legacy_opt_in(monkeypatch, old_flag):
    if old_flag is None:
        monkeypatch.delenv("RESMAN_BROWSER_ENABLED", raising=False)
    else:
        monkeypatch.setenv("RESMAN_BROWSER_ENABLED", old_flag)
    assert Settings().browser_enabled is True


def test_browser_connection_reaches_login_without_opt_in(env, monkeypatch):
    from app import login_support
    client, app, panel, token = env
    attempts = []
    async def capture(connector, current, profile):
        attempts.append(current["id"])
        assert not profile.login.success_selector
        raise BridgeError("synthetic_login_reached", "Login de teste alcançado", 409)
    monkeypatch.setattr(login_support, "capture_browser", capture)
    identifier = connection(client, mode="browser")
    result = client.post(f"/api/v1/connections/{identifier}/connect")
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "synthetic_login_reached"
    assert attempts == [identifier]
    assert not panel.requests


def test_missing_bundled_browser_is_not_a_dependency_install_instruction(tmp_path):
    fake = SimpleNamespace(chromium=SimpleNamespace(executable_path=str(tmp_path / "missing.exe")))
    with pytest.raises(BridgeError) as exc:
        asyncio.run(launch_browser(fake))
    assert exc.value.code == "browser_unavailable" and exc.value.status == 503
    assert "instale o Chromium" not in exc.value.message


def test_frozen_browser_must_be_inside_bundle(tmp_path, monkeypatch):
    import sys
    external = tmp_path / "external.exe"
    external.touch()
    fake = SimpleNamespace(chromium=SimpleNamespace(executable_path=str(external)))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "bundle"), raising=False)
    with pytest.raises(BridgeError, match="instalação externa"):
        asyncio.run(launch_browser(fake))


def test_browser_launch_error_is_not_reported_as_a_login_error(tmp_path):
    from playwright.async_api import Error
    executable = tmp_path / "chrome.exe"
    executable.touch()
    async def failed_launch(**kwargs):
        raise Error("synthetic missing library")
    fake = SimpleNamespace(chromium=SimpleNamespace(executable_path=str(executable), launch=failed_launch))
    with pytest.raises(BridgeError) as exc:
        asyncio.run(launch_browser(fake))
    assert exc.value.code == "browser_unavailable"


def test_all_container_targets_include_chromium():
    dockerfile = (ROOT / "Dockerfile").read_text()
    runtime, alias = dockerfile.split("FROM runtime AS browser")
    assert "playwright install --with-deps chromium" in runtime
    assert "PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers" in runtime
    assert "USER 10001:10001" in runtime
    assert not alias.strip()
    assert "playwright==1.57.0" in (ROOT / "requirements.txt").read_text()
    for file in ("compose.yaml", "deploy/compose.yaml"):
        env = yaml.safe_load((ROOT / file).read_text())["services"]["api"]["environment"]
        assert "RESMAN_BROWSER_ENABLED" not in env
    smoke = (ROOT / "scripts/smoke_container.py").read_text()
    assert '"app.browser_support"' in smoke
    assert 'if args.target == "browser":' not in smoke


def test_ci_downloads_chromium_without_apt_on_hosted_runners():
    # The native Docker build still installs Linux dependencies in its image;
    # CI host runners must not block on apt downloads of optional font packs.
    ci = yaml.load((ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    steps = ci["jobs"]["tests"]["steps"]
    install = next(s for s in steps if s.get("name") == "Prepare integrated browser for connection regression tests")
    assert install["run"] == "python -m playwright install chromium"
    assert int(install["timeout-minutes"]) >= 5
    pytest_step = next(s for s in steps if "python -m pytest -q" in s.get("run", ""))
    assert pytest_step["env"]["RESMAN_RUN_BROWSER_TESTS"] == "1"


def test_windows_always_bundles_and_tests_browser_before_archive():
    build = (ROOT / "packaging/build_windows.py").read_text()
    assert '"--exclude-module","playwright"' not in build
    assert '"--collect-all","playwright"' in build
    assert '"PLAYWRIGHT_BROWSERS_PATH"]="0"' in build
    assert build.index('scripts/smoke_browser.py') < build.index('shutil.make_archive')
    ps = (ROOT / "scripts/build-windows.ps1").read_text()
    assert "$BuildArgs += '--with-browser'" in ps
    assert 'if ($WithBrowser)' not in ps
    assert '--browser-self-test' in (ROOT / 'packaging/launcher.py').read_text()


def test_release_waits_for_both_native_builds_and_never_runs_on_pr():
    ci = yaml.load((ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader)
    job = ci['jobs']['release']
    assert set(job['needs']) == {'tests', 'container', 'windows'}
    assert "github.event_name == 'push'" in job['if']
    assert "github.ref == 'refs/heads/main'" in job['if']
    assert job['permissions'] == {'contents': 'write', 'packages': 'write'}
    assert any('scripts.publish_release' in step.get('run', '') for step in job['steps'])


def make_assets(directory: Path, *, browser=True, source_sha=SHA, smoke="passed"):
    directory.mkdir(parents=True, exist_ok=True)
    prefix = f"reseller-manager-{VERSION}"
    for suffix in ("windows-x64", "deploy", "deploy-browser"):
        name = f"{prefix}-{suffix}.zip"
        archive = directory / name
        with zipfile.ZipFile(archive, 'w') as z:
            if suffix == 'windows-x64':
                base = prefix + '-windows-x64/'
                info = {'version': VERSION, 'source_sha': source_sha, 'browser_bundled': browser,
                        'browser_smoke': smoke, 'http_smoke': 'passed'}
                z.writestr(base + 'manifest.json', json.dumps(info))
                z.writestr(base + 'ResellerManager.exe', b'MZ')
                z.writestr(base + '_internal/playwright/driver/package/.local-browsers/chromium-1/chrome-win64/chrome.exe', b'MZ')
            else:
                image = f'ghcr.io/{REPO.lower()}:sha-{source_sha[:12]}' + ('-browser' if suffix == 'deploy-browser' else '')
                z.writestr('deployment.json', json.dumps({'version': VERSION, 'source_sha': source_sha, 'browser': browser, 'image': image}))
                for entry in ('compose.yaml', '.env', '.env.example', 'README.md'):
                    z.writestr(entry, 'synthetic')
        archive.with_suffix('.zip.sha256').write_text(f'{release.checksum(archive)}  {name}\n')
    return release.validate_assets(directory, VERSION, SHA, REPO)


def test_release_accepts_only_complete_same_sha_artifacts(tmp_path):
    assets = make_assets(tmp_path)
    assert len(assets) == 6


@pytest.mark.parametrize('kwargs,match', [
    ({'browser': False}, 'Chromium'),
    ({'smoke': 'not-tested'}, 'testado'),
    ({'source_sha': 'b' * 40}, 'SHA'),
])
def test_release_rejects_incomplete_or_mixed_artifacts(tmp_path, kwargs, match):
    with pytest.raises(ValueError, match=match):
        make_assets(tmp_path, **kwargs)


def test_release_rejects_corrupted_artifacts(tmp_path):
    assets = make_assets(tmp_path)
    assets[0].write_bytes(assets[0].read_bytes() + b'changed')
    with pytest.raises(ValueError, match='Checksum'):
        release.validate_assets(tmp_path, VERSION, SHA, REPO)


def test_release_rejects_missing_windows_artifact(tmp_path):
    with pytest.raises(ValueError, match='obrigatório'):
        release.validate_assets(tmp_path, VERSION, SHA, REPO)


@pytest.mark.parametrize('ref', ['refs/pull/2/merge', 'refs/heads/develop', 'refs/heads/fix/test', 'refs/tags/v99.0.0'])
def test_release_ref_is_not_trusted(ref):
    with pytest.raises(ValueError, match='somente'):
        release.publish(REPO, ref, SHA, VERSION, [])


def test_release_never_moves_an_existing_version(monkeypatch):
    monkeypatch.setattr(release, 'tag_sha', lambda *args: 'b' * 40)
    with pytest.raises(ValueError, match='outro commit'):
        release.publish(REPO, 'refs/heads/main', SHA, VERSION, [])


def test_existing_public_release_is_immutable(monkeypatch):
    monkeypatch.setattr(release, 'tag_sha', lambda *args: SHA)
    calls = []
    def fake_run(*args, **kwargs):
        calls.append(args)
        return json.dumps([[{'id': 5, 'draft': False, 'tag_name': 'v' + VERSION}]])
    monkeypatch.setattr(release, 'run', fake_run)
    monkeypatch.setattr(release, 'promote_images', lambda *args: pytest.fail('must not change existing images'))
    release.publish(REPO, 'refs/heads/main', SHA, VERSION, [])
    assert len(calls) == 1


def test_release_publishes_only_after_all_assets_verified(tmp_path, monkeypatch):
    assets = make_assets(tmp_path)
    monkeypatch.setattr(release, 'tag_sha', lambda *args: None)
    promoted = []
    monkeypatch.setattr(release, 'promote_images', lambda *args: promoted.append(args))
    uploads = []
    monkeypatch.setattr(release, 'upload_asset', lambda repo, release_id, path: uploads.append((release_id, path.name)))
    calls = []
    draft = {'id': 5, 'draft': True, 'target_commitish': SHA, 'tag_name': 'v' + VERSION}

    def fake_run(*args, **kwargs):
        calls.append(args)
        if args[:2] == ('gh', 'api') and '/releases?per_page=' in args[-1]:
            # A listagem continua desatualizada logo após criar o rascunho.
            return '[[]]'
        if args[:4] == ('gh', 'api', '--method', 'POST'):
            assert args[4] == f'repos/{REPO}/releases'
            payload = json.loads(Path(args[6]).read_text(encoding='utf-8'))
            assert payload['tag_name'] == 'v' + VERSION
            assert payload['target_commitish'] == SHA and payload['draft'] is True
            return json.dumps(draft)
        if args[:2] == ('gh', 'api') and args[-1].endswith('/releases/5'):
            return json.dumps({**draft, 'assets': ([{'name': p.name, 'state': 'uploaded',
                'size': p.stat().st_size, 'digest': 'sha256:' + release.checksum(p)}
                for p in assets] if uploads else [])})
        return ''

    monkeypatch.setattr(release, 'run', fake_run)
    release.publish(REPO, 'refs/heads/main', SHA, VERSION, assets)
    assert promoted and calls[-1][:4] == ('gh', 'api', '--method', 'PATCH')
    assert 'draft=false' in calls[-1]
    assert sum(1 for c in calls if c[:4] == ('gh', 'api', '--method', 'POST')) == 1
    assert len(uploads) == len(assets) and all(ident == 5 for ident, _ in uploads)
    assert not any(c[1:3] == ('release', 'upload') for c in calls)


def test_invalid_draft_creation_response_never_uploads(tmp_path, monkeypatch):
    assets = make_assets(tmp_path)
    monkeypatch.setattr(release, 'tag_sha', lambda *args: None)
    monkeypatch.setattr(release, 'promote_images', lambda *args: None)
    calls = []

    def fake_run(*args, **kwargs):
        calls.append(args)
        if '/releases?per_page=' in args[-1]:
            return '[[]]'
        if args[:4] == ('gh', 'api', '--method', 'POST'):
            return json.dumps({'id': 9, 'draft': True, 'tag_name': 'v' + VERSION,
                               'target_commitish': 'b' * 40})
        raise AssertionError('Não deve fazer upload/publicação com metadados inválidos')

    monkeypatch.setattr(release, 'run', fake_run)
    with pytest.raises(RuntimeError, match='rascunho inválido'):
        release.publish(REPO, 'refs/heads/main', SHA, VERSION, assets)
    assert not any(c[1:3] == ('release', 'upload') for c in calls)


def test_incomplete_remote_upload_keeps_release_draft(tmp_path, monkeypatch):
    assets = make_assets(tmp_path)
    monkeypatch.setattr(release, 'tag_sha', lambda *args: SHA)
    monkeypatch.setattr(release, 'promote_images', lambda *args: None)
    monkeypatch.setattr(release, 'upload_asset', lambda *args: {})
    calls = []
    def fake_run(*args, **kwargs):
        calls.append(args)
        draft = {'id': 5, 'draft': True, 'target_commitish': SHA, 'tag_name': 'v' + VERSION, 'assets': []}
        return json.dumps([[draft]] if '/releases?per_page=' in args[-1] else draft)
    monkeypatch.setattr(release, 'run', fake_run)
    with pytest.raises(RuntimeError, match='Upload incompleto'):
        release.publish(REPO, 'refs/heads/main', SHA, VERSION, assets)
    assert not any('PATCH' in c for c in calls)


def test_image_promotion_refuses_conflicting_numeric_tag(monkeypatch):
    monkeypatch.setattr(release, 'image_digest', lambda image, **kwargs: 'sha256:' + ('a' if ':sha-' in image else 'b') * 64)
    monkeypatch.setattr(release, 'run', lambda *args, **kwargs: pytest.fail('must not overwrite an image'))
    with pytest.raises(ValueError, match='outro digest'):
        release.promote_images(REPO, VERSION, SHA)
