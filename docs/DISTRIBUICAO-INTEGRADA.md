# Distribuição integrada — Windows, Docker/Dockge e Releases

## Contrato de entrega

O pacote distribuído inclui Python/FastAPI, Playwright, seu driver e Chromium.
No Windows, extraia a pasta inteira do ZIP e execute `ResellerManager.exe`.
No Docker/Dockge, use `compose.yaml` e `.env` do ZIP de deploy com a imagem GHCR.
Não é necessário instalar Python, Node.js, Playwright, Chrome ou Chromium no host.
Docker Engine/Compose continuam sendo necessários para a modalidade container.

A aplicação não baixa dependências na primeira abertura nem durante o login.
As dependências são baixadas **no build**, incorporadas e verificadas antes da distribuição.
Para desenvolvimento pelo fonte, `scripts\start-windows.cmd` prepara o ambiente e o navegador automaticamente.
Isso não é o fluxo exigido de quem utiliza o binário pronto.

## Compatibilidade com instalações anteriores

Dados, chaves, sessões, tokens e perfis permanecem na mesma pasta.
Não apague `data` nem gere uma nova `master.key` durante a atualização.
O `.env` antigo pode ser mantido: `RESMAN_BROWSER_ENABLED=0` é legado e não bloqueia mais o recurso.
As imagens padrão (`latest`, `develop`, versão e SHA) incluem Chromium.
Tags/target `-browser` continuam disponíveis como compatibilidade, também completas.
A flag de build `-WithBrowser` continua aceita, mas não é necessária.

Os seletores/contratos de login do kOfficePanel continuam precisando de configuração real.
Ter Chromium embarcado não confirma a compatibilidade de endpoints desconhecidos nem contorna CAPTCHA/2FA.

## Verificação nativa

Antes de gerar o ZIP Windows, o build:

1. Empacota Chromium junto com o runtime PyInstaller.
2. Verifica PE x64 e a API HTTP do executável, fora do diretório de código-fonte.
3. Executa `ResellerManager.exe --browser-self-test --result arquivo.json` em pasta vazia.
4. Define um cache externo inexistente para provar que o executável usa o navegador embarcado.
5. Abre um documento local com rede bloqueada e só gera o pacote se o teste passar.

O container é testado pelo Compose de deploy real, sem montar código-fonte.
São conferidos healthcheck, autenticação, usuário não-root, persistência e renderização offline no Chromium.
Nenhum desses testes usa credenciais ou executa alterações no fornecedor.

## Release automática

A PR executa validações/builds, mas não publica GHCR/release.
Após push/merge em `main`, ou push de tag `vVERSION`, a mesma rodada executa:

```text
Testes Linux/Windows → imagens Docker + binário Windows → release
```

O publicador exige os três ZIPs (Windows, deploy padrão, alias deploy-browser),
seus checksums, a mesma versão/SHA e a confirmação de navegador embarcado/testado.
Os ZIPs de deploy apontam para a imagem `sha-...` exata; não dependem de `latest` móvel.
As imagens testadas são promovidas por digest para a tag numérica da versão.
A release permanece em rascunho até que todos os anexos estejam carregados e conferidos.

Uma versão já publicada para outro commit **não é movida nem substituída**.
Para a próxima release, incremente `VERSION` e a versão da aplicação de forma coerente.
Reexecutar uma publicação já concluída para o mesmo SHA não substitui seus anexos.
O `GITHUB_TOKEN` precisa de `contents: write` e `packages: write` somente nos jobs de publicação.
Não depende de PAT pessoal nem de novo workflow disparado pela tag criada pelo próprio token.

## Limites de comprovação

A presença do workflow não comprova um build concluído. Consulte o SHA e os resultados
no Actions e os anexos efetivamente publicados em Releases. O build nativo não pode ser
substituído por um teste simulado ou pela mera presença dos arquivos no fonte.
