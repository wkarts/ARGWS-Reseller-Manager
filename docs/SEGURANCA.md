# Segurança e limites

- Acesso somente com token de alta entropia gerado por `secrets`; banco guarda SHA-256 do token. O token inicial também fica em arquivo privado para primeiro acesso. Administrações posteriores podem emitir/revogar tokens; o último admin global não é revogável sem substituto.
- `admin`, `operate` e `read`, com restrição explícita por conexão em tokens não-admin. Não há usuários por senha/2FA na própria ferramenta nesta versão. O painel remoto mantém as regras dele.
- Credenciais, cookies, perfil e cache dos clientes são criptografados com Fernet. A chave fica junto aos dados para permitir execução portátil. Isso **não protege contra um invasor com acesso integral à mesma conta/pasta do servidor**. Use permissões de SO, volume criptografado e backup protegido. Em Windows, a pasta do usuário herda ACLs do perfil; valide ACLs ao selecionar outra pasta. Não há integração DPAPI/Vault externa nesta versão.
- A UI guarda apenas o token da própria API em `sessionStorage` durante a sessão do navegador; sair apaga-o. Tokens recém-gerados aparecem uma vez. Credenciais do painel não retornam pela API, não são copiadas para o armazenamento web e são limpas do formulário após salvar.
- Campos de clientes são explicitamente projetados, sem retorno indiscriminado do JSON/HTML bruto. Ao mapear índices, confirme que não está apontando para a coluna de senha.
- Logs de acesso HTTP estão desligados e logs das bibliotecas de rede são suprimidos para não registrar URLs com tokens. Erros remotos não retornam corpo bruto nem valores de validação Pydantic. Não registre a saída completa de comandos com tokens em terminais compartilhados.
- TLS do destino é verificado, proxy de ambiente ignorado e redirects/formulários externos bloqueados. Host exato deve estar na allowlist; IPs privados/reservados são recusados, exceto exceções administrativas explícitas.
- A checagem DNS ocorre antes de cada requisição, mas o cliente HTTP resolve o hostname novamente para conexão. **Não é proteção completa contra DNS rebinding em um host autorizado comprometido.** Restrinja também a saída por firewall/proxy de egress em ambientes sensíveis. Não adicione domínios arbitrários à allowlist.
- Login via navegador permite só a mesma origem e bloqueia recursos externos não autorizados. Isso pode impedir desafios/serviços externos legítimos; o produto não contorna CAPTCHA, 2FA ou bloqueios de terceiros.
- `Idempotency-Key` é local. Sem idempotência real do fornecedor não existe garantia de exactly-once ponta a ponta. Timeouts/resultado ambíguo bloqueiam novas alterações até conferência humana.
- O servidor aceita no máximo 4 MiB por corpo HTTP; respostas remotas limitadas a 8 MiB. O importador não executa scripts. Trate HAR como informação privada: pode conter dados pessoais fora dos campos conhecidos.
- Não há varredura de diretórios/endpoints, enumeração de contas ou execução automática de testes com custo. O operador configura apenas operações da conta autorizada.
- Não é uma aplicação multi-tenant/SaaS pública. Um administrador tem controle global; operadores são restritos por tokens/conexões. Não entregue token admin ao browser de um cliente final.
- Dados/auditoria/entregas acumulam sem expiração automática nesta versão. Planeje backup e retenção antes de uso prolongado; não apague registros de idempotência enquanto callbacks antigos ainda puderem chegar.
- O endpoint `/payments/confirmed` é para sistemas confiáveis autenticados. Não recebe webhooks anônimos de gateways e não valida transações financeiras por conta própria.

## Antes de produção

Valide o contrato real e termos do fornecedor, use conta de homologação, verifique cálculos de prazo/créditos/telas, valide criptografia/ACL/backup, exponha somente HTTPS, faça revisão das dependências e execute os builds Windows/Docker nativos. O software não foi homologado com o Servip2P nesta entrega.
