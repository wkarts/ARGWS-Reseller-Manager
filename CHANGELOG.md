# Changelog

## 0.1.3

- Corrige a leitura de respostas HTTP comprimidas (gzip/deflate/br) no conector; evita HTTP 502 por dupla descompressão durante login por formulário ou verificação da sessão do navegador.
- Preserva cookies, mantém limite sobre conteúdo descomprimido e corrige cabeçalhos de comprimento e codificação ao reconstruir respostas.
- Acrescenta regressões de login, consulta autenticada e limite de tamanho. Mantém proteção CSP, persistência e as distribuições Windows/Docker/Dockge.


## 0.1.2

- Corrige a publicação de releases: usa o ID retornado ao criar o rascunho e também no upload direto dos anexos, sem consultas imediatas por tag sujeitas a atraso de propagação.
- Mantém validação de SHA/versão, integridade dos seis anexos e publicação somente após build Windows e Docker aprovados.
- Adiciona testes para listagem de rascunhos desatualizada e rejeição de metadados inválidos, sem alterar funcionalidades do Reseller Manager.

## 0.1.1

- Edição de conexões e credenciais sem apagar campos vazios.
- Exclusão local completa, com confirmação, revisão e isolamento.
- Login com descoberta de formulário/CSRF, redirecionamentos HTML e diagnóstico TLS/rede.
- Navegador sem bloqueio por success_selector vazio; confirmação positiva de sessão.
- Testes reais de navegador em Windows/Linux; Chromium distribuído preservado.

## 0.1.0 — 2026-11-06

Primeira implementação do Reseller Manager baseada na estrutura do template fornecido. API FastAPI, UI Vue local, executor HTTP por contrato, autenticação por token/formulário e navegador opcional, fila SQLite, idempotência, proteção de segredos, agendamentos, eventos, Postman/HAR, Docker e build Windows x64.

Perfil Servip2P deliberadamente não homologado. Não foram transportados módulos de escrituração. Nenhuma alteração foi feita no painel real.

## Correção de distribuição da PR #1

- Restaurado deploy independente GHCR/Dockge com compose.yaml, modelo .env e persistência ./data.
- Mantido o compose de build local e o executável Windows x64; variante browser recebe defaults próprios no pacote.
- Workflows constroem e testam imagens runtime/browser e Windows após a validação, publicando GHCR somente em push autorizado.
- Pacote de deploy com .env público, checksum e metadados; nenhum dado ou segredo de instalação é empacotado.
- Correção LF/CRLF do frontend preservada, com testes que continuam rejeitando artefatos realmente desatualizados.

## 0.1.0 — distribuição integrada e release automática

- Playwright/Chromium incluídos no Docker padrão e em todo pacote Windows x64, sem downloads na máquina de uso.
- `RESMAN_BROWSER_ENABLED` deixa de ser opt-in: `.env` antigo com valor 0 não bloqueia a atualização.
- Smoke offline do Chromium executado pelo binário congelado, com cache externo vazio; ambos os targets Docker testam o navegador.
- Releases após validação completa em main/tags, com ZIP Windows, deploys, SHA-256 e promoção por digest da imagem testada.
- Guarda de versão/SHA impede sobrescrever uma release já publicada; rascunho só é publicado após upload completo.
- Mantidos autenticação, contratos, credenciais, persistência, healthchecks, Docker/Dockge e modo Windows local.
