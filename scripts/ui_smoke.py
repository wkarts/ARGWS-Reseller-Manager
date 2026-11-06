"""Real Chromium + actual FastAPI process; remote panel is explicitly synthetic."""
from pathlib import Path
from datetime import datetime,timedelta
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tests.conftest import profile

def main():
    out=ROOT/'build/ui-smoke';out.mkdir(parents=True,exist_ok=True)
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix='reseller-ui-') as directory:
        process=subprocess.Popen([sys.executable,'-m','tests.ui_server','--data',directory,'--port',str(port)],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        base=f'http://127.0.0.1:{port}'
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            for _ in range(100):
                try:
                    with opener.open(base+'/health',timeout=.5) as r:assert r.status==200
                    break
                except OSError:time.sleep(.1)
            else:raise RuntimeError('Test server unavailable')
            with sync_playwright() as pw:
                executable=os.getenv('CHROMIUM_EXECUTABLE')
                if not executable and not Path(pw.chromium.executable_path).exists():executable=shutil.which('chromium')
                browser=pw.chromium.launch(headless=True,executable_path=executable,args=['--no-sandbox'])
                context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
                page=context.new_page();errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(base,wait_until='networkidle')
                expect(page.get_by_role('heading',name='Bem-vindo ao seu painel')).to_be_visible()
                page.screenshot(path=str(out/'01-login.png'),full_page=True)
                page.get_by_label('Token desta instalação').fill((Path(directory)/'admin.token').read_text().strip())
                page.get_by_role('button',name='Entrar no ambiente →').click()
                expect(page.get_by_role('heading',name='Visão geral',exact=True)).to_be_visible()
                page.locator('aside a[href="#connections"]').click()
                page.get_by_role('button',name='＋ Nova conexão').click()
                page.get_by_label('Nome',exact=True).fill('Revenda de homologação')
                page.get_by_label('URL base').fill('https://panel.example')
                page.get_by_label('Usuário',exact=True).fill('upstream-user')
                page.get_by_label('Senha',exact=True).fill('upstream-password')
                page.get_by_role('button',name='Salvar conexão',exact=True).click()
                expect(page.get_by_role('heading',name='Revenda de homologação')).to_be_visible()
                page.get_by_role('button',name='Inspecionar formulário').click()
                expect(page.get_by_role('heading',name='Formulário observado — somente leitura')).to_be_visible()
                page.locator('aside a[href="#contracts"]').click()
                page.get_by_label('Contrato JSON').fill(json.dumps(profile(),indent=2))
                page.get_by_role('button',name='Salvar perfil e invalidar sessão anterior').click()
                expect(page.get_by_role('status')).to_contain_text('Perfil atualizado')
                page.locator('aside a[href="#connections"]').click()
                page.get_by_role('button',name='Autenticar conexão').click()
                expect(page.get_by_role('status')).to_contain_text('Autenticada',timeout=10000)
                page.locator('aside a[href="#clients"]').click()
                page.get_by_role('button',name='Consultar painel',exact=True).click()
                expect(page.get_by_role('cell',name='cliente-1',exact=True)).to_be_visible()
                assert 'CUSTOMER_SECRET' not in page.content()
                page.screenshot(path=str(out/'02-clientes.png'),full_page=True)
                page.get_by_role('button',name='Renovar',exact=True).first.click()
                page.get_by_label('Parâmetros JSON',exact=True).fill(json.dumps({'client_id':'c1','plan_id':'p1'}))
                page.get_by_label('Confirmo esta operação e os possíveis custos/créditos no painel.').check()
                page.get_by_role('button',name='Enviar para fila').click()
                expect(page.get_by_text('Concluída',exact=True).first).to_be_visible(timeout=10000)
                page.screenshot(path=str(out/'03-operacao.png'),full_page=True)
                page.locator('aside a[href="#overview"]').click()
                page.screenshot(path=str(out/'04-visao-geral.png'),full_page=True)
                page.set_viewport_size({'width':390,'height':844})
                expect(page.get_by_role('button',name='Abrir menu')).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Mobile horizontal overflow'
                page.screenshot(path=str(out/'05-mobile.png'),full_page=True)
                docs=context.new_page();docs.on('pageerror',lambda e:errors.append(str(e)));docs.goto(base+'/docs',wait_until='networkidle')
                expect(docs.locator('.route').first).to_be_visible()
                assert docs.locator('.route').count()>30
                docs.screenshot(path=str(out/'06-api.png'),full_page=True)
                assert not errors,errors
                browser.close()
                (out/'result.json').write_text(json.dumps({'status':'passed','remote_panel':'synthetic','javascript_errors':errors,'checks':['login','connection creation','login form inspection','profile save','remote session auth','client listing','credential projection','renewal queue','websocket completion','responsive viewport','offline API docs']},indent=2),encoding='utf-8')
                print('UI SMOKE PASSED — Chromium, actual API, synthetic remote panel; zero JS errors')
        finally:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)

if __name__=='__main__':main()
