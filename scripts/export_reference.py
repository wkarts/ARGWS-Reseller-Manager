"""Export this application's OpenAPI and Postman collection; no provider calls."""
from pathlib import Path
import json
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.main import create_app
from app.settings import Settings

def request(name,method,path,body=None,*,idempotent=False):
    headers=[{'key':'Accept','value':'application/json'}]
    item={'name':name,'request':{'method':method,'header':headers,'url':'{{base_url}}'+path}}
    if body is not None:
        headers.append({'key':'Content-Type','value':'application/json'})
        item['request']['body']={'mode':'raw','raw':json.dumps(body,ensure_ascii=False,indent=2),'options':{'raw':{'language':'json'}}}
    if idempotent:headers.append({'key':'Idempotency-Key','value':'{{idempotency_key}}'})
    return item

def main():
    output=ROOT/'examples';output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='reseller-export-') as directory:
        spec=create_app(Settings(data_dir=Path(directory),worker_enabled=False)).openapi()
    (output/'reseller-manager.openapi.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    conn='/api/v1/connections/{{connection_id}}'
    items=[
        request('Meu token da API própria','GET','/api/v1/me'),
        request('Listar conexões','GET','/api/v1/connections'),
        request('Cadastrar conexão — configure o perfil antes de autenticar','POST','/api/v1/connections',{'name':'Minha revenda','base_url':'https://servip2p.com','auth_mode':'form','credentials':{'username':'{{panel_username}}','password':'{{panel_password}}'},'profile':json.loads((ROOT/'app/static/koffice-observed.json').read_text())}),
        request('Consultar conexão e perfil (admin)','GET',conn),
        request('Inspecionar formulário sem login','GET',conn+'/login-form'),
        request('Capacidades validadas','GET',conn+'/capabilities'),
        request('Autenticar conexão conforme perfil','POST',conn+'/connect'),
        request('Listar clientes no painel','GET',conn+'/clients?start=0&length=50&search='),
        request('Listar cache local (não consulta o painel)','GET',conn+'/clients?start=0&length=50&cached=true'),
        request('Consultar cliente','GET',conn+'/clients/{{client_id}}'),
        request('Consultar planos','POST',conn+'/queries/list_plans',{}),
        request('Consultar saldo','POST',conn+'/queries/get_balance',{}),
        request('Renovar cliente — desabilitado até configurar perfil e confirmar','POST',conn+'/clients/{{client_id}}/renewals',{'parameters':{'plan_id':'{{plan_id}}'},'confirmed':False},idempotent=True),
        request('Alteração genérica — contrato precisa ser validado','POST',conn+'/operations/{{action}}',{'parameters':{},'confirmed':False},idempotent=True),
        request('Operações recentes','GET','/api/v1/operations'),
        request('Resultado da operação','GET','/api/v1/operations/{{operation_id}}'),
        request('Cancelar somente enquanto na fila','POST','/api/v1/operations/{{operation_id}}/cancel'),
        request('Eventos após cursor','GET','/api/v1/events?after=0'),
        request('Agendamentos','GET','/api/v1/schedules'),
        request('Pagamento confirmado pelo ERP — não é callback de banco','POST',conn+'/payments/confirmed',{'reference':'{{payment_reference}}','client_id':'{{client_id}}','parameters':{'plan_id':'{{plan_id}}'},'confirmed':False}),
    ]
    collection={'info':{'name':'Reseller Manager 0.1.0 — SUA API, não a API oficial kOfficePanel','description':'As rotas pertencem à aplicação entregue. Dados do fornecedor são placeholders. Alterações exigem perfil aprovado, confirmed=true e chave única. Não há scripts que leem credenciais nem operações reais executadas automaticamente. Não use Collection Runner para executar a coleção inteira.','schema':'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'},'auth':{'type':'bearer','bearer':[{'key':'token','value':'{{api_token}}','type':'string'}]},'variable':[{'key':k,'value':v} for k,v in {'base_url':'http://127.0.0.1:48190','api_token':'','connection_id':'','client_id':'','plan_id':'','operation_id':'','action':'renew_client','idempotency_key':'','payment_reference':'','panel_username':'','panel_password':''}.items()],'item':items}
    (output/'reseller-manager.postman_collection.json').write_text(json.dumps(collection,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    methods=sum(len([m for m in ms if m in {'get','post','put','patch','delete'}]) for ms in spec['paths'].values())
    print(f'Exported own API: {len(spec["paths"])} paths; {methods} HTTP operations; {len(items)} Postman requests')

if __name__=='__main__':main()
