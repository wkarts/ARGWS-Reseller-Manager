"""Distribution-only regression tests; no upstream logins or Docker daemon required."""
from pathlib import Path
import hashlib
import json
import runpy
import subprocess
import sys
import zipfile

import pytest
import yaml
from scripts.distribution import metadata
from scripts.package_deploy import build_package

ROOT = Path(__file__).resolve().parents[1]
SHA = '1' * 40


def workflow(name):
    # GitHub workflow YAML follows 1.2; BaseLoader avoids YAML 1.1 `on` -> True.
    return yaml.load((ROOT / '.github/workflows' / name).read_text(), Loader=yaml.BaseLoader)


@pytest.mark.parametrize('target', ['runtime', 'browser'])
@pytest.mark.parametrize('ref,channel,tag', [
    ('refs/heads/main', 'stable', 'latest'),
    ('refs/heads/develop', 'develop', 'develop'),
    ('refs/tags/v0.1.0', 'stable', '0.1.0'),
])
def test_published_image_channels(target, ref, channel, tag):
    result = metadata('WkArts/ARGWS-Reseller-Manager', ref, SHA, '0.1.0', target)
    suffix = '-browser' if target == 'browser' else ''
    assert result['primary'] == 'ghcr.io/wkarts/argws-reseller-manager:' + tag + suffix
    assert result['publish_allowed'] and result['channel'] == channel
    assert result['tags'][-1].startswith('ghcr.io/wkarts/')
    assert any(':sha-' + SHA[:12] + suffix in t for t in result['tags'])


@pytest.mark.parametrize('ref', ['refs/pull/1/merge', 'refs/heads/feat/work', 'refs/heads/fix/ci'])
def test_pr_and_feature_branches_never_allowed_to_publish(ref):
    result = metadata('wkarts/test', ref, SHA, '0.1.0', 'runtime')
    assert not result['publish_allowed']
    assert result['tags'] == ['ghcr.io/wkarts/test:sha-' + SHA[:12]]


@pytest.mark.parametrize('ref', ['refs/tags/v0.2.0-dev.1', 'refs/heads/main', 'refs/heads/develop'])
def test_prerelease_never_moves_latest(ref):
    result = metadata('wkarts/test', ref, SHA, '0.2.0-dev.1', 'runtime')
    assert all(not tag.endswith(':latest') for tag in result['tags'])


def test_git_tag_must_match_version():
    with pytest.raises(ValueError, match='VERSION'):
        metadata('wkarts/test', 'refs/tags/v0.9.0', SHA, '0.1.0', 'runtime')


@pytest.mark.parametrize('args', [
    ('bad\nowner/test', 'refs/heads/main', SHA, '0.1.0', 'runtime'),
    ('wkarts/test', 'refs/heads/main', 'invalid', '0.1.0', 'runtime'),
    ('wkarts/test', 'refs/heads/main', SHA, '../foo', 'runtime'),
    ('wkarts/test', 'refs/heads/main', SHA, '0.1.0', 'invalid'),
])
def test_distribution_input_validation(args):
    with pytest.raises(ValueError):
        metadata(*args)


def test_require_publish_cli_rejects_pull_request(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/distribution.py'),
        '--repository', 'wkarts/test', '--ref', 'refs/pull/1/merge', '--sha', SHA,
        '--version', '0.1.0', '--require-publish', '--output', str(tmp_path / 'result.json')],
        capture_output=True, text=True)
    assert result.returncode != 0 and not (tmp_path / 'result.json').exists()


def test_dockge_compose_is_standalone_and_data_persistent():
    data = yaml.safe_load((ROOT / 'deploy/compose.yaml').read_text())
    services = data['services']
    assert set(services) == {'api', 'data-init'}
    for service in services.values():
        assert 'build' not in service and 'container_name' not in service
        assert service['image'] == '${RESMAN_IMAGE:-ghcr.io/wkarts/argws-reseller-manager:latest}'
        assert service['volumes'] == ['./data:/data']
        assert service['pull_policy'] == 'always'
    api = services['api']
    assert api['user'] == '10001:10001' and api['read_only']
    assert api['restart'] == 'unless-stopped' and api['init']
    assert api['environment']['RESMAN_HOST'] == '0.0.0.0'
    assert api['environment']['RESMAN_PORT'] == '48190'
    assert api['ports'] == ['${RESMAN_BIND:-127.0.0.1}:${RESMAN_PORT:-48190}:48190']
    assert api['depends_on']['data-init']['condition'] == 'service_completed_successfully'
    assert api['healthcheck']['test'][0] == 'CMD' and '/health' in api['healthcheck']['test'][-1]
    assert services['data-init']['network_mode'] == 'none'
    assert services['data-init']['restart'] == 'no'


def test_root_compose_retains_local_build():
    services = yaml.safe_load((ROOT / 'compose.yaml').read_text())['services']
    assert all(s['build']['context'] == '.' for s in services.values())
    assert services['api']['volumes'] == ['./data:/data']


@pytest.mark.parametrize('browser', [False, True])
def test_deploy_archive_has_ready_env_and_no_sources_or_secrets(tmp_path, monkeypatch, browser):
    # An unrelated live .env must never be read into the distribution package.
    (tmp_path / '.env').write_text('TOKEN=SECRET_NOT_FOR_DISTRIBUTION\n')
    monkeypatch.chdir(tmp_path)
    image = 'ghcr.io/wkarts/test:develop' + ('-browser' if browser else '')
    archive = build_package(tmp_path / 'output', image, browser, SHA)
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist()) == {'compose.yaml', '.env', '.env.example', 'README.md', 'deployment.json'}
        env = z.read('.env').decode()
        assert 'RESMAN_IMAGE=' + image in env
        assert 'RESMAN_BROWSER_ENABLED=' + str(int(browser)) in env
        assert z.read('.env.example') == z.read('.env')
        assert json.loads(z.read('deployment.json'))['source_sha'] == SHA
        assert all(b'SECRET_NOT_FOR_DISTRIBUTION' not in z.read(name) for name in z.namelist())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert archive.with_suffix('.zip.sha256').read_text().startswith(digest)
    previous = archive.read_bytes()
    build_package(tmp_path / 'output', image, browser, SHA)
    assert archive.read_bytes() == previous


@pytest.mark.parametrize('image', ['ghcr.io/wkarts/test:latest\nTOKEN=secret',
    'https://user:secret@ghcr.io/wkarts/test:latest', 'ghcr.io/wkarts/test', 'untrusted:test'])
def test_packager_rejects_unsafe_or_unversioned_image(tmp_path, image):
    with pytest.raises(ValueError):
        build_package(tmp_path, image)


def test_distribution_jobs_require_validation_and_pr_does_not_publish():
    ci = workflow('ci.yml')
    assert ci['on']['push']['branches'] == ['main', 'develop']
    assert ci['on']['push']['tags'] == ['v*']
    for name in ['container', 'windows']:
        assert ci['jobs'][name]['needs'] == 'tests'
        assert ci['jobs'][name]['uses'].endswith('/' + name + '.yml')
    assert ci['jobs']['container']['with']['publish'] == "${{ github.event_name == 'push' }}"
    assert ci['jobs']['container']['permissions']['packages'] == 'write'


def test_container_workflow_tests_exact_deploy_before_publication():
    wf = workflow('container.yml')
    assert set(wf['on']) == {'workflow_call', 'workflow_dispatch'}
    job = wf['jobs']['container']
    assert job['strategy']['matrix']['target'] == ['runtime', 'browser']
    steps = job['steps']
    smoke = next(i for i, s in enumerate(steps) if 'scripts/smoke_container.py' in s.get('run', ''))
    publish = next(i for i, s in enumerate(steps) if 'docker push' in s.get('run', ''))
    assert smoke < publish and steps[publish]['if'] == 'inputs.publish'
    assert 'docker tag "$TEST_IMAGE"' in steps[publish]['run']
    assert any('--require-publish' in s.get('run', '') for s in steps)


def test_windows_build_preserved_and_available_from_validation():
    wf = workflow('windows.yml')
    assert set(wf['on']) == {'workflow_call', 'workflow_dispatch'}
    assert wf['jobs']['windows']['runs-on'] == 'windows-latest'
    build = (ROOT / 'packaging/build_windows.py').read_text()
    assert 'PE x64' in build and 'scripts/smoke_runtime.py' in build
    assert '--onefile' in build and '--with-browser' in build
    assert 'packaging/browser_hook.py' in build
    assert (ROOT / 'scripts/start-windows.cmd').is_file()


def test_browser_bundle_defaults_do_not_override_user_environment(monkeypatch):
    monkeypatch.delenv('RESMAN_BROWSER_ENABLED', raising=False)
    monkeypatch.delenv('PLAYWRIGHT_BROWSERS_PATH', raising=False)
    runpy.run_path(str(ROOT / 'packaging/browser_hook.py'))
    import os
    assert os.environ['RESMAN_BROWSER_ENABLED'] == '1'
    assert os.environ['PLAYWRIGHT_BROWSERS_PATH'] == '0'
    monkeypatch.setenv('RESMAN_BROWSER_ENABLED', '0')
    monkeypatch.setenv('PLAYWRIGHT_BROWSERS_PATH', 'custom')
    runpy.run_path(str(ROOT / 'packaging/browser_hook.py'))
    assert os.environ['RESMAN_BROWSER_ENABLED'] == '0'
    assert os.environ['PLAYWRIGHT_BROWSERS_PATH'] == 'custom'
