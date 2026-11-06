# Operação e distribuição

## Pastas e backup

`data/reseller.sqlite3`: banco; `data/master.key`: chave de criptografia; `data/admin.token`: primeiro acesso; `data/logs/`: logs rotativos; `data/instance.lock`: trava de processo.

Faça backup da pasta inteira **com serviço parado**. Se optar por backup online, use backup consistente SQLite, não copie apenas o arquivo principal enquanto WAL estiver ativo. Banco sem `master.key` não será aberto. Não compartilhe a pasta por SMB para múltiplas instâncias.

A ausência da chave com banco existente gera erro, não uma substituição silenciosa. O aplicativo não lê nem migra bancos do projeto contábil original.

## Windows

Fonte: Python 3.12 x64 ou 3.13 x64. Build documentado/CI: 3.12 x64. O EXE usa a mesma API da versão Docker. Janela: abrir painel, copiar token, iniciar/parar serviço, selecionar pasta/porta e abrir os dados. Ao fechar, fica na bandeja quando o ícone nativo está disponível; para parar de fato, escolha Sair.

O padrão desktop é 127.0.0.1:48190. O modo `--server` aceita `--host`, `--port`, `--data`. Não há instalador MSI, assinatura Authenticode, serviço Windows instalado automaticamente nem atualização automática nesta primeira versão. Pode ser colocado na inicialização do usuário por uma política local; não cria registro de autostart sem autorização.

Todos os pacotes Windows incluem Playwright e Chromium. `-WithBrowser` permanece aceito por compatibilidade, mas não é necessário. O executável usa o navegador embarcado, não Chrome/Edge do usuário nem cache externo, e não baixa dependências na primeira execução. Para exibir a janela do navegador no Windows, `RESMAN_BROWSER_HEADLESS=0`; headless é o padrão.

## Docker

`docker compose up -d --build` prepara o volume ./data e inicia a API não-root. `docker compose down` para sem apagar os dados. Não use `--scale api=2` e não configure múltiplos workers Uvicorn.

Configurações:

| Variável | Padrão / significado |
|---|---|
| RESMAN_HOST / PORT | 127.0.0.1 / 48190 na fonte; 0.0.0.0 / 48190 dentro do container. |
| RESMAN_DATA | ./data na fonte; /data no container. |
| RESMAN_ALLOWED_HOSTS | servip2p.com; hosts exatos autorizados para painel e webhooks. |
| RESMAN_PRIVATE_HOSTS | Vazio. Exceções privadas explícitas; também devem estar na allowlist. |
| RESMAN_PUBLIC_ORIGIN | Origem HTTPS pública da sua própria API quando houver proxy. |
| RESMAN_BROWSER_ENABLED | Legada e ignorada: Chromium está incluído em todas as distribuições, inclusive ao atualizar `.env` antigo com valor 0. |
| RESMAN_BROWSER_HEADLESS | 1 por padrão; Windows permite 0 para login assistido local. |

O target Docker `runtime` e as tags padrão incluem Chromium e suas bibliotecas Linux. O target/tag `browser` permanece como alias de compatibilidade. Os downloads de dependências acontecem na construção da imagem, nunca no servidor em execução. O pacote não fornece acesso remoto ao desktop do navegador do container; desafios interativos devem ser tratados pelo acesso autorizado, sem contornar restrições.

Para exposição pública, use proxy HTTPS com suporte ao upgrade de `/ws/events`; não há TLS automático incluído. Configure `RESMAN_PUBLIC_ORIGIN` com a URL externa exata. A API não habilita CORS irrestrito nem confia automaticamente em X-Forwarded-*.

## Fila e automação

SQLite WAL persiste operações, agendamentos e eventos. Um único worker processa alterações de forma serial nesta versão. Isso reduz risco de concorrência, mas limita throughput; múltiplas réplicas/Redis distribuído são evolução futura, não promessa de suporte atual.

Agendamentos usam instantes UTC e a UI converte do horário local. Repetição é por **dias corridos**, não meses de calendário. Um agendamento vencido enquanto o serviço estava parado executa uma vez ao voltar; não cobra em lote todas as ocorrências perdidas. Após sucesso, avança para a próxima data futura. Falha/incerteza pausa a recorrência. Alterar perfil ou credenciais também exige nova autorização: os agendamentos da revisão anterior são pausados.

Uma mudança de perfil invalida sessões. Uma operação já na fila preserva a revisão esperada e falha antes de transmitir se o contrato mudou. Operações interrompidas que já estavam executando vão para conferência na reinicialização.

Pausar agendamento não desfaz uma operação que já entrou na fila; cancele-a separadamente antes de começar. Não há retomada automática de agendamento pausado: crie uma nova ordem após conferir a causa.

## Estado da conexão

- `not_connected`: ainda não autenticada ou sessão descartada.
- `session_received`: cookies obtidos, ainda sem consulta confirmada.
- `authenticated`: última consulta JSON satisfez o contrato; não garante sessão eterna.
- `expired`: painel solicitou autenticação.
- `requires_action`: login navegador/formulário depende de intervenção ou configuração.

## CI

`Validate`: testes Linux e Windows, frontend e smoke da API. Em seguida, builds nativos Docker/Windows com abertura real do Chromium integrado. A release é criada após push/merge em `main` ou tag `vVERSION`, somente se todas as etapas passarem. PR não publica imagens/releases. ZIP Windows, deploy `compose.yaml`/`.env` e checksums são anexados; imagens recebem tags de versão sem recompilar. Versão já publicada em outro SHA não é sobrescrita. Não faz merge nem deploy no servidor. Veja [distribuição integrada](DISTRIBUICAO-INTEGRADA.md).
