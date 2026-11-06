"""One-off isolated workspace preparation; excluded from the resulting product tree."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.request

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
changed = {'app/connection_management.py', 'app/login_support.py', 'tests/test_connection_management.py', 'tests/test_connection_login.py', 'tests/test_connection_browser.py', 'docs/CONEXOES.md'}

def write(name, text):
    Path(name).write_text(text, encoding='utf-8', newline='\n')
    changed.add(name)

def patch(name, old, new):
    text = Path(name).read_text(encoding='utf-8')
    assert text.count(old) == 1, (name, old[:100], text.count(old))
    write(name, text.replace(old, new, 1))

def run(*args, **kwargs):
    subprocess.run(args, check=True, **kwargs)

patch('app/main.py', '    def connection_access(connection_id, p, scope="read", private=False):', '    from .connection_management import register_connection_management\n    register_connection_management(app, store, connector, principal, authorize)\n\n    def connection_access(connection_id, p, scope="read", private=False):')
text = Path('app/connector.py').read_text()
text = text.replace('from .network import NetworkPolicy, limited_request', 'from .network import NetworkPolicy, limited_request\nfrom . import login_support')
a, b = text.index('def looks_like_login(response):'), text.index('\ndef save_cookies(client):')
text = text[:a] + 'def looks_like_login(response):\n    return login_support.is_login_response(response)\n\n' + text[b:]
text = text.replace('follow_redirects=False, trust_env=False, transport=self.transport', 'verify=login_support.tls_context(), follow_redirects=False, trust_env=False, transport=self.transport')
text = text.replace('"User-Agent": "ResellerManager/0.1.0"', '"User-Agent": connection["session"].get("user_agent") or "ResellerManager/0.1.1"')
a = text.index('    async def login_page(self, c, client):')
text = text[:a] + '''    async def login_page(self, c, client):
        return await login_support.login_page(self, c, client)

    async def inspect_login(self, identifier):
        return await login_support.inspect_login(self, identifier)

    async def connect(self, identifier):
        return await login_support.connect(self, identifier)

    async def browser_login(self, identifier):
        return await login_support.browser_login(self, identifier)
'''
write('app/connector.py', text)
patch('app/worker.py', '        d = self.store.pending_delivery()\n        if not d: return\n        delivered = False', '''        d = self.store.pending_delivery()
        if not d: return
        async with self.connector.lock(d["connection_id"] or "__global_webhooks__"):
            current = self.store.pending_delivery()
            if not current or current["id"] != d["id"]:
                return
            await self._deliver(d)

    async def _deliver(self, d):
        delivered = False''')
patch('app/store.py', '            attempt = r["attempts"] + 1', '            if r is None: return  # A fully deleted connection has no pending deliveries.\n            attempt = r["attempts"] + 1')
write('VERSION', '0.1.1\n')
write('app/__init__.py', '__version__ = "0.1.1"\n')

js = Path('app/static/app.js').read_text()
js = js.replace("showConnectionForm:false,connectionForm:", "editor:null,deleteTarget:null,deleteName:'',deleteUncertain:false,showConnectionForm:false,connectionForm:")
js = js.replace("base_url:'https://servip2p.com',auth_mode:'form'", "base_url:'https://servip2p.com',auth_mode:'browser'")
js = js.replace("session_received:'Sessão a confirmar'", "session_received:'Login confirmado · consulta pendente'")
js = js.replace("this.newToken='';clearTimeout", "this.newToken='';this.editor=null;this.deleteTarget=null;this.credentialForm={username:'',password:'',token:''};clearTimeout")
js = js.replace("async changeConnection(){this.clients=[];", "async changeConnection(){this.editor=null;this.deleteTarget=null;this.credentialForm={username:'',password:'',token:''};this.clients=[];")
js = js.replace("Conexão salva. Configure o contrato real antes de autenticar e habilitar as operações.", "Conexão salva. Autentique a conta; os campos do formulário serão detectados. Operações comerciais exigem contratos validados.")
start = js.index('  async connect(){')
end = js.index('  async disconnect(){', start)
js = js[:start] + '''  async connect(){await this.work(async()=>{let r;try{r=await this.api('/api/v1/connections/'+this.connectionId+'/connect',{method:'POST'});}finally{await this.loadBase();}this.notice=r.message||'Estado da conexão: '+this.statusLabel(r.status);});},
''' + js[end:]
start = js.index('  async saveCredentials(){')
end = js.index('  async loadClients(', start)
js = js[:start] + '''  async saveCredentials(){await this.work(async()=>{if(!Object.values(this.credentialForm).some(v=>v!==''))throw new Error('Preencha ao menos uma credencial para atualizar. Campos vazios são preservados.');await this.api('/api/v1/connections/'+this.connectionId,{method:'PATCH',body:JSON.stringify({revision:this.activeConnection.revision,credentials:this.credentialForm})});this.credentialForm={username:'',password:'',token:''};await this.loadBase();this.notice='Credenciais informadas atualizadas. Valores em branco foram preservados. Autentique novamente.';});},
  async beginEditConnection(c){await this.work(async()=>{const current=await this.api('/api/v1/connections/'+c.id);this.connectionId=c.id;await this.loadConnection();this.deleteTarget=null;this.editor={id:c.id,revision:current.revision,name:current.name,base_url:current.base_url,auth_mode:current.auth_mode,credentials:{username:'',password:'',token:''},clear_credentials:[],login:JSON.parse(JSON.stringify(current.profile.login)),token_auth:JSON.parse(JSON.stringify(current.profile.token_auth))};await this.$nextTick();document.getElementById('connection-editor')?.scrollIntoView({block:'start',behavior:'smooth'});});},
  async saveConnection(){await this.work(async()=>{const {id,...payload}=this.editor;const result=await this.api('/api/v1/connections/'+id,{method:'PATCH',body:JSON.stringify(payload)});this.editor=null;this.clients=[];this.queryResult=null;await this.loadBase();this.notice='Conexão atualizada. Sessão invalidada; autentique novamente. Operações canceladas: '+result.cancelled_operations+'. Agendamentos pausados: '+result.paused_schedules+'.';});},
  async beginDeleteConnection(c){await this.work(async()=>{const preview=await this.api('/api/v1/connections/'+c.id+'/deletion-preview');this.editor=null;this.deleteTarget={id:c.id,...preview};this.deleteName='';this.deleteUncertain=false;await this.$nextTick();document.getElementById('connection-delete')?.scrollIntoView({block:'start',behavior:'smooth'});});},
  async removeConnection(){await this.work(async()=>{const target=this.deleteTarget;await this.api('/api/v1/connections/'+target.id,{method:'DELETE',body:JSON.stringify({revision:target.revision,confirm_name:this.deleteName,acknowledge_uncertain:this.deleteUncertain})});if(this.connectionId===target.id)this.connectionId='';this.deleteTarget=null;this.deleteName='';this.clients=[];this.queryResult=null;this.loginInspection=null;this.credentialForm={username:'',password:'',token:''};this.events=this.events.filter(e=>e.connection_id!==target.id);await this.loadBase();this.notice='Conexão e dados locais vinculados excluídos. Nenhuma conta ou cliente foi apagado no fornecedor.';});},
  async applyLoginSuggestion(){if(!this.loginInspection?.suggested_login)return;await this.work(async()=>{if(this.editor){this.editor.login=JSON.parse(JSON.stringify(this.loginInspection.suggested_login));this.notice='Campos detectados preenchidos no editor. Salve para aplicar.';return;}await this.api('/api/v1/connections/'+this.connectionId,{method:'PATCH',body:JSON.stringify({revision:this.activeConnection.revision,login:this.loginInspection.suggested_login})});await this.loadBase();this.notice='Campos detectados aplicados. Autentique a conexão novamente.';});},
''' + js[end:]
write('app/static/app.js', js)
html = Path('frontend/app.html').read_text().replace('v0.1.0', 'v0.1.1')
marker = '      <div class="connection-grid spaced">'
assert html.count(marker) == 1
editor = '''      <form v-if="editor && isAdmin" id="connection-editor" class="panel padded spaced" @submit.prevent="saveConnection">
        <h2>Editar conexão</h2><p class="muted small">Credenciais em branco são preservadas. Ao mudar o endereço, as credenciais anteriores são removidas por segurança. A edição invalida a sessão, limpa o cache de clientes, cancela operações na fila e pausa agendamentos.</p>
        <div class="form-grid">
          <label class="field">Nome da conexão<input v-model="editor.name" required maxlength="100"></label>
          <label class="field">Endereço do painel<input v-model="editor.base_url" type="url" required></label>
          <label class="field">Modo de autenticação<select v-model="editor.auth_mode"><option value="browser">Login com navegador integrado</option><option value="form">Login por formulário HTTP</option><option value="token">Token da API pública</option></select></label>
          <label class="field">Novo usuário<input v-model="editor.credentials.username" autocomplete="off" placeholder="Vazio: manter o atual"></label>
          <label class="field">Nova senha<input v-model="editor.credentials.password" type="password" autocomplete="new-password" placeholder="Vazio: manter a atual"></label>
          <label class="field">Novo token<input v-model="editor.credentials.token" type="password" autocomplete="off" placeholder="Vazio: manter o atual"></label>
        </div>
        <details class="spaced"><summary>Configuração de login e token</summary><p class="muted small">Detecção automática quando os nomes estiverem vazios. O seletor de sucesso é opcional quando uma consulta autenticada ou a página do painel confirma a sessão.</p>
          <div class="form-grid"><label class="field">Página de login<input v-model="editor.login.page" placeholder="/login/" required></label><label class="field">Seletor do formulário<input v-model="editor.login.form_selector" placeholder="form"></label><label class="field">Nome do campo usuário<input v-model="editor.login.username_field" placeholder="Automático"></label><label class="field">Nome do campo senha<input v-model="editor.login.password_field" placeholder="Automático"></label><label class="field">Seletor do usuário<input v-model="editor.login.username_selector"></label><label class="field">Seletor da senha<input v-model="editor.login.password_selector"></label><label class="field">Seletor do botão entrar<input v-model="editor.login.submit_selector"></label><label class="field">Seletor de sucesso (opcional)<input v-model="editor.login.success_selector" placeholder="Automático / consulta autenticada"></label><label class="field">Local do token<select v-model="editor.token_auth.location"><option value="header">Cabeçalho</option><option value="query">Parâmetro da URL</option><option value="body">Corpo</option></select></label><label class="field">Nome do token<input v-model="editor.token_auth.name" placeholder="Conforme o contrato da API"></label><label class="field">Prefixo do token<input v-model="editor.token_auth.prefix" placeholder="Conforme o contrato da API"></label></div>
          <p class="muted small">Limpar credenciais explicitamente:</p><div class="actions wrap"><label class="check"><input type="checkbox" value="username" v-model="editor.clear_credentials">Remover usuário salvo</label><label class="check"><input type="checkbox" value="password" v-model="editor.clear_credentials">Remover senha salva</label><label class="check"><input type="checkbox" value="token" v-model="editor.clear_credentials">Remover token salvo</label></div>
        </details><div class="actions spaced"><button class="btn primary" :disabled="busy">Salvar alterações</button><button type="button" class="btn secondary" @click="editor=null" :disabled="busy">Cancelar edição</button></div>
      </form>
      <form v-if="deleteTarget && isAdmin" id="connection-delete" class="panel padded spaced" @submit.prevent="removeConnection">
        <h2>Excluir conexão definitivamente</h2><p>Esta ação remove <strong>{{deleteTarget.name}}</strong>, suas credenciais, sessão, perfil, cache de clientes, operações, agendamentos e eventos locais. Tokens restritos são ajustados ou revogados. Não exclui contas no fornecedor nem altera backups externos.</p>
        <p class="notice spaced">Clientes em cache: {{deleteTarget.impact.clients}} · Operações: {{deleteTarget.impact.operations}} · Agendamentos: {{deleteTarget.impact.schedules}} · Eventos: {{deleteTarget.impact.events}} · Entregas de webhook: {{deleteTarget.impact.deliveries}}</p>
        <p v-if="deleteTarget.impact.running" class="feedback error">Há uma operação em execução. Aguarde sua conclusão antes de excluir.</p>
        <label v-if="deleteTarget.impact.uncertain" class="check spaced"><input type="checkbox" v-model="deleteUncertain">Reconheço que há operações incertas e confirmo a perda do histórico local. A exclusão não desfaz cobranças no fornecedor.</label>
        <label class="field">Digite o nome exato da conexão<input v-model="deleteName" autocomplete="off" required></label><div class="actions spaced"><button class="btn danger" :disabled="busy || deleteName!==deleteTarget.name || deleteTarget.impact.running>0 || (deleteTarget.impact.uncertain>0 && !deleteUncertain)">Excluir definitivamente</button><button type="button" class="btn secondary" @click="deleteTarget=null" :disabled="busy">Cancelar exclusão</button></div>
      </form>
'''
html = html.replace(marker, editor + marker)
needle = "{{c.id===connectionId?'Conexão selecionada':'Selecionar conexão'}}</button>"
assert html.count(needle) == 1
html = html.replace(needle, needle + '<div v-if="isAdmin" class="actions spaced connection-card-actions"><button class="btn secondary" @click="beginEditConnection(c)" :disabled="busy">Editar</button><button class="btn danger" @click="beginDeleteConnection(c)" :disabled="busy">Excluir conexão</button></div>')
html = html.replace('Copie os nomes reais para <code>login.username_field</code> e <code>login.password_field</code> no perfil.', 'Os nomes podem ser detectados automaticamente. A sugestão não contém valores de CSRF, cookies ou credenciais.')
html = html.replace('<pre>{{pretty(loginInspection)}}</pre>', '<button v-if="loginInspection.suggested_login && isAdmin" class="btn secondary" @click="applyLoginSuggestion" :disabled="busy">Aplicar campos detectados</button><pre>{{pretty(loginInspection)}}</pre>')
html = html.replace('Substituir credenciais da conexão ativa', 'Atualizar credenciais da conexão ativa').replace('Substitui o conjunto inteiro e invalida a sessão local. Dados atuais nunca são exibidos.', 'Somente campos preenchidos são alterados. Campos vazios mantêm os valores salvos. A sessão será invalidada; para remover um valor, use Editar.')
write('frontend/app.html', html)
write('app/static/app.css', Path('app/static/app.css').read_text() + '\n/* Connection lifecycle controls; existing layout preserved. */\n.btn.danger{background:#fff0ed;border:1px solid #d98b80;color:#922d22}.connection-card-actions{display:flex;gap:10px;flex-wrap:wrap}.connection-card-actions .btn{flex:1}#connection-editor,#connection-delete{scroll-margin-top:90px}details summary{cursor:pointer;font-weight:600}\n')
patch('.github/workflows/ci.yml', '      - run: python -m pytest -q --junitxml=build/test-results.xml', '''      - name: Prepare integrated browser for connection regression tests
        run: python -m playwright install --with-deps chromium
      - run: python -m pytest -q --junitxml=build/test-results.xml
        env:
          RESMAN_RUN_BROWSER_TESTS: '1' ''')
write('CHANGELOG.md', Path('CHANGELOG.md').read_text().replace('# Changelog', '# Changelog\n\n## 0.1.1\n\n- Edição de conexões e credenciais sem apagar campos vazios.\n- Exclusão local completa, com confirmação, revisão e isolamento.\n- Login com descoberta de formulário/CSRF, redirecionamentos HTML e diagnóstico TLS/rede.\n- Navegador sem bloqueio por success_selector vazio; confirmação positiva de sessão.\n- Testes reais de navegador em Windows/Linux; Chromium distribuído preservado.'))
# Keep the historical validation reports unchanged; this is a new revision.
run('node', 'frontend/build.mjs')
run('node', 'frontend/build.mjs', '--check')
run('node', '--test', 'tests/frontend-build.test.mjs')
changed.add('app/static/render.js')
run(sys.executable, '-m', 'compileall', '-q', 'app', 'scripts', 'tests')
run(sys.executable, '-m', 'playwright', 'install', '--with-deps', 'chromium')
os.environ['RESMAN_RUN_BROWSER_TESTS'] = '1'
run(sys.executable, '-m', 'pytest', '-q')
run(sys.executable, 'scripts/smoke_runtime.py')
from app.main import create_app
from app.settings import Settings
with tempfile.TemporaryDirectory() as tmp:
    app = create_app(Settings(data_dir=Path(tmp), worker_enabled=False, test_network=True))
    write('examples/reseller-manager.openapi.json', json.dumps(app.openapi(), ensure_ascii=False, indent=2) + '\n')
manifest = json.loads(Path('MANIFEST-SHA256.json').read_text())
manifest['version'] = '0.1.1'
for name in set(manifest['files']) | changed:
    if Path(name).is_file():
        manifest['files'][name] = hashlib.sha256(Path(name).read_bytes()).hexdigest()
write('MANIFEST-SHA256.json', json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
# Create only immutable Git objects. The connected GitHub tool will publish the
# tested tree on a new branch; this runner cannot move main or create a release.
repository = os.environ['GITHUB_REPOSITORY']
def api(path, payload):
    request = urllib.request.Request('https://api.github.com/repos/' + repository + path, data=json.dumps(payload).encode(), headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'], 'Accept':'application/vnd.github+json', 'Content-Type':'application/json'}, method='POST')
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)
entries=[]
for name in sorted(changed):
    assert Path(name).is_file(), name
    blob=api('/git/blobs', {'content':Path(name).read_text(encoding='utf-8'), 'encoding':'utf-8'})
    entries.append({'path':name,'mode':'100644','type':'blob','sha':blob['sha']})
tree=api('/git/trees', {'base_tree':'01b9f56b3557cf566bba0d517cbab3b6fa40f687', 'tree':entries})
print('TESTED_PRODUCT_TREE=' + tree['sha'])
print('CHANGED_PRODUCT_FILES=' + json.dumps(sorted(changed)))
