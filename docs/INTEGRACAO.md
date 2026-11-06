# Contrato de integração

## Não confundir as duas APIs

`/api/v1/...` é o contrato do Reseller Manager. `profile.endpoints` contém os caminhos do fornecedor. Um endpoint disponível na sua API não significa que a respectiva operação do kOfficePanel já foi descoberta ou homologada.

A única URL remota observada na conversa foi `/clients/api/?get_clients`, com estrutura DataTables. Não foram confirmados método, parâmetros, campos de cada índice ou mecanismo de token. Por isso o perfil é desabilitado e não mapeia a coluna de senha presumidamente existente.

## Perfil

`token_auth` define `location` (`header`, `query`, `body`), `name` e `prefix`. Configure `Authorization` / `Bearer ` somente quando o contrato do fornecedor realmente exigir. Tokens não podem ser usados como cabeçalhos Host/Cookie ou cabeçalhos de transporte.

`login` define página, nomes de usuário/senha, seletor do formulário, campos adicionais e seletores do modo navegador. O modo HTTP lê os campos ocultos do formulário e envia POST. Formulários/redirects externos são bloqueados. O modo navegador é opcional e requer `success_selector` verificável, Playwright e Chromium.

Cada ação em `endpoints` possui:

| Campo | Uso |
|---|---|
| method / path | Método e caminho relativo do fornecedor. Pode incluir a query original. |
| encoding | `query`, `json` ou `form`; não converte formulário em JSON sem autorização. |
| params / body / headers | Campos fixos e templates de valores. |
| required | Lista de parâmetros internos obrigatórios. |
| verified / evidence | Aprovação explícita do contrato e origem dessa confirmação. |
| data_path | Caminho com pontos para o objeto/lista na resposta. Vazio representa a raiz. |
| fields | Mapeamento dos nomes seguros de saída para índices/caminhos do fornecedor. |
| success_path / success_value | Regra obrigatória para confirmar escritas. Igualdade é estrita: `true` não é `1`. |
| success_status | Status HTTP permitidos para confirmar uma alteração. |

Templates suportados:

```text
{{input.client_id}}
{{input.plan_id}}
{{input.screens}}
{{secret.token}}
{{session.csrf.csrf}}
```

Valor que é apenas um template preserva tipo numérico, booleano ou objeto. Componentes de URL dinâmicos são escapados. Variável ausente interrompe antes da chamada. Não há execução de código, JavaScript Postman ou interpolação livre Python.

Para DataTables, `fields` pode mapear `id` para `"0"` e outros campos para os índices COMPROVADOS. Para objetos, use `"user.id"`. Não copie índices hipotéticos desta documentação. Campos permitidos: `id`, `username`, `name`, `expires_at`, `plan`, `screens`, `technology`, `status`, `credits`, `amount`, `created_at`.

## Ações implementadas no adaptador

Leitura: `list_clients`, `get_client`, `list_plans`, `list_technologies`, `get_balance`, `list_resellers`, `get_reseller`, `list_payments`.

Alteração: `create_client`, `renew_client`, `change_plan`, `change_screens`, `migrate_technology`, `enable_client`, `disable_client`, `delete_client`, `create_reseller`, `update_reseller`, `credit_transfer`, `create_payment`.

As ações de aumento/redução de telas, créditos e tecnologia **não presumem** que o painel use quantidade absoluta, delta, estorno ou proporcionalidade. Esses detalhes devem ser definidos no perfil e na regra comercial antes de autorizar a chamada.

Chamadas próprias:

```text
POST /api/v1/connections/{id}/queries/{action}
{ "client_id": "..." }

POST /api/v1/connections/{id}/operations/{action}
Idempotency-Key: referencia-unica
{ "parameters": { ... }, "confirmed": true }
```

Existem aliases para `GET/POST /connections/{id}/clients`, consulta individual e `POST /clients/{id}/renewals`. Todos os demais recursos estão acessíveis pelo executor de ações e visíveis no OpenAPI.

## Login e expiração

1. A autenticação é sempre na conta autorizada cadastrada; não há bypass de privilégios.
2. HTTP: GET do formulário, preservação de campos ocultos/cookies, POST com os nomes configurados, redirects somente na mesma origem.
3. Uma resposta de login pode gerar `session_received`; somente consulta JSON validada promove para `authenticated`.
4. Antes de alterar com sessão, o worker faz uma consulta de autenticação. Se expirada, tenta login uma vez e confirma por leitura. Nunca repete uma alteração para "ver se agora funciona".
5. Cookies ficam criptografados no banco. CAPTCHA/2FA/bloqueios podem exigir ação humana. O modo navegador não resolve desafios automaticamente nem contorna controles.
6. O modo navegador faz login e exporta cookies/CSRF para o cliente HTTP. Não implementa execução permanente de JavaScript, LocalStorage como token, perfil remoto por VNC ou manipulação de telas arbitrárias.

## Renovação e duplicidade

A referência de idempotência é única por conexão. Repetir mesma ação/conteúdo devolve a operação existente. Reutilizar a chave com outro conteúdo retorna 409. O mesmo cliente/recurso não aceita outra alteração enquanto houver uma na fila/em execução. Resultado incerto bloqueia novas alterações na conexão até conferência.

`queued → running → succeeded / failed / reconciliation_required`.

`failed` significa que uma falha foi identificada sem presumir sucesso. Falhas ambíguas depois de transmitir uma alteração, HTTP inesperado, falta da regra de sucesso e interrupção do processo são `reconciliation_required`. Todas precisam de conferência; não há garantia de exactly-once no servidor remoto sem suporte dele.

`success_path` só comprova que a resposta obedeceu à regra aprovada. Essa versão não efetua conferência independente e universal de vencimento/saldo após toda alteração, pois a semântica e os endpoints reais ainda não são conhecidos. Faça essa validação na homologação do perfil.

## Confirmação de pagamento pelo ERP

`POST /api/v1/connections/{id}/payments/confirmed` recebe `reference`, `client_id`, `parameters`, `confirmed` e exige token `operate` ou `admin`. A referência gera uma chave de idempotência. É uma declaração autenticada do seu ERP: **não é um webhook bancário público nem uma verificação de pagamento Pix/Asaas**. O ERP deve verificar o pagamento antes de chamar. Mantenha o token restrito à conexão.

## Webhooks de saída

Configuração via `/api/v1/webhooks`. URL precisa estar na allowlist de hosts. Payload: `id`, `type`, `connection_id`, `data`, `created_at`. Cabeçalhos:

```text
X-Reseller-Event: evt_...
X-Reseller-Timestamp: unix_seconds
X-Reseller-Signature: sha256=HEX
```

Assinatura: HMAC-SHA256(secret, timestamp + "." + corpo HTTP ORIGINAL). Verifique janela de tempo, assinatura em comparação constante e deduplique pelo ID do evento. Até 8 tentativas com intervalo exponencial limitado a 1 hora; entrega ao menos uma vez. Não colocar segredos na URL.

## Importação

Postman v2/v2.1 e HAR são lidos localmente. Scripts, exemplos de resposta, cookies e cabeçalhos secretos não são executados/importados como sessão. Autenticação bearer/apikey declarada pode gerar uma sugestão de formato, nunca comprova compatibilidade. Valores de campos sensíveis viram templates de entrada. O operador precisa revisar e habilitar explicitamente cada ação.

Não há download autenticado da coleção online integrado. A coleção pública indicada pelo usuário não ficou legível na consulta desta entrega; não foi inventada uma documentação em seu lugar.
