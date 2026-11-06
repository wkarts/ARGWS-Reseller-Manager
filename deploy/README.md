# Reseller Manager — deploy GHCR / Docker / Dockge

Esta pasta é um deploy independente. **Não precisa do código-fonte, de Node.js,
de Python no host nem de Dockerfile.** A aplicação roda na imagem Linux x64
publicada no GHCR; somente Docker Engine e Compose v2 são necessários no servidor.
O pacote de deploy não contém a imagem: publique-a pelo workflow antes do primeiro pull.

## Arquivos da stack

```text
reseller-manager/
  compose.yaml
  .env                 # gerado no ZIP de deploy, com configurações públicas
  .env.example
  README.md
  data/                # criado no primeiro início; contém dados e segredos reais
```

No repositório, `.env.example` é o modelo; o `.env` real não é versionado.
O gerador do ZIP cria `.env` com valores públicos a partir do modelo, nunca a partir
de um `.env` de instalação. A pasta `data` não entra em nenhum pacote de distribuição.

## Primeiro deploy via terminal

Extraia o ZIP de deploy em uma pasta própria. O ZIP já inclui `.env`.
Ao usar diretamente esta pasta do repositório, crie-o **apenas na primeira instalação**:

```sh
cp .env.example .env
```

Edite `.env`, principalmente `RESMAN_IMAGE`, `RESMAN_BIND`, `RESMAN_PORT`,
`RESMAN_ALLOWED_HOSTS` e `RESMAN_PUBLIC_ORIGIN`.

```sh
docker compose config --quiet
docker compose pull
docker compose up -d
docker compose ps -a
docker compose logs --tail=100 api
docker compose exec -T api cat /data/admin.token
```

`RESMAN_BIND=0.0.0.0` disponibiliza a porta na rede. Com os valores do pacote,
abra `http://IP_DO_SERVIDOR:48190`. Limite o acesso no firewall e use HTTPS no proxy
para acesso externo. Para um proxy no mesmo host, prefira `RESMAN_BIND=127.0.0.1`
e informe a origem HTTPS exata em `RESMAN_PUBLIC_ORIGIN`, sem barra final.
O deploy não instala TLS automaticamente nem reserva as portas 80/443.
A API exige token; o token mostrado é da sua instalação, não do fornecedor.

## Dockge

Crie uma stack `reseller-manager`, copie o conteúdo de `compose.yaml` para o editor
e o conteúdo do `.env` do pacote para o editor de variáveis. Faça o deploy.
Alternativamente, coloque os arquivos na pasta de stacks configurada no Dockge,
por exemplo `/opt/stacks/reseller-manager/`, e use **Scan Stacks Folder**.
Não altere a localização de uma stack existente sem mover seu `data` com segurança.
Não há `build:`, caminhos para código-fonte ou arquivos externos exigidos pela stack.
Não fixe `container_name`: o nome da stack permite múltiplas instalações isoladas.

O serviço `data-init` é transitório: `Exited (0)` significa conclusão normal.
Ele prepara as permissões de `./data`; a API roda como UID/GID 10001, não como root.
O healthcheck real de `/health` permanece ativo. Um init com erro impede o início da API.

## Imagens e canais

O workflow usa automaticamente o proprietário/repositório em letras minúsculas.
Para este repositório, a imagem é `ghcr.io/wkarts/argws-reseller-manager`.

| Tag | Origem |
|---|---|
| `latest` | main estável ou tag estável `vVERSION`, após testes |
| `develop` | branch develop, após testes |
| `0.1.0` | tag Git `v0.1.0`, com VERSION correspondente |
| `sha-<12 caracteres>` | referência do commit efetivamente compilado |
| `latest-browser`, `develop-browser`, `0.1.0-browser` | aliases de compatibilidade; a imagem padrão também inclui Chromium |

Builds prerelease não atualizam `latest`. Pull requests geram validações e artefatos,
mas **não publicam imagens**. Os pacotes de deploy gerados em PR podem referenciar
uma imagem ainda não publicada; não os trate como deploy de produção disponível.
Para reproduzir uma instalação, prefira uma tag de versão ou digest já publicado.
`latest` e `develop` são canais móveis.

Playwright, Chromium e bibliotecas Linux já estão incluídos na imagem padrão. Não é necessário selecionar outra variante, instalar pacotes nem configurar `RESMAN_BROWSER_ENABLED`. A variável legada é ignorada, inclusive quando um `.env` anterior contém valor 0. Não há download de navegador durante a inicialização.
O browser é headless no Docker; desafios que exigem interação precisam ser tratados
pelo fluxo autorizado, nunca contornados automaticamente.

## GHCR privado / primeira publicação

A visibilidade pública do repositório não garante que o pacote GHCR seja público.
Configure a visibilidade do pacote ou autentique o host/Dockge no GHCR com uma
credencial autorizada para leitura. Não coloque essa credencial no compose nem
nas variáveis da aplicação. O workflow publica usando `GITHUB_TOKEN` e `packages: write`.
A publicação pode depender das políticas da conta/organização e permissões do pacote.

## Atualizar e preservar dados

```sh
docker compose pull
docker compose up -d
```

Não substitua seu `.env` por um exemplo a cada atualização. Faça backup da pasta
`./data` inteira com a aplicação parada; banco, `master.key` e credenciais criptografadas
precisam permanecer juntos. Não exclua a pasta de dados para atualizar a imagem.
Para voltar uma versão, restaure uma imagem compatível e, quando necessário, o backup
correspondente. Não é garantido downgrade de banco entre versões futuras.

## Desenvolvimento local e Windows

O compose na **raiz do código-fonte** continua sendo a opção para build local:

```sh
cp .env.example .env
docker compose up -d --build
```

No Windows, o código-fonte mantém `scripts\start-windows.cmd` (Python 3.12 x64).
O pacote Windows gerado pelo workflow inclui `ResellerManager.exe`: extraia a pasta
inteira e execute. Não exige Docker, Node.js ou Python instalados na máquina de uso.
Modo servidor: `ResellerManager.exe --server --host 127.0.0.1 --port 48190 --data C:\ResellerData`.
O binário usa os mesmos módulos FastAPI da imagem Docker; instâncias distintas
mantêm dados independentes e não devem compartilhar um SQLite simultaneamente.

O executável Windows e os ZIPs de deploy ficam em **Actions → Validate → Artifacts**,
depois que os respectivos jobs passam. Os workflows também podem ser executados
manualmente. Após push/merge em `main` (ou tag `vVERSION`), a release é publicada automaticamente somente depois de todos os testes e builds nativos. Os ZIPs e checksums ficam também em **Releases**. A release inicial usa VERSION=0.1.0; novas versões exigem incremento explícito de VERSION, sem substituir releases anteriores.

## Limites de validação

Existência do compose/workflow não comprova uma imagem publicada nem um binário gerado.
O CI prepara teste real da imagem, persistência após recriação, usuário não-root e,
em ambas as tags, abertura de Chromium sem conectar ao fornecedor. O Windows
valida PE x64, API e Chromium a partir do executável nativo, fora da pasta-fonte e com cache externo vazio. Consulte os resultados da execução.
A homologação dos endpoints reais do kOfficePanel continua separada.

Referências de operação: documentação oficial de [Docker Compose](https://docs.docker.com/compose/),
[Dockge](https://github.com/louislam/dockge) e [GHCR](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).
