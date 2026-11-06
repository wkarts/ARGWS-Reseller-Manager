# Reseller Manager — 0.1.4

Ferramenta própria de revendas em **Python/FastAPI**, adaptada do modelo `escrituracao-contabil-0.3.0-dev.9.1.zip` fornecido por Wallace. Painel web Vue local, API REST, eventos WebSocket, fila persistente SQLite, credenciais criptografadas, execução Docker e projeto de executável gráfico Windows x64.

**Esta entrega não é uma API oficial do kOfficePanel nem uma homologação da instalação Servip2P.** O software de integração está implementado e é testável; os endpoints remotos de alteração dependem de contratos reais aprovados. O perfil inicial contém somente a URL de listagem observada, DESABILITADA: método, autenticação, campos e paginação não foram comprovados. Não foram feitos login, cadastros, pagamentos ou renovações reais.

## Entregue

- Conexões por token (local/nome/prefixo configuráveis), formulário HTTP com cookies/CSRF e login com Playwright/Chromium integrado.
- API própria com tokens admin/operate/read, escopo por conexão, revogação e OpenAPI.
- Consulta de clientes, cache incremental protegido e projeção explícita de colunas, sem exportar senhas de clientes.
- Executor de cadastros, renovações, planos, telas, tecnologia, bloqueio, revendas, créditos e cobranças: habilitação depende de mapeamento real, evidência e regra de sucesso.
- Fila durável, Idempotency-Key, prevenção de concorrência por cliente, estado de conferência para resultados ambíguos, cancelamento antes da execução.
- Agendamentos de renovação e entrada autenticada de confirmação de pagamento pelo ERP. **Não inclui gateway de pagamento ou validação automática de Pix.**
- WebSocket com autenticação na primeira mensagem e webhooks de saída HMAC-SHA256, IDs estáveis e até oito tentativas.
- Inspeção de coleções Postman v2/v2.1 e HAR: rascunhos desabilitados, sem executar scripts ou importar cookies/credenciais de forma automática.
- UI clara responsiva, documentação local sem CDN, lançador Windows com bandeja reaproveitada do modelo.

## 1. Executar no Windows pelo código-fonte

Instale **Python 3.12 x64**. Na raiz do projeto:

```cmd
scripts\start-windows.cmd
```

O script cria `.venv`, instala dependências e abre a administração gráfica. Clique em **Abrir painel** e **Copiar token de primeiro acesso**. A pasta padrão dos dados é `%LOCALAPPDATA%\ResellerManager\data`. A janela pode permanecer na bandeja; o serviço precisa ficar em execução para processar agendamentos.

Alternativa no terminal, sem janela gráfica:

```cmd
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m app.runtime --host 127.0.0.1 --port 48190 --data .\data
```

Acesse `http://127.0.0.1:48190`. O primeiro token fica em `data\admin.token`. O token do Reseller Manager autentica SUA API. O token do kOfficePanel é outro segredo, cadastrado na conexão.

## 2. Gerar o binário Windows

Em PowerShell no Windows x64:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1
```

Esse comando prepara dependências, executa testes, gera o pacote com `ResellerManager.exe`, valida o cabeçalho PE x64, executa smoke HTTP contra o executável e cria ZIP/checksum em `artifacts/`.

```powershell
# Chromium já está incluído por padrão; opção abaixo mantida por compatibilidade:
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1 -WithBrowser

# Variante em um único .exe (o padrão é pasta portátil):
powershell -ExecutionPolicy Bypass -File .\scripts\build-windows.ps1 -OneFile
```

No pacote portátil padrão, **distribua a pasta inteira**, não apenas o EXE. O usuário final não precisa instalar Python. Para executar sem interface: `ResellerManager.exe --server --host 127.0.0.1 --port 48190 --data C:\ResellerData`.

**O ZIP desta entrega contém código-fonte e o processo de build, não um EXE Windows já compilado.** O ambiente de geração foi Linux, sem Windows/Wine. O build nativo foi preparado, mas não executado aqui. Workflow `.github/workflows/windows.yml` pode gerar o binário no runner Windows após publicação do repositório.

## 3. Distribuição: GHCR/Dockge e build local

### 3.1. Deploy pronto pelo GHCR — sem código-fonte

Use **`deploy/compose.yaml`** e **`deploy/.env.example`**. O pacote de deploy gerado
pelo workflow já inclui `compose.yaml` e `.env`, sem segredos e sem build local.

```sh
cd deploy
cp .env.example .env
# Ajuste imagem, porta e origem HTTPS no .env. A imagem deve estar publicada.
docker compose pull
docker compose up -d
docker compose exec -T api cat /data/admin.token
```

O modelo do deploy permite acesso pela rede em `0.0.0.0:48190`; use firewall e
proxy HTTPS. Para proxy no mesmo host, ajuste `RESMAN_BIND=127.0.0.1`.
No Dockge, copie compose e variáveis para os editores da stack ou use sua pasta de stacks.
Persistência em `./data`, healthcheck mantido, inicialização de permissões e API não-root.
A imagem padrão e o executável Windows já incluem Playwright e Chromium. Não é necessário habilitar `RESMAN_BROWSER_ENABLED`, instalar dependências ou baixar navegador na máquina de uso. As tags `-browser` são aliases de compatibilidade; `.env` antigo com `RESMAN_BROWSER_ENABLED=0` não desabilita o recurso.

O workflow `Validate` testa Windows/Linux antes de construir as duas imagens e o
executável Windows. Push em main/develop/tags publica imagens aprovadas no GHCR;
PR apenas valida, sem publicar. Os artefatos de deploy e Windows ficam no Actions. Após push/merge em `main` (ou tag `vVERSION`), a release é criada automaticamente somente depois dos testes e builds nativos. O publicador verifica SHA, checksums e Chromium integrado antes de expor os downloads.
Imagem: `ghcr.io/wkarts/argws-reseller-manager` (owner/repo calculados no workflow).
Canais: `latest`, `develop`, versão promovida na release e `sha-...`, incluindo aliases `-browser`. Releases publicadas não são substituídas; incremente `VERSION` para uma nova entrega. Guia: [distribuição integrada](docs/DISTRIBUICAO-INTEGRADA.md).
Não há publicação de imagem ou geração de EXE comprovada até os workflows passarem.

Guia completo, atualização e preservação dos dados: [deploy/README.md](deploy/README.md).

### 3.2. Build Docker local — mantém o fluxo anterior

Na raiz do código-fonte:

```sh
cp .env.example .env
docker compose up -d --build
docker compose logs --tail=100 api
docker compose exec api cat /data/admin.token
```

Windows CMD: use `copy .env.example .env` no lugar de `cp`.

Painel: `http://127.0.0.1:48190` · documentação: `/docs` · especificação: `/openapi.json` · saúde: `/health`.

Persistência em **`./data:/data`**. O serviço transitório `data-init` ajusta permissões do volume, sem rede; a API executa como UID 10001, sem capabilities, com filesystem somente leitura. A porta externa fica em loopback por padrão. Para acesso externo, configure proxy HTTPS e `RESMAN_PUBLIC_ORIGIN`; `RESMAN_BIND=0.0.0.0` altera o bind, mas não instala TLS.

O container não depende de Node em execução. Os assets Vue já estão compilados. Redis não é necessário nesta versão: a fila usa SQLite e um único processo para funcionar também no executável Windows.

**Docker não estava instalado neste ambiente de entrega.** Os arquivos foram inspecionados, mas o build e a execução da imagem precisam da rodada nativa do workflow `Container` ou do seu Docker.

## 4. Configurar a primeira conexão

1. Entre com o token próprio da instalação e cadastre a conta em **Conexões**. O domínio precisa estar em `RESMAN_ALLOWED_HOSTS` (padrão: `servip2p.com`).
2. Para login HTTP, use **Inspecionar formulário**; configure os nomes exatos em `login.username_field` e `login.password_field`, na tela **Contratos e descoberta**. O conector preserva os campos ocultos da página.
3. Para token, copie do contrato público a localização, o nome e o prefixo. **Bearer não é presumido.**
4. Importe a coleção Postman/HAR ou edite o perfil. Confirme método, caminho, parâmetros, resposta e campos. Só depois use `verified: true` com `evidence` explicando a validação.
5. Autentique a conexão e faça primeiro uma consulta. Um HTML de login com HTTP 200 não é aceito como sucesso.
6. Habilite alterações individualmente e teste com uma conta de homologação. A ferramenta NÃO testa operações com custo automaticamente.

## 5. Consultar clientes pela SUA API

Windows CMD (uma linha):

```cmd
curl --request GET "http://127.0.0.1:48190/api/v1/connections/ID_DA_CONEXAO/clients?start=0&length=50" --header "Authorization: Bearer TOKEN_DA_SUA_API"
```

Após mapear a renovação, use um arquivo `renovacao.json`:

```json
{"parameters":{"plan_id":"ID_REAL_DO_PLANO"},"confirmed":true}
```

```cmd
curl --request POST "http://127.0.0.1:48190/api/v1/connections/ID_DA_CONEXAO/clients/ID_DO_CLIENTE/renewals" --header "Authorization: Bearer TOKEN_DA_SUA_API" --header "Content-Type: application/json" --header "Idempotency-Key: renovacao-fatura-400" --data-binary "@renovacao.json"
```

`plan_id` é apenas um exemplo de parâmetro interno; configure a tradução para o contrato real do fornecedor. HTTP 202 significa trabalho registrado, não renovação concluída. Consulte `/api/v1/operations/ID`.

## Desenvolvimento e validação

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python scripts/smoke_runtime.py
node frontend/build.mjs --check
```

Node só é necessário para **alterar/recompilar o template Vue**, não para usar a aplicação. Edite `frontend/app.html`, rode `node frontend/build.mjs` e versione `app/static/render.js`.

Referências utilizáveis: `examples/reseller-manager.openapi.json` e `examples/reseller-manager.postman_collection.json` (API própria, não a coleção oficial kOfficePanel). O relatório desta entrega está em `qa-results/report.json`; imagens com dados sintéticos estão em `docs/capturas/`.

Guia completo: [deploy GHCR/Dockge](deploy/README.md), [integração](docs/INTEGRACAO.md), [operação](docs/OPERACAO.md), [segurança](docs/SEGURANCA.md), [validação](docs/VALIDACAO.md), [reaproveitamento do modelo](docs/TEMPLATE.md).

Autoria: **Wallace Kleiton — wkarts@gmail.com — WWSoftware’s**. Nome técnico: `reseller-manager`. Nome comercial provisório: **Reseller Manager**. A situação de publicação e dos builds é verificável no GitHub Actions/Releases; a homologação no fornecedor é independente.


## Auditoria passiva e dry-run

Após entrar no painel, abra **Auditoria e dry-run** no menu ou acesse `/audit` na mesma instalação.
A matriz e as simulações são executadas exclusivamente na API local e **não geram requisições ao fornecedor**, créditos, alterações ou agendamentos. Consulte `docs/KOFFICE-AUDITORIA-PASSIVA.md` para o inventário já observado e os limites da auditoria.
