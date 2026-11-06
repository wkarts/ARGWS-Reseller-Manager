# Validação da entrega 0.1.0

Registro de 6 de novembro de 2026. Este relatório distingue testes do software, testes visuais e integração com o fornecedor.

## Executado neste ambiente

Ambiente: Linux, Python 3.13.5, Node 22.16.0. A matriz preparada no GitHub utiliza Python 3.12, mas não foi executada remotamente nesta entrega.

| Verificação | Resultado real |
|---|---|
| `python -m pytest -q --junitxml=build/pytest.xml` | **60 passaram**, zero falhas; última execução: 3,51 s. |
| `python scripts/smoke_runtime.py` | Passou: processo Uvicorn real em loopback, saúde, autenticação própria, HTML, docs, OpenAPI e arquivos estáticos. |
| `node frontend/build.mjs --check` | Passou: render compilado corresponde ao template. |
| `node --check app/static/app.js` e `api.js` | Passaram. |
| `python -m compileall -q app packaging scripts tests` | Passou. |
| `python scripts/ui_render_offline.py` | Passou: ativos Vue reais, transportes e dados simulados, zero requisições de rede e zero erros JavaScript. |
| YAML de Compose e três workflows | Parseado sem erro. Isso não substitui `docker compose config`, actionlint ou execução de Actions. |
| `python scripts/export_reference.py` | Exportou 30 caminhos / 34 operações HTTP da API própria e 20 requisições de exemplo Postman. |

## Cobertura da suíte Python

Autenticação e revogação de tokens próprios; autorização por conexão; criptografia/persistência; ausência da chave com banco existente; trava de instância; respostas de validação sem credenciais; projeção de dados/remoção de HTML; não divulgação de senha do cliente; recusa de HTTP 200 com HTML de login; formulário com campos ocultos/CSRF/cookies; bloqueio de redirect externo; perfil não confirmado; contratos alterados após enfileiramento; repetição idempotente e conflito de chave; concorrência no mesmo cliente; timeout/erro após possível alteração remota; execução interrompida e recuperação sem reenvio; cancelamento e conciliação manual; renovação agendada; revisão do perfil associada à autorização; confirmação de pagamento com referência única; evento filtrado por conta; WebSocket; webhook de saída; inspeção Postman/HAR; preflight e reautenticação antes de alterações.

O fornecedor desses testes é **uma fixture sintética `httpx.MockTransport`**. As rotas `/synthetic/*`, os usuários e as senhas de `tests/` são exclusivamente de teste. Não são endpoints nem credenciais do kOfficePanel.

## Verificação visual

Foram usados os arquivos reais `vue.js`, `render.js`, `app.js` e CSS em Chromium, sem navegação HTTP. A suíte injeta somente dados fictícios e substitutos de fetch/WebSocket dentro da página de teste; o código entregue da aplicação não contém esses mocks.

Verificado: login, navegação, visão geral, tabela de clientes, formulário de renovação, conexões, perfil de integração, documentação local, largura móvel de 390 px, menu móvel recolhido e ausência de rolagem horizontal do documento. Corrigido contraste do título do login. As imagens em `docs/capturas/` são dessa execução simulada, não de uma conta real.

A tentativa separada de `scripts/ui_smoke.py`, que utiliza navegador + processo HTTP local + painel remoto simulado, foi **bloqueada pela política do Chromium deste ambiente**: `net::ERR_BLOCKED_BY_ADMINISTRATOR`. Essa verificação NÃO foi contada como aprovada. O script está incluído para um ambiente de homologação que permita acesso à aplicação local. Nenhuma política do navegador foi alterada.

## Não executado / não comprovado

- Compilação PE/EXE Windows; interação Tkinter/bandeja no Windows; execução do EXE resultante.
- Build/execução da imagem Docker e navegador dentro da imagem. Docker não está disponível aqui.
- Workflows GitHub remotos, publicação GHCR, assinatura de binário, release ou deploy.
- Autenticação Playwright contra uma página real; suporte a CAPTCHA/2FA não está homologado.
- Login, listagem ou alteração real no Servip2P/kOfficePanel. Nenhuma conta foi modificada nem cobrada.
- Rotas reais de criar/renovar cliente, mudar telas/plano/tecnologia, transferir créditos ou pagar. A URL observada de listagem não determina sozinha o contrato.
- Auditoria independente de segurança, teste de carga, múltiplas réplicas ou banco compartilhado em rede.

## Evidências e reprodução

`qa-results/report.json`: resumo estruturado. `qa-results/pytest.xml`: resultado pytest. `qa-results/ui-offline.json`: verificação visual. `examples/`: especificação e coleção da API **própria**. `profiles/koffice-observed.json`: referência observada, desabilitada.

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python scripts/smoke_runtime.py
node frontend/build.mjs --check
```

Verificação visual opcional, em ambiente com Playwright/Chromium disponível:

```sh
python -m pip install -r requirements-browser.txt
python -m playwright install chromium
python scripts/ui_render_offline.py
# Somente em ambiente que autorize navegador -> HTTP local:
python scripts/ui_smoke.py
```

Não habilite operações financeiras apenas porque estes testes passaram. A integração do fornecedor precisa de evidência própria e homologação controlada, com autorização do titular da revenda.
