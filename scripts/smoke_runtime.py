"""HTTP smoke against an actual process, also usable with the Windows frozen executable."""
from pathlib import Path
import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--executable');a=p.parse_args()
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix='reseller-smoke-') as directory:
        command=[a.executable,'--server'] if a.executable else [sys.executable,'-m','app.runtime']
        command+=['--host','127.0.0.1','--port',str(port),'--data',directory]
        process=subprocess.Popen(command,cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            deadline=time.monotonic()+40
            while True:
                try:
                    with opener.open(f'http://127.0.0.1:{port}/health',timeout=2) as r:health=json.load(r)
                    assert health['service']=='reseller-manager';break
                except (OSError,ValueError):
                    if process.poll() is not None:raise RuntimeError('Server exited before readiness')
                    if time.monotonic()>deadline:raise RuntimeError('Server readiness timeout')
                    time.sleep(.15)
            token=(Path(directory)/'admin.token').read_text().strip()
            req=urllib.request.Request(f'http://127.0.0.1:{port}/api/v1/me',headers={'Authorization':'Bearer '+token})
            with opener.open(req,timeout=3) as r:assert json.load(r)['scope']=='admin'
            for path in ['/','/docs','/openapi.json','/static/app.js','/static/render.js','/static/vendor/vue.js']:
                with opener.open(f'http://127.0.0.1:{port}'+path,timeout=3) as r:assert r.status==200,path
            print('SMOKE PASSED: process, health, admin auth, UI, local docs, OpenAPI, bundled assets')
        finally:
            process.terminate()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)

if __name__=='__main__':main()
