"""Offline visual regression of real Vue assets; no browser navigation or network.

All data and browser transports below are synthetic. This is NOT a live API,
WebSocket, upstream authentication or kOfficePanel integration test.
"""
from pathlib import Path
import json
import os
import shutil
import sys
import tempfile
from playwright.sync_api import sync_playwright, expect
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.main import create_app
from app.settings import Settings
from tests.conftest import profile


def main():
    out = ROOT / 'build/ui-offline'
    out.mkdir(parents=True, exist_ok=True)
    fixture = {
        'connection': {'id': 'demo-connection', 'name': 'Revenda de homologação', 'base_url': 'https://panel.example', 'auth_mode': 'form', 'status': 'authenticated', 'revision': 2, 'profile': profile()},
        'clients': [
            {'id': 'c1', 'username': 'cliente-1', 'expires_at': '2030-12-31', 'plan': 'p1', 'screens': 2, 'technology': 'P2P'},
            {'id': 'c2', 'username': 'cliente-2', 'expires_at': '2030-12-31', 'plan': 'p2', 'screens': 1, 'technology': 'IPTV'},
        ],
    }
    bootstrap = r'''
window.__fixture = FIXTURE;
window.__offline_calls = [];
Object.defineProperty(window, 'sessionStorage', {value: {
  values:{}, getItem(k){return this.values[k]??null;}, setItem(k,v){this.values[k]=String(v);}, removeItem(k){delete this.values[k];}
}});
window.__operations = [];
window.WebSocket = class {
  constructor(){setTimeout(()=>this.onopen?.(),5);}
  send(){setTimeout(()=>this.onmessage?.({data:JSON.stringify({type:'authenticated'})}),5);}
  close(){}
};
window.fetch = async function(path, options={}){
  window.__offline_calls.push({path,method:options.method||'GET'});
  const f=window.__fixture, data=JSON.parse(options.body||'{}');
  let result;
  if(path==='/api/v1/me') result={name:'Administrador · dados simulados',scope:'admin',connection_ids:null};
  else if(path==='/api/v1/connections') result=[f.connection];
  else if(path==='/api/v1/connections/demo-connection') result=f.connection;
  else if(path.endsWith('/capabilities')) result={actions:Object.keys(f.connection.profile.endpoints).map(name=>({name,enabled:true}))};
  else if(path==='/api/v1/operations') result=window.__operations;
  else if(path==='/api/v1/schedules') result=[];
  else if(path==='/api/v1/tokens') result=[{id:'demo-token',name:'Token sintético',scope:'admin',connection_ids:null,revoked:false}];
  else if(path==='/api/v1/webhooks') result=[];
  else if(path.includes('/clients?')) result={data:f.clients,records_total:2,records_filtered:2,source:'upstream',mapping_required:false};
  else if(path.includes('/operations/renew_client')) {
    result={id:'demo-operation',action:'renew_client',connection_id:f.connection.id,resource:'client:c1',status:'succeeded',created_at:'2030-11-06T03:00:00+00:00',updated_at:'2030-11-06T03:00:00+00:00'};
    window.__operations=[result];
  }
  else throw Error('Unhandled offline fixture: '+path);
  return {ok:true,status:200,json:async()=>structuredClone(result)};
};
'''.replace('FIXTURE', json.dumps(fixture, ensure_ascii=False))
    with sync_playwright() as pw:
        executable = os.getenv('CHROMIUM_EXECUTABLE')
        if not executable and not Path(pw.chromium.executable_path).exists(): executable=shutil.which('chromium')
        browser = pw.chromium.launch(headless=True, executable_path=executable, args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        errors=[];requests=[]
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('request', lambda r: requests.append(r.url))
        page.set_content('<!doctype html><html lang="pt-BR"><head><meta charset="UTF-8"></head><body><div id="app"></div></body></html>')
        for name in ('template.css','app.css'):page.add_style_tag(content=(ROOT/'app/static'/name).read_text())
        page.add_script_tag(content=bootstrap)
        for name in ('vendor/vue.js','render.js','app.js'):
            text=(ROOT/'app/static'/name).read_text()
            if name=='app.js':text=text.replace('Vue.createApp({','window.__test_vm=Vue.createApp({',1)
            page.add_script_tag(content=text)
        expect(page.get_by_role('heading', name='Bem-vindo ao seu painel')).to_be_visible()
        page.screenshot(path=str(out/'01-login.png'),full_page=True)
        page.get_by_label('Token desta instalação').fill('OFFLINE_SYNTHETIC_TOKEN_NOT_A_REAL_CREDENTIAL')
        page.get_by_role('button',name='Entrar no ambiente →',exact=True).click()
        expect(page.get_by_role('heading', name='Visão geral',exact=True)).to_be_visible()
        page.evaluate("window.__test_vm.events=[{seq:1,type:'operation.succeeded',created_at:'2030-11-06T03:00:00+00:00'},{seq:2,type:'connection.authenticated',created_at:'2030-11-06T02:59:00+00:00'}]")
        page.screenshot(path=str(out/'02-visao-geral.png'),full_page=True)
        page.locator('aside a[href="#clients"]').click()
        page.get_by_role('button',name='Consultar painel',exact=True).click()
        expect(page.get_by_role('cell',name='cliente-1',exact=True)).to_be_visible()
        page.screenshot(path=str(out/'03-clientes.png'),full_page=True)
        page.get_by_role('button',name='Renovar',exact=True).first.click()
        page.get_by_label('Parâmetros JSON',exact=True).fill(json.dumps({'client_id':'c1','plan_id':'p1'}))
        page.get_by_label('Confirmo esta operação e os possíveis custos/créditos no painel.').check()
        page.get_by_role('button',name='Enviar para fila',exact=True).click()
        expect(page.get_by_text('Concluída',exact=True).first).to_be_visible()
        page.screenshot(path=str(out/'04-operacoes.png'),full_page=True)
        page.locator('aside a[href="#connections"]').click()
        page.get_by_role('button',name='＋ Nova conexão',exact=True).click()
        expect(page.get_by_label('URL base')).to_be_visible()
        page.screenshot(path=str(out/'05-conexoes.png'),full_page=True)
        page.locator('aside a[href="#contracts"]').click()
        expect(page.get_by_label('Contrato JSON')).to_be_visible()
        page.screenshot(path=str(out/'06-contratos.png'),full_page=True)
        page.locator('aside a[href="#overview"]').click()
        page.set_viewport_size({'width':390,'height':844})
        expect(page.get_by_role('button',name='Abrir menu')).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile horizontal overflow'
        assert page.locator('aside.sidebar').evaluate('(el)=>el.getBoundingClientRect().right<=0'), 'Sidebar must be fully hidden on mobile'
        page.screenshot(path=str(out/'07-mobile.png'),full_page=True)
        page.get_by_role('button',name='Abrir menu').click()
        expect(page.locator('aside a[href="#clients"]')).to_be_visible()
        page.locator('aside a[href="#clients"]').click()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Client mobile horizontal overflow'
        page.screenshot(path=str(out/'08-mobile-clientes.png'),full_page=True)
        assert not errors,errors
        assert not requests,requests
        docs=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        docs.on('pageerror',lambda e:errors.append(str(e)))
        docs.on('request',lambda r:requests.append(r.url))
        with tempfile.TemporaryDirectory() as directory:
            spec=create_app(Settings(data_dir=Path(directory),worker_enabled=False)).openapi()
        html=(ROOT/'app/static/api.html').read_text()
        import re
        html=re.sub(r'<link[^>]+>', '', html)
        html=re.sub(r'<script[^>]*>.*?</script>','',html,flags=re.S)
        docs.set_content(html)
        for name in ('template.css','app.css','api.css'):docs.add_style_tag(content=(ROOT/'app/static'/name).read_text())
        docs.add_script_tag(content='window.fetch=async()=>({json:async()=>('+json.dumps(spec)+')});')
        docs.add_script_tag(content=(ROOT/'app/static/api.js').read_text())
        expect(docs.locator('.route').first).to_be_visible()
        assert docs.locator('.route').count()>30
        docs.screenshot(path=str(out/'09-api.png'),full_page=True)
        assert not errors,errors
        assert not requests,requests
        (out/'result.json').write_text(json.dumps({'status':'passed','mode':'offline_visual_synthetic_no_network','javascript_errors':errors,'network_requests':requests,'checks':['actual Vue assets','login view','local interaction with mocked fetch','dashboard','clients','operation form','connections','contracts','mobile dashboard','mobile clients','local OpenAPI rendering']},indent=2),encoding='utf-8')
        browser.close()
    print('OFFLINE UI PASSED: real Vue assets; synthetic data/transports; zero network requests; no live integration asserted')

if __name__=='__main__': main()
