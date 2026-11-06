import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import test from 'node:test';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const normalize = value => value.replace(/\r\n?/g, '\n');
const compiled = normalize(fs.readFileSync(path.join(root, 'app/static/render.js'), 'utf8'));

function fixture(t, templateEol = '\n', renderEol = '\n') {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'reseller frontend '));
  t.after(() => fs.rmSync(directory, {recursive: true, force: true}));
  for (const name of ['frontend/build.mjs', 'frontend/vendor/vue.js', 'frontend/app.html', 'app/static/render.js']) {
    const destination = path.join(directory, name);
    fs.mkdirSync(path.dirname(destination), {recursive: true});
    const eol = name === 'app/static/render.js' ? renderEol : templateEol;
    const source = normalize(fs.readFileSync(path.join(root, name), 'utf8'));
    fs.writeFileSync(destination, source.replace(/\n/g, eol), 'utf8');
  }
  return {
    template: path.join(directory, 'frontend/app.html'),
    target: path.join(directory, 'app/static/render.js'),
    run(...args) {
      const result = spawnSync(process.execPath, [path.join(directory, 'frontend/build.mjs'), ...args], {
        cwd: directory,
        encoding: 'utf8',
        timeout: 15000,
      });
      assert.ifError(result.error);
      assert.equal(result.signal, null);
      return result;
    },
  };
}

for (const [name, templateEol, renderEol] of [
  ['LF', '\n', '\n'],
  ['CRLF (Windows)', '\r\n', '\r\n'],
  ['CRLF template / LF artifact', '\r\n', '\n'],
  ['LF template / CRLF artifact', '\n', '\r\n'],
]) {
  test(`--check accepts ${name} without changing files`, t => {
    const files = fixture(t, templateEol, renderEol);
    const beforeTemplate = fs.readFileSync(files.template);
    const beforeTarget = fs.readFileSync(files.target);
    const result = files.run('--check');
    assert.equal(result.status, 0, result.stderr);
    assert.deepEqual(fs.readFileSync(files.template), beforeTemplate);
    assert.deepEqual(fs.readFileSync(files.target), beforeTarget);
  });
}

test('--check rejects a stale compiled artifact', t => {
  const files = fixture(t);
  fs.appendFileSync(files.target, '\n// Deliberate artifact mismatch.\n');
  const before = fs.readFileSync(files.target);
  const result = files.run('--check');
  assert.equal(result.status, 1, result.stderr);
  assert.match(result.stderr, /Execute node frontend\/build\.mjs/);
  assert.deepEqual(fs.readFileSync(files.target), before);
});

test('--check rejects an uncompiled template change', t => {
  const files = fixture(t, '\r\n', '\r\n');
  fs.appendFileSync(files.template, '\r\n<div>Regression check</div>\r\n');
  const result = files.run('--check');
  assert.equal(result.status, 1, result.stderr);
  assert.match(result.stderr, /Execute node frontend\/build\.mjs/);
});

test('--check rejects a missing artifact', t => {
  const files = fixture(t);
  fs.unlinkSync(files.target);
  const result = files.run('--check');
  assert.equal(result.status, 1, result.stderr);
  assert.match(result.stderr, /ENOENT/);
  assert.equal(fs.existsSync(files.target), false);
});

test('build emits the same LF artifact from a CRLF checkout', t => {
  const files = fixture(t, '\r\n', '\r\n');
  const result = files.run();
  assert.equal(result.status, 0, result.stderr);
  assert.equal(fs.readFileSync(files.target, 'utf8'), compiled);
  assert.equal(files.run('--check').status, 0);
});
