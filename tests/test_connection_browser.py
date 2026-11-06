"""Real Chromium regression tests against local synthetic services, never a provider."""
import asyncio
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import threading
import time
from urllib.parse import parse_qs, urlsplit
import pytest
import uvicorn
from app.connector import Connector
from app.errors import BridgeError
from app.main import create_app
from app.models import ConnectionCreate
from app.settings import Settings
from app.store import Store

pytestmark = pytest.mark.skipif(os.environ.get('RESMAN_RUN_BROWSER_TESTS') != '1', reason='Real browser suite runs in native CI with bundled Chromium installed')
FORM='''<form method="POST" id="form-login"><input name="try_login" type="hidden" value="1"><input name="csrf_token" type="hidden" value="synthetic-csrf"><input name="username" aria-label="Usuário"><input name="password" aria-label="Senha" type="password"><button type="submit">Entrar</button></form>'''


@contextmanager
def provider():
    state={'posts':0}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def send(self,status,body,content_type='text/html',cookie=None):
            body=body.encode()
            self.send_response(status);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(body)))
            if cookie:self.send_header('Set-Cookie',cookie)
            self.end_headers();self.wfile.write(body)
        def do_GET(self):
            path=urlsplit(self.path).path
            if path=='/login/':return self.send(200,FORM,cookie='pre=visit; Path=/; HttpOnly')
            if 'session=accepted' not in self.headers.get('Cookie',''):
                return self.send(200,'<meta http-equiv="refresh" content="0;url=/login/">')
            if path=='/home/':return self.send(200,'<h1>Carteira sintética</h1><a href="/logout/">Sair</a>')
            if path=='/clients/api/':return self.send(200,json.dumps({'data':[['demo','client','SECRET_NOT_EXPORTED']], 'draw':1,'recordsTotal':1,'recordsFiltered':1}),'application/json')
            return self.send(404,'Not found')
        def do_POST(self):
            state['posts']+=1
            data=parse_qs(self.rfile.read(int(self.headers.get('Content-Length','0'))).decode())
            good=(data.get('username')==['demo'] and data.get('password')==['test-password'] and data.get('try_login')==['1'] and data.get('csrf_token')==['synthetic-csrf'] and 'pre=visit' in self.headers.get('Cookie',''))
            if good:return self.send(200,'<meta http-equiv="Refresh" content="0;url=/home/">',cookie='session=accepted; Path=/; HttpOnly')
            return self.send(401,'<div class="alert-danger" role="alert">Login inválido</div>'+FORM)
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield 'http://127.0.0.1:'+str(server.server_port),state
    finally:server.shutdown();server.server_close();thread.join(timeout=5)


def contract(probe=True):
    return {'name':'LOCAL SYNTHETIC ONLY','login':{},'endpoints':{'list_clients':{'path':'/clients/api/?get_clients','verified':True,'evidence':'Local synthetic integration fixture','fields':{'id':'0','username':'1'}}} if probe else {}}


def setup_connector(tmp_path,url,mode='browser',probe=True,password='test-password'):
    settings=Settings(data_dir=tmp_path,allowed_hosts=('127.0.0.1',),private_hosts=('127.0.0.1',),worker_enabled=False,test_network=True)
    store=Store(tmp_path)
    item=store.create_connection(ConnectionCreate(name='Fixture',base_url=url,auth_mode=mode,credentials={'username':'demo','password':password},profile=contract(probe)))
    return store,Connector(store,settings),item['id']


@pytest.mark.parametrize('mode',['form','browser'])
def test_real_login_without_success_selector_and_with_csrf(tmp_path,mode):
    with provider() as (url,state):
        store,connector,identifier=setup_connector(tmp_path,url,mode)
        result=asyncio.run(connector.connect(identifier))
        assert result['status']=='authenticated'
        assert state['posts']==1
        assert store.connection(identifier,True)['session']['cookies']
        listing=asyncio.run(connector.execute(identifier,'list_clients',{}))
        assert listing['data'][0]['id']=='demo'
        assert 'SECRET_NOT_EXPORTED' not in json.dumps(listing)


def test_real_browser_positive_page_without_validated_probe(tmp_path):
    with provider() as (url,state):
        store,connector,identifier=setup_connector(tmp_path,url,probe=False)
        result=asyncio.run(connector.connect(identifier))
        assert result['status']=='session_received'
        assert state['posts']==1
        assert store.connection(identifier)['status']=='session_received'


def test_real_browser_rejection_never_replays_login(tmp_path):
    with provider() as (url,state):
        store,connector,identifier=setup_connector(tmp_path,url,password='wrong-password')
        with pytest.raises(BridgeError) as result:
            asyncio.run(connector.connect(identifier))
        assert result.value.code=='login_requires_action'
        assert state['posts']==1
        assert store.connection(identifier,True)['session']=={}


def test_web_interface_edit_and_delete(tmp_path):
    from playwright.sync_api import sync_playwright
    settings=Settings(data_dir=tmp_path,allowed_hosts=('panel.example',),worker_enabled=False,test_network=True)
    app=create_app(settings)
    item=app.state.store.create_connection(ConnectionCreate(name='Conta local',base_url='https://panel.example',credentials={'username':'SECRET_USER','password':'SECRET_PASSWORD'}))
    token=(tmp_path/'admin.token').read_text().strip()
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,log_level='error',access_log=False))
    thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
    try:
        deadline=time.monotonic()+10
        while not server.started:
            assert time.monotonic()<deadline,'API did not start'
            time.sleep(.05)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            context=browser.new_context(viewport={'width':1280,'height':900})
            context.add_init_script('sessionStorage.setItem("reseller_token",'+json.dumps(token)+');')
            page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{port}/#connections')
            page.get_by_role('button',name='Editar',exact=True).click()
            editor=page.locator('#connection-editor')
            assert editor.get_by_label('Nova senha',exact=True).input_value()==''
            editor.get_by_label('Nome da conexão',exact=True).fill('Conta editada')
            editor.get_by_role('button',name='Salvar alterações',exact=True).click()
            page.get_by_role('heading',name='Conta editada',exact=True).wait_for()
            assert app.state.store.connection(item['id'],True)['credentials']['password']=='SECRET_PASSWORD'
            assert 'SECRET_PASSWORD' not in page.content() and 'SECRET_USER' not in page.content()
            Path('build').mkdir(exist_ok=True)
            page.screenshot(path='build/ui-connections-edit.png',full_page=True)
            page.get_by_role('button',name='Excluir conexão',exact=True).click()
            deletion=page.locator('#connection-delete')
            assert deletion.get_by_role('button',name='Excluir definitivamente').is_disabled()
            deletion.get_by_label('Digite o nome exato da conexão').fill('Conta editada')
            deletion.get_by_role('button',name='Excluir definitivamente').click()
            page.get_by_role('heading',name='Nenhuma conexão cadastrada',exact=True).wait_for()
            assert app.state.store.connections()==[]
            assert not errors,errors
            # Mobile controls must remain usable after the destructive confirmation.
            page.set_viewport_size({'width':390,'height':844})
            page.screenshot(path='build/ui-connections-empty-mobile.png',full_page=True)
            browser.close()
    finally:
        server.should_exit=True;thread.join(timeout=10);sock.close()
