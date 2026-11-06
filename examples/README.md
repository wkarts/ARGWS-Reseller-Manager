# Exemplos da API própria

- `reseller-manager.openapi.json`: exportação do aplicativo entregue.
- `reseller-manager.postman_collection.json`: 20 requisições, sem credenciais reais e sem scripts automáticos. Importe no Postman/cliente compatível, configure `base_url` e `api_token` localmente.
- Não confundir com a coleção pública do kOfficePanel fornecida na conversa. O conteúdo daquela coleção não foi extraído nem substituído por endpoints de outro produto.
- Não use Collection Runner para executar todas as requisições: há ações de autenticação, criação, cancelamento e alteração.
- As operações com custo possuem `confirmed: false` e chave de idempotência vazia por padrão. Revise o perfil, preencha os dados e autorize somente a requisição desejada.
- Os valores `plan_id`, `client_id` e afins são parâmetros do seu contrato; precisam ser traduzidos para a API real no perfil.
- Regenere estes arquivos com `python scripts/export_reference.py` após alterar a API.
