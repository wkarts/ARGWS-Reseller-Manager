# Uso do modelo fornecido

Origem: `escrituracao-contabil-0.3.0-dev.9.1.zip`. O arquivo original foi preservado; a nova ferramenta foi criada em pasta independente e não reutiliza o banco antigo.

## Reaproveitado

- Padrão de distribuição: Python/FastAPI, SQLite, aplicação Windows gráfica e servidor Docker.
- Shell visual claro do portal (`src/portal/app.css`, adaptado) e vendor Vue local com licença preservada.
- Compilação de templates Vue com Node durante desenvolvimento, mantendo render pré-compilado sem eval no navegador.
- Classe de bandeja Windows nativa, adaptada para Reseller Manager.
- Ícone técnico do modelo reaproveitado provisoriamente. Não foi criada identidade visual definitiva.
- Abordagem de empacotamento PyInstaller e smoke contra processo real, reescrita para o novo domínio.

## Não levado para a nova ferramenta

Motor fiscal/contábil; SPED/XML/NF-e; Prosoft; planos de contas; partidas e lançamentos; livros e competências; conciliação contábil/documental; importadores fiscais; histórico e migrações do banco contábil; exports fiscais; relatórios; regras e rotas contábeis; dados de clientes anteriores; deploys/nomes de repositório e flows específicos da aplicação antiga.

O sistema de acesso do modelo (usuários, empresas, senhas e 2FA) não foi transportado inteiro: esta ferramenta usa tokens próprios com permissões por conexão. Não é uma migração de usuários do projeto contábil.

## Novo

Domínio de revendas, conectores por contratos, armazenamento protegido, autorizações por token, consultas/cache, fila idempotente, conciliação manual de resultados incertos, agendamentos, entrada de confirmação de pagamento pelo ERP, webhooks HMAC, WebSocket, importador Postman/HAR e testes sintéticos.

A versão é **0.1.0**, pois trata-se de outro produto. O número 0.3.0 do template não foi herdado como versão da nova ferramenta.
