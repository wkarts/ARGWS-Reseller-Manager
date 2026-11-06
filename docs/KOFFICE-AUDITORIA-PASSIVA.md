# Inventário passivo — kOfficePanel v4.6.9 PREMIUM / Servip2P

**Origem:** leitura de duas abas já autenticadas de `https://servip2p.com/clients/`, autorizada pelo titular, em 06/11/2026. Nenhuma ação foi executada no fornecedor.

**Limitação da auditoria:** o acesso aqui permite ler as abas abertas, mas não navegar/inspecionar automaticamente todas as áreas privadas nem capturar XHR. O inventário abaixo é de **navegação confirmada na interface**, não de endpoints homologados para uma API de revenda.

## Páginas observadas

| Área | Caminho exibido na interface | Risco |
|---|---|---|
| Clientes IPTV | `/clients/` | Consulta da lista atual |
| Formulário de novo cliente | `/clients/create/` | A página existe; **não enviar formulário** |
| Editar cliente | `/clients/edit/{id}/` | Não acessar para salvar sem autorização |
| Clientes P2P | `/p2p/` | Consulta da lista |
| Cadastro P2P | `/p2p/create/` | Não enviar |
| Teste P2P | `/test/p2p/` | Não criar teste |
| Teste IPTV | `/test/` | Não criar teste |
| Revendedores | `/resellers/` | Consulta da lista |
| Novo revendedor | `/resellers/create/` | Não enviar |
| Bloqueados por recarga | `/resellers/no_recharge/` | Consulta da lista |
| Conexões ativas | `/connections/` | Consultar com prudência |
| Logs de login | `/logs/login/` | Consulta auditável |
| Logs de vendas | `/logs/sales/` | Consulta auditável |
| Logs de créditos | `/logs/credits/` | Consulta auditável |
| Logs de clientes | `/logs/clients/` | Consulta auditável |
| Logs de revendedores | `/logs/resellers/` | Consulta auditável |

**Rota deliberadamente NÃO testada:** `/test/fast_client/1`. Na interface, ela está ligada à criação de teste/ativação potencialmente cobrada. Não deduza ausência de efeito colateral a partir do método HTTP GET.

## Listagem IPTV observada

- Controles de paginação: 10, 25, 50 e 100 registros; filtros por master e situação.
- Estados oferecidos: ativo, desativado, expirado, teste e cliente.
- Busca por ID, login, senha, data de criação, vencimento, master e notas.
- A tabela tem ID, login, senha, datas, master, conexões, notas e status.
- O campo de senha de cliente **não deve ser exportado** pelo conector. IDs e dados pessoais foram omitidos deste inventário.
- Em captura Network anterior foi observada a URL `/clients/api/?get_clients` e resposta JSON no formato DataTables. Método, parâmetros e autenticação dessa chamada ainda exigem reprodução exata.

## Fluxo seguro de homologação

1. Para cada conexão R2/R3, registrar `session_received` após login é apenas **sessão da interface recebida**; ainda não comprova autenticação de endpoint JSON.
2. Importar documentos Postman e HAR **sanitizados** (sem cookies, senhas, tokens e respostas pessoais), sem executar scripts ou chamadas.
3. Associar as requisições às ações do catálogo, mantendo `verified=false` até confirmar método, parâmetros e efeitos.
4. Executar a **matriz de dry-run local**, que não se conecta ao fornecedor, e corrigir contratos e campos faltantes.
5. Somente consultas de leitura explicitamente validadas podem ser testadas com o fornecedor; limitar tamanho, paginação e taxa. **Não testar mutações.**
6. Para criação, renovação, migração, telas, créditos e pagamentos, validar esquema e regra de negócio por documentação/capturas autorizadas; simular sobre dados fictícios sem encaminhar POST, PUT, PATCH ou DELETE ao fornecedor.
7. Não promover ações comerciais para automação sem homologação separada e autorização explícita para teste real.

## Endpoints do dry-run próprio (sem chamadas externas)

```http
GET /api/v1/connections/{connection_id}/dry-run
POST /api/v1/connections/{connection_id}/dry-run/{action}
Content-Type: application/json
Authorization: Bearer TOKEN_LOCAL_ADMIN
```

Exemplo de corpo, apenas na API local:

```json
{"parameters":{"client_id":"EXEMPLO_FICTICIO","plan_id":"PLANO_FICTICIO"}}
```

Resposta inclui `result: "NOT_EXECUTED"`, `upstream_request_sent: false`, `credits_charged: false`, problemas do contrato e apenas **nomes** de campos. Não revela valores, URLs sensíveis, cookies, senha ou token. O dry-run não enfileira operações, não agenda e não modifica dados.

Acesse a interface local em `http://127.0.0.1:48190/audit` após autenticar no Reseller Manager. O inventário de navegação é referência de páginas, não autorização para executar chamadas remotas.
