# Conexões — edição, exclusão e autenticação (0.1.1)

Na tela Conexões, cada cartão oferece **Editar** e **Excluir conexão**. A atualização preserva o banco e a chave da instalação; não é necessário recriar as conexões existentes.

## Editar

Altere nome, endereço, modo de autenticação e configuração de login/token. Usuário, senha e token em branco são preservados. Para apagar um valor salvo, marque sua opção explícita em Configuração de login e token. Valores atuais nunca são retornados ao navegador.

Ao mudar o endereço do fornecedor, credenciais antigas são removidas: informe as credenciais do novo destino. Isso impede enviar automaticamente a senha de um provedor para outro host.

Uma edição invalida a sessão, limpa o cache de clientes, cancela alterações ainda na fila e pausa agendamentos. Operações em execução ou exigindo conferência impedem a edição. O histórico é preservado. Edições concorrentes retornam 409 em vez de sobrescrever dados de outra aba.

## Excluir completamente do Reseller Manager

A tela apresenta o impacto e exige digitar o nome exato. Remove conexão, credenciais criptografadas, sessão, perfil, cache, operações, agendamentos, eventos e entregas de webhook vinculadas. Tokens restritos são ajustados; os que ficam sem conexão são revogados, nunca convertidos em acesso global. Conexões e webhooks globais de outras contas permanecem intactos.

Uma operação em execução impede a exclusão. Operações incertas exigem confirmação adicional: apagar o histórico não desfaz uma renovação ou cobrança no fornecedor. Somente um registro agregado e anônimo da exclusão permanece para auditoria.

A exclusão é local, não chama endpoints de exclusão do fornecedor. Não remove backups externos nem promete apagamento forense dos blocos de armazenamento/SQLite.

## Login

O modo navegador usa o Chromium já integrado ao Windows e ao Docker. Não exige instalação adicional. Nomes de campos vazios ativam a identificação de um único formulário de senha. Um formulário ambíguo não recebe credenciais por tentativa.

O seletor `success_selector` é opcional quando a consulta autenticada confirma JSON válido ou a página pós-login apresenta uma evidência de sessão. Sem confirmação positiva, HTTP 200, um cookie ou uma mudança de URL sozinhos não são aceitos como sucesso. O status `session_received` indica login confirmado pela página, mas consulta de clientes ainda pendente; `authenticated` exige a consulta JSON.

**Inspecionar formulário** faz uma leitura sem enviar senha. **Aplicar campos detectados** preenche o editor ou salva a configuração local; valores de CSRF e cookies não são exibidos. Campos ocultos são coletados a cada tentativa, não fixados no código. São tratados redirecionamentos HTTP e redirecionamentos HTML literais, limitados à mesma origem; a senha nunca é reenviada automaticamente.

A inspeção pública do Servip2P em 06/11/2026 encontrou `form#form-login`, POST na própria página, campos `username`, `password`, `try_login` e `csrf_token`. Isso comprova o formato público do formulário, não uma autenticação com conta real. A referência de leitura `/clients/api/?get_clients` foi fornecida pelo proprietário; a checagem automática não habilita endpoints de alteração nem infere colunas que possam conter senhas.

O cliente HTTP usa certificados confiáveis do sistema e certifi, preservando a validação TLS. Falhas de certificado, conexão e timeout têm códigos separados e não expõem credenciais. CAPTCHA e autenticação adicional não são contornados. Em Windows, o navegador roda em um loop com suporte a subprocessos, separado do loop da API.

## API local

- `PATCH /api/v1/connections/{id}`: `revision`, campos editados, credenciais parciais, `clear_credentials`, `login` e `token_auth`.
- `GET /api/v1/connections/{id}/deletion-preview`: impacto da exclusão local.
- `DELETE /api/v1/connections/{id}`: `revision`, `confirm_name` e, quando necessário, `acknowledge_uncertain`.

As três rotas exigem administrador global. A rota antiga PUT de substituição integral de credenciais permanece para compatibilidade; a interface usa PATCH para preservar campos vazios.

## Validação

Testes automatizados incluem isolamento entre contas, revisões, permissões, exclusão com dependências, proteção de tokens, campos ocultos, redirecionamentos, falhas TLS/rede e navegador real contra servidor sintético local. Os testes de navegador não enviam credenciais ao Servip2P. O login com a conta real e os contratos comerciais continuam sujeitos à homologação na instalação do usuário.
