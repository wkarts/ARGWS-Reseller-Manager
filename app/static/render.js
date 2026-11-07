/* Template pré-compilado; não requer eval ou CDN. */
var _Vue=Vue;var ResellerRender=function render(_ctx, _cache) {
  with (_ctx) {
    const { createElementVNode: _createElementVNode, createTextVNode: _createTextVNode, vModelText: _vModelText, withDirectives: _withDirectives, toDisplayString: _toDisplayString, openBlock: _openBlock, createElementBlock: _createElementBlock, createCommentVNode: _createCommentVNode, withModifiers: _withModifiers, renderList: _renderList, Fragment: _Fragment, normalizeClass: _normalizeClass, vModelSelect: _vModelSelect, vShow: _vShow, vModelCheckbox: _vModelCheckbox, withKeys: _withKeys } = _Vue

    return (_openBlock(), _createElementBlock("div", null, [(!authenticated)
      ? (_openBlock(), _createElementBlock("div", {
          key: 0,
          class: "auth-layout"
        }, [_createElementVNode("section", { class: "auth-intro" }, [_createElementVNode("div", { class: "brand" }, [_createElementVNode("div", { class: "monogram" }, "RM"), _createElementVNode("strong", null, [_createTextVNode("Reseller Manager"), _createElementVNode("span", null, "GESTÃO DE REVENDAS")])]), _createElementVNode("div", { class: "auth-copy" }, [
          _createElementVNode("p", { class: "eyebrow" }, "SUA OPERAÇÃO, EM UM SÓ LUGAR"),
          _createElementVNode("h1", null, [_createTextVNode("Conecte. Gerencie."), _createElementVNode("br"), _createTextVNode("Renove com controle.")]),
          _createElementVNode("p", null, "Uma API própria para integrar sua carteira, organizar renovações e acompanhar cada operação."),
          _createElementVNode("div", { class: "auth-feature" }, "Sessões protegidas · Histórico persistente · Contratos verificáveis")
        ]), _createElementVNode("footer", null, "WWSoftware’s · Wallace Kleiton · v0.1.5")]), _createElementVNode("section", { class: "auth-panel" }, [_createElementVNode("form", {
          class: "auth-form",
          onSubmit: _withModifiers(login, ["prevent"])
        }, [
          _createElementVNode("p", { class: "eyebrow" }, "ACESSO AO AMBIENTE"),
          _createElementVNode("h2", null, "Bem-vindo ao seu painel"),
          _createElementVNode("p", { class: "muted" }, [_createTextVNode("Entre com o token do "), _createElementVNode("strong", null, "Reseller Manager"), _createTextVNode(". O token do kOfficePanel será cadastrado depois, na conexão.")]),
          _createElementVNode("label", { class: "field" }, [_createTextVNode("Token desta instalação"), _withDirectives(_createElementVNode("input", {
            type: "password",
            "onUpdate:modelValue": $event => ((loginToken) = $event),
            autocomplete: "off",
            required: "",
            placeholder: "Cole o token de acesso"
          }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, loginToken]])]),
          _createElementVNode("button", {
            class: "btn primary full",
            disabled: busy
          }, "Entrar no ambiente →", 8, ["disabled"]),
          _createElementVNode("div", { class: "notice spaced" }, [_createElementVNode("strong", null, "Primeiro acesso"), _createElementVNode("p", null, [
            _createTextVNode("Windows: botão “Copiar token” na janela do aplicativo."),
            _createElementVNode("br"),
            _createTextVNode("Docker/código-fonte: arquivo "),
            _createElementVNode("code", null, "data/admin.token"),
            _createTextVNode("."),
            _createElementVNode("br"),
            _createTextVNode("Nenhuma senha padrão é distribuída.")
          ])]),
          error
            ? (_openBlock(), _createElementBlock("p", {
                key: 0,
                class: "feedback error"
              }, _toDisplayString(error), 1))
            : _createCommentVNode("", true),
          _createElementVNode("a", {
            class: "link-button spaced",
            href: "/docs",
            target: "_blank",
            rel: "noopener"
          }, "Documentação da API ↗")
        ], 40, ["onSubmit"])])]))
      : (_openBlock(), _createElementBlock("div", { key: 1 }, [mobileMenu
          ? (_openBlock(), _createElementBlock("button", {
              key: 0,
              class: "sidebar-shade",
              onClick: $event => (mobileMenu=false),
              "aria-label": "Fechar navegação"
            }, null, 8, ["onClick"]))
          : _createCommentVNode("", true), _createElementVNode("aside", { class: _normalizeClass(["sidebar", {visible:mobileMenu}]) }, [_createElementVNode("div", { class: "brand" }, [_createElementVNode("div", { class: "monogram small-mark" }, "RM"), _createElementVNode("strong", null, [_createTextVNode("Reseller"), _createElementVNode("span", null, "MANAGER")])]), _createElementVNode("div", { class: "sidebar-scroll" }, [
          _createElementVNode("p", { class: "nav-label" }, "OPERAÇÃO"),
          _createElementVNode("nav", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(navigation, (item) => {
            return (_openBlock(), _createElementBlock("a", {
              key: item.id,
              href: '#'+item.id,
              class: _normalizeClass({active:page===item.id}),
              onClick: _withModifiers($event => (navigate(item.id)), ["prevent"])
            }, [_createElementVNode("span", { class: "nav-icon" }, _toDisplayString(item.icon), 1), _createTextVNode(_toDisplayString(item.title), 1)], 10, ["href", "onClick"]))
          }), 128))]),
          _createElementVNode("p", { class: "nav-label spaced" }, "AMBIENTE"),
          _createElementVNode("div", { class: "nav-note" }, [
            _createElementVNode("span", { class: _normalizeClass(['signal',socketOnline?'online':'']) }, null, 2),
            _createTextVNode(_toDisplayString(socketOnline?'Eventos em tempo real':'Reconectando eventos'), 1),
            _createElementVNode("br"),
            _createElementVNode("small", null, "v0.1.5 · " + _toDisplayString(user.scope), 1)
          ])
        ]), _createElementVNode("div", { class: "sidebar-footer" }, [_createElementVNode("span", null, "WWSoftware’s"), _createElementVNode("small", null, "Integrações sob seu controle")])], 2), _createElementVNode("div", { class: "main-area" }, [_createElementVNode("header", { class: "topbar" }, [_createElementVNode("div", { class: "actions" }, [_createElementVNode("button", {
          class: "icon-button mobile-menu",
          onClick: $event => (mobileMenu=!mobileMenu),
          "aria-label": "Abrir menu"
        }, "☰", 8, ["onClick"]), _createElementVNode("span", { class: "muted small" }, "CONEXÃO ATIVA"), _withDirectives(_createElementVNode("select", {
          class: "connection-select",
          "onUpdate:modelValue": $event => ((connectionId) = $event),
          onChange: changeConnection
        }, [_createElementVNode("option", { value: "" }, "Selecione uma conexão"), (_openBlock(true), _createElementBlock(_Fragment, null, _renderList(connections, (c) => {
          return (_openBlock(), _createElementBlock("option", { value: c.id }, _toDisplayString(c.name), 9, ["value"]))
        }), 256))], 40, ["onUpdate:modelValue", "onChange"]), [[_vModelSelect, connectionId]])]), _createElementVNode("div", { class: "actions" }, [_createElementVNode("span", { class: "badge" }, _toDisplayString(user.name), 1), _createElementVNode("button", {
          class: "link-button",
          onClick: logout
        }, "Sair", 8, ["onClick"])])]), _createElementVNode("main", null, [
          _createElementVNode("div", { class: "page-heading" }, [_createElementVNode("div", null, [_createElementVNode("p", { class: "eyebrow" }, "CENTRAL DE REVENDAS"), _createElementVNode("h1", null, _toDisplayString(pageTitle), 1), _createElementVNode("p", { class: "muted" }, _toDisplayString(pageDescription), 1)]), _createElementVNode("button", {
            class: "btn secondary",
            onClick: reload,
            disabled: busy
          }, "↻ Atualizar", 8, ["onClick", "disabled"])]),
          error
            ? (_openBlock(), _createElementBlock("div", {
                key: 0,
                class: "feedback error",
                role: "alert"
              }, [_createElementVNode("span", null, _toDisplayString(error), 1), _createElementVNode("button", {
                onClick: $event => (error=''),
                "aria-label": "Fechar aviso"
              }, "×", 8, ["onClick"])]))
            : _createCommentVNode("", true),
          notice
            ? (_openBlock(), _createElementBlock("div", {
                key: 1,
                class: "feedback success",
                role: "status"
              }, [_createElementVNode("span", null, _toDisplayString(notice), 1), _createElementVNode("button", {
                onClick: $event => (notice=''),
                "aria-label": "Fechar mensagem"
              }, "×", 8, ["onClick"])]))
            : _createCommentVNode("", true),
          busy
            ? (_openBlock(), _createElementBlock("div", {
                key: 2,
                class: "progress-line",
                "aria-label": "Processando"
              }))
            : _createCommentVNode("", true),
          _withDirectives(_createElementVNode("section", null, [
            _createElementVNode("div", { class: "welcome-banner" }, [_createElementVNode("div", null, [_createElementVNode("p", { class: "eyebrow" }, "CONTROLE ANTES DA AUTOMAÇÃO"), _createElementVNode("h2", null, "Sua central de operações"), _createElementVNode("p", null, "Cadastre sua conexão, valide os contratos e acompanhe cada solicitação até a confirmação.")]), _createElementVNode("div", { class: "banner-mark" }, "RM")]),
            _createElementVNode("div", { class: "stats" }, [
              _createElementVNode("article", { class: "stat-card" }, [_createElementVNode("small", null, "CONEXÕES CADASTRADAS"), _createElementVNode("strong", null, _toDisplayString(connections.length), 1), _createElementVNode("p", null, "Ambientes isolados")]),
              _createElementVNode("article", { class: "stat-card" }, [_createElementVNode("small", null, "NA FILA / EXECUTANDO"), _createElementVNode("strong", null, _toDisplayString(pendingCount), 1), _createElementVNode("p", null, "Últimas 100 operações")]),
              _createElementVNode("article", { class: "stat-card" }, [_createElementVNode("small", null, "EXIGEM CONFERÊNCIA"), _createElementVNode("strong", null, _toDisplayString(uncertainCount), 1), _createElementVNode("p", null, "Sem repetição automática")]),
              _createElementVNode("article", { class: "stat-card" }, [_createElementVNode("small", null, "AGENDAMENTOS"), _createElementVNode("strong", null, _toDisplayString(schedules.length), 1), _createElementVNode("p", null, "Ordens explícitas de renovação")])
            ]),
            _createElementVNode("div", { class: "dashboard-grid" }, [_createElementVNode("section", { class: "panel" }, [_createElementVNode("header", { class: "panel-header" }, [_createElementVNode("div", null, [_createElementVNode("h2", null, "Atividade recente"), _createElementVNode("p", null, "Eventos da sua API, sem expor credenciais.")]), _createElementVNode("span", { class: "badge" }, _toDisplayString(socketOnline?'Ao vivo':'Histórico'), 1)]), (!events.length)
              ? (_openBlock(), _createElementBlock("div", {
                  key: 0,
                  class: "empty"
                }, [
                  _createElementVNode("span", null, "◎"),
                  _createElementVNode("h3", null, "Seu ambiente está pronto para começar"),
                  _createElementVNode("p", null, "Cadastre uma conexão para iniciar a configuração."),
                  _createElementVNode("button", {
                    class: "btn primary",
                    onClick: $event => {navigate('connections');showConnectionForm=true}
                  }, "Cadastrar conexão", 8, ["onClick"])
                ]))
              : (_openBlock(), _createElementBlock("div", {
                  key: 1,
                  class: "event-list"
                }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(events.slice(0,8), (e) => {
                  return (_openBlock(), _createElementBlock("div", null, [_createElementVNode("span", { class: "signal online" }), _createElementVNode("div", null, [_createElementVNode("b", null, _toDisplayString(e.type), 1), _createElementVNode("small", null, _toDisplayString(date(e.created_at)), 1)])]))
                }), 256))]))]), _createElementVNode("section", { class: "panel next-steps" }, [
              _createElementVNode("p", { class: "eyebrow" }, "PRIMEIROS PASSOS"),
              _createElementVNode("h2", null, "Uma integração verificável"),
              _createElementVNode("a", {
                href: "#connections",
                onClick: _withModifiers($event => (navigate('connections')), ["prevent"])
              }, [_createElementVNode("span", { class: "step-number" }, "1"), _createElementVNode("span", null, [_createElementVNode("b", null, "Cadastre a conta"), _createElementVNode("small", null, "Token ou login com sessão")]), _createElementVNode("span", null, "→")], 8, ["onClick"]),
              _createElementVNode("a", {
                href: "#contracts",
                onClick: _withModifiers($event => (navigate('contracts')), ["prevent"])
              }, [_createElementVNode("span", { class: "step-number" }, "2"), _createElementVNode("span", null, [_createElementVNode("b", null, "Valide as operações"), _createElementVNode("small", null, "Postman, HAR ou contrato manual")]), _createElementVNode("span", null, "→")], 8, ["onClick"]),
              _createElementVNode("a", {
                href: "#clients",
                onClick: _withModifiers($event => (navigate('clients')), ["prevent"])
              }, [_createElementVNode("span", { class: "step-number" }, "3"), _createElementVNode("span", null, [_createElementVNode("b", null, "Consulte e automatize"), _createElementVNode("small", null, "Primeiro leitura, depois alterações")]), _createElementVNode("span", null, "→")], 8, ["onClick"])
            ])]),
            _createElementVNode("div", { class: "notice spaced" }, "O perfil inicial contém somente a URL de listagem observada no Servip2P, ainda desabilitada para validação. A aplicação não apresenta endpoints de outros painéis como se fossem do kOfficePanel.")
          ], 512), [[_vShow, page==='overview']]),
          _withDirectives(_createElementVNode("section", null, [
            _createElementVNode("div", { class: "actions section-actions" }, [
              isAdmin
                ? (_openBlock(), _createElementBlock("button", {
                    key: 0,
                    class: "btn primary",
                    onClick: $event => (showConnectionForm=!showConnectionForm)
                  }, "＋ Nova conexão", 8, ["onClick"]))
                : _createCommentVNode("", true),
              (activeConnection && isAdmin)
                ? (_openBlock(), _createElementBlock("button", {
                    key: 1,
                    class: "btn secondary",
                    onClick: connect,
                    disabled: busy
                  }, "Autenticar conexão", 8, ["onClick", "disabled"]))
                : _createCommentVNode("", true),
              (activeConnection && isAdmin)
                ? (_openBlock(), _createElementBlock("button", {
                    key: 2,
                    class: "btn secondary",
                    onClick: inspectLogin,
                    disabled: busy
                  }, "Inspecionar formulário", 8, ["onClick", "disabled"]))
                : _createCommentVNode("", true),
              (activeConnection && isAdmin)
                ? (_openBlock(), _createElementBlock("button", {
                    key: 3,
                    class: "btn secondary",
                    onClick: disconnect
                  }, "Descartar sessão local", 8, ["onClick"]))
                : _createCommentVNode("", true)
            ]),
            (showConnectionForm && isAdmin)
              ? (_openBlock(), _createElementBlock("form", {
                  key: 0,
                  class: "panel padded spaced",
                  onSubmit: _withModifiers(createConnection, ["prevent"])
                }, [
                  _createElementVNode("h2", null, "Nova conexão de revendedor"),
                  _createElementVNode("div", { class: "form-grid" }, [
                    _createElementVNode("label", { class: "field" }, [_createTextVNode("Nome"), _withDirectives(_createElementVNode("input", {
                      "onUpdate:modelValue": $event => ((connectionForm.name) = $event),
                      required: "",
                      placeholder: "Minha revenda"
                    }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, connectionForm.name]])]),
                    _createElementVNode("label", { class: "field" }, [_createTextVNode("URL base"), _withDirectives(_createElementVNode("input", {
                      "onUpdate:modelValue": $event => ((connectionForm.base_url) = $event),
                      required: "",
                      type: "url",
                      placeholder: "https://servip2p.com"
                    }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, connectionForm.base_url]])]),
                    _createElementVNode("label", { class: "field" }, [_createTextVNode("Autenticação"), _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((connectionForm.auth_mode) = $event) }, [_createElementVNode("option", { value: "form" }, "Login por formulário HTTP"), _createElementVNode("option", { value: "token" }, "Token da API pública"), _createElementVNode("option", { value: "browser" }, "Login com navegador (Playwright)")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, connectionForm.auth_mode]])]),
                    (connectionForm.auth_mode==='token')
                      ? (_openBlock(), _createElementBlock("label", {
                          key: 0,
                          class: "field"
                        }, [_createTextVNode("Token do painel"), _withDirectives(_createElementVNode("input", {
                          "onUpdate:modelValue": $event => ((connectionForm.token) = $event),
                          type: "password",
                          autocomplete: "off"
                        }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, connectionForm.token]])]))
                      : (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [_createElementVNode("label", { class: "field" }, [_createTextVNode("Usuário"), _withDirectives(_createElementVNode("input", {
                          "onUpdate:modelValue": $event => ((connectionForm.username) = $event),
                          autocomplete: "off"
                        }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, connectionForm.username]])]), _createElementVNode("label", { class: "field" }, [_createTextVNode("Senha"), _withDirectives(_createElementVNode("input", {
                          "onUpdate:modelValue": $event => ((connectionForm.password) = $event),
                          type: "password",
                          autocomplete: "new-password"
                        }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, connectionForm.password]])])], 64))
                  ]),
                  _createElementVNode("p", { class: "muted small" }, "O host precisa estar permitido em RESMAN_ALLOWED_HOSTS. O token/usuário/senha nunca são retornados pela API."),
                  _createElementVNode("div", { class: "actions spaced" }, [_createElementVNode("button", {
                    class: "btn primary",
                    disabled: busy
                  }, "Salvar conexão", 8, ["disabled"]), _createElementVNode("button", {
                    type: "button",
                    class: "btn secondary",
                    onClick: $event => (showConnectionForm=false)
                  }, "Cancelar", 8, ["onClick"])])
                ], 40, ["onSubmit"]))
              : _createCommentVNode("", true),
            (editor && isAdmin)
              ? (_openBlock(), _createElementBlock("form", {
                  key: 1,
                  id: "connection-editor",
                  class: "panel padded spaced",
                  onSubmit: _withModifiers(saveConnection, ["prevent"])
                }, [
                  _createElementVNode("h2", null, "Editar conexão"),
                  _createElementVNode("p", { class: "muted small" }, "Credenciais em branco são preservadas. Ao mudar o endereço, as credenciais anteriores são removidas por segurança. A edição invalida a sessão, limpa o cache de clientes, cancela operações na fila e pausa agendamentos."),
                  _createElementVNode("div", { class: "form-grid" }, [
                    _createElementVNode("label", { class: "field" }, [_createTextVNode("Nome da conexão"), _withDirectives(_createElementVNode("input", {
                      "onUpdate:modelValue": $event => ((editor.name) = $event),
                      required: "",
                      maxlength: "100"
                    }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, editor.name]])]),
                    _createElementVNode("label", { class: "field" }, [_createTextVNode("Endereço do painel"), _withDirectives(_createElementVNode("input", {
                      "onUpdate:modelValue": $event => ((editor.base_url) = $event),
                      type: "url",
                      required: ""
                    }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, editor.base_url]])]),
                    _createElementVNode("label", { class: "field" }, [_createTextVNode("Modo de autenticação"), _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((editor.auth_mode) = $event) }, [_createElementVNode("option", { value: "browser" }, "Login com navegador integrado"), _createElementVNode("option", { value: "form" }, "Login por formulário HTTP"), _createElementVNode("option", { value: "token" }, "Token da API pública")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, editor.auth_mode]])]),
                    _createElementVNode("label", { class: "field" }, [_createTextVNode("Novo usuário"), _withDirectives(_createElementVNode("input", {
                      "onUpdate:modelValue": $event => ((editor.credentials.username) = $event),
                      autocomplete: "off",
                      placeholder: "Vazio: manter o atual"
                    }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, editor.credentials.username]])]),
                    _createElementVNode("label", { class: "field" }, [_createTextVNode("Nova senha"), _withDirectives(_createElementVNode("input", {
                      "onUpdate:modelValue": $event => ((editor.credentials.password) = $event),
                      type: "password",
                      autocomplete: "new-password",
                      placeholder: "Vazio: manter a atual"
                    }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, editor.credentials.password]])]),
                    _createElementVNode("label", { class: "field" }, [_createTextVNode("Novo token"), _withDirectives(_createElementVNode("input", {
                      "onUpdate:modelValue": $event => ((editor.credentials.token) = $event),
                      type: "password",
                      autocomplete: "off",
                      placeholder: "Vazio: manter o atual"
                    }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, editor.credentials.token]])])
                  ]),
                  _createElementVNode("details", { class: "spaced" }, [
                    _createElementVNode("summary", null, "Configuração de login e token"),
                    _createElementVNode("p", { class: "muted small" }, "Detecção automática quando os nomes estiverem vazios. O seletor de sucesso é opcional quando uma consulta autenticada ou a página do painel confirma a sessão."),
                    _createElementVNode("div", { class: "form-grid" }, [
                      _createElementVNode("label", { class: "field" }, [_createTextVNode("Página de login"), _withDirectives(_createElementVNode("input", {
                        "onUpdate:modelValue": $event => ((editor.login.page) = $event),
                        placeholder: "/login/",
                        required: ""
                      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, editor.login.page]])]),
                      _createElementVNode("label", { class: "field" }, [_createTextVNode("Seletor do formulário"), _withDirectives(_createElementVNode("input", {
                        "onUpdate:modelValue": $event => ((editor.login.form_selector) = $event),
                        placeholder: "form"
                      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, editor.login.form_selector]])]),
                      _createElementVNode("label", { class: "field" }, [_createTextVNode("Nome do campo usuário"), _withDirectives(_createElementVNode("input", {
                        "onUpdate:modelValue": $event => ((editor.login.username_field) = $event),
                        placeholder: "Automático"
                      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, editor.login.username_field]])]),
                      _createElementVNode("label", { class: "field" }, [_createTextVNode("Nome do campo senha"), _withDirectives(_createElementVNode("input", {
                        "onUpdate:modelValue": $event => ((editor.login.password_field) = $event),
                        placeholder: "Automático"
                      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, editor.login.password_field]])]),
                      _createElementVNode("label", { class: "field" }, [_createTextVNode("Seletor do usuário"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((editor.login.username_selector) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, editor.login.username_selector]])]),
                      _createElementVNode("label", { class: "field" }, [_createTextVNode("Seletor da senha"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((editor.login.password_selector) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, editor.login.password_selector]])]),
                      _createElementVNode("label", { class: "field" }, [_createTextVNode("Seletor do botão entrar"), _withDirectives(_createElementVNode("input", { "onUpdate:modelValue": $event => ((editor.login.submit_selector) = $event) }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, editor.login.submit_selector]])]),
                      _createElementVNode("label", { class: "field" }, [_createTextVNode("Seletor de sucesso (opcional)"), _withDirectives(_createElementVNode("input", {
                        "onUpdate:modelValue": $event => ((editor.login.success_selector) = $event),
                        placeholder: "Automático / consulta autenticada"
                      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, editor.login.success_selector]])]),
                      _createElementVNode("label", { class: "field" }, [_createTextVNode("Local do token"), _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((editor.token_auth.location) = $event) }, [_createElementVNode("option", { value: "header" }, "Cabeçalho"), _createElementVNode("option", { value: "query" }, "Parâmetro da URL"), _createElementVNode("option", { value: "body" }, "Corpo")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, editor.token_auth.location]])]),
                      _createElementVNode("label", { class: "field" }, [_createTextVNode("Nome do token"), _withDirectives(_createElementVNode("input", {
                        "onUpdate:modelValue": $event => ((editor.token_auth.name) = $event),
                        placeholder: "Conforme o contrato da API"
                      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, editor.token_auth.name]])]),
                      _createElementVNode("label", { class: "field" }, [_createTextVNode("Prefixo do token"), _withDirectives(_createElementVNode("input", {
                        "onUpdate:modelValue": $event => ((editor.token_auth.prefix) = $event),
                        placeholder: "Conforme o contrato da API"
                      }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, editor.token_auth.prefix]])])
                    ]),
                    _createElementVNode("p", { class: "muted small" }, "Limpar credenciais explicitamente:"),
                    _createElementVNode("div", { class: "actions wrap" }, [_createElementVNode("label", { class: "check" }, [_withDirectives(_createElementVNode("input", {
                      type: "checkbox",
                      value: "username",
                      "onUpdate:modelValue": $event => ((editor.clear_credentials) = $event)
                    }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, editor.clear_credentials]]), _createTextVNode("Remover usuário salvo")]), _createElementVNode("label", { class: "check" }, [_withDirectives(_createElementVNode("input", {
                      type: "checkbox",
                      value: "password",
                      "onUpdate:modelValue": $event => ((editor.clear_credentials) = $event)
                    }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, editor.clear_credentials]]), _createTextVNode("Remover senha salva")]), _createElementVNode("label", { class: "check" }, [_withDirectives(_createElementVNode("input", {
                      type: "checkbox",
                      value: "token",
                      "onUpdate:modelValue": $event => ((editor.clear_credentials) = $event)
                    }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, editor.clear_credentials]]), _createTextVNode("Remover token salvo")])])
                  ]),
                  _createElementVNode("div", { class: "actions spaced" }, [_createElementVNode("button", {
                    class: "btn primary",
                    disabled: busy
                  }, "Salvar alterações", 8, ["disabled"]), _createElementVNode("button", {
                    type: "button",
                    class: "btn secondary",
                    onClick: $event => (editor=null),
                    disabled: busy
                  }, "Cancelar edição", 8, ["onClick", "disabled"])])
                ], 40, ["onSubmit"]))
              : _createCommentVNode("", true),
            (deleteTarget && isAdmin)
              ? (_openBlock(), _createElementBlock("form", {
                  key: 2,
                  id: "connection-delete",
                  class: "panel padded spaced",
                  onSubmit: _withModifiers(removeConnection, ["prevent"])
                }, [
                  _createElementVNode("h2", null, "Excluir conexão definitivamente"),
                  _createElementVNode("p", null, [_createTextVNode("Esta ação remove "), _createElementVNode("strong", null, _toDisplayString(deleteTarget.name), 1), _createTextVNode(", suas credenciais, sessão, perfil, cache de clientes, operações, agendamentos e eventos locais. Tokens restritos são ajustados ou revogados. Não exclui contas no fornecedor nem altera backups externos.")]),
                  _createElementVNode("p", { class: "notice spaced" }, "Clientes em cache: " + _toDisplayString(deleteTarget.impact.clients) + " · Operações: " + _toDisplayString(deleteTarget.impact.operations) + " · Agendamentos: " + _toDisplayString(deleteTarget.impact.schedules) + " · Eventos: " + _toDisplayString(deleteTarget.impact.events) + " · Entregas de webhook: " + _toDisplayString(deleteTarget.impact.deliveries), 1),
                  (deleteTarget.impact.running)
                    ? (_openBlock(), _createElementBlock("p", {
                        key: 0,
                        class: "feedback error"
                      }, "Há uma operação em execução. Aguarde sua conclusão antes de excluir."))
                    : _createCommentVNode("", true),
                  (deleteTarget.impact.uncertain)
                    ? (_openBlock(), _createElementBlock("label", {
                        key: 1,
                        class: "check spaced"
                      }, [_withDirectives(_createElementVNode("input", {
                        type: "checkbox",
                        "onUpdate:modelValue": $event => ((deleteUncertain) = $event)
                      }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, deleteUncertain]]), _createTextVNode("Reconheço que há operações incertas e confirmo a perda do histórico local. A exclusão não desfaz cobranças no fornecedor.")]))
                    : _createCommentVNode("", true),
                  _createElementVNode("label", { class: "field" }, [_createTextVNode("Digite o nome exato da conexão"), _withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": $event => ((deleteName) = $event),
                    autocomplete: "off",
                    required: ""
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, deleteName]])]),
                  _createElementVNode("div", { class: "actions spaced" }, [_createElementVNode("button", {
                    class: "btn danger",
                    disabled: busy || deleteName!==deleteTarget.name || deleteTarget.impact.running>0 || (deleteTarget.impact.uncertain>0 && !deleteUncertain)
                  }, "Excluir definitivamente", 8, ["disabled"]), _createElementVNode("button", {
                    type: "button",
                    class: "btn secondary",
                    onClick: $event => (deleteTarget=null),
                    disabled: busy
                  }, "Cancelar exclusão", 8, ["onClick", "disabled"])])
                ], 40, ["onSubmit"]))
              : _createCommentVNode("", true),
            _createElementVNode("div", { class: "connection-grid spaced" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(connections, (c) => {
              return (_openBlock(), _createElementBlock("article", { class: _normalizeClass(["panel padded", {selectedCard:c.id===connectionId}]) }, [
                _createElementVNode("div", { class: "actions" }, [_createElementVNode("div", { class: "connection-avatar" }, "↔"), _createElementVNode("div", { class: "grow" }, [_createElementVNode("h2", null, _toDisplayString(c.name), 1), _createElementVNode("p", { class: "muted small" }, _toDisplayString(c.base_url), 1)]), _createElementVNode("span", { class: _normalizeClass(["badge", {warning:c.status!=='authenticated'}]) }, _toDisplayString(statusLabel(c.status)), 3)]),
                _createElementVNode("div", { class: "connection-meta" }, [_createElementVNode("span", null, _toDisplayString(c.auth_mode), 1), _createElementVNode("span", null, "Perfil r" + _toDisplayString(c.revision), 1)]),
                _createElementVNode("button", {
                  class: "btn secondary full",
                  onClick: $event => {connectionId=c.id;changeConnection()}
                }, _toDisplayString(c.id===connectionId?'Conexão selecionada':'Selecionar conexão'), 9, ["onClick"]),
                isAdmin
                  ? (_openBlock(), _createElementBlock("div", {
                      key: 0,
                      class: "actions spaced connection-card-actions"
                    }, [_createElementVNode("button", {
                      class: "btn secondary",
                      onClick: $event => (beginEditConnection(c)),
                      disabled: busy
                    }, "Editar", 8, ["onClick", "disabled"]), _createElementVNode("button", {
                      class: "btn danger",
                      onClick: $event => (beginDeleteConnection(c)),
                      disabled: busy
                    }, "Excluir conexão", 8, ["onClick", "disabled"])]))
                  : _createCommentVNode("", true)
              ], 2))
            }), 256))]),
            (!connections.length)
              ? (_openBlock(), _createElementBlock("div", {
                  key: 3,
                  class: "panel empty spaced"
                }, [_createElementVNode("h3", null, "Nenhuma conexão cadastrada"), _createElementVNode("p", null, "Seu banco está vazio. Nenhum cliente ou dado de demonstração foi misturado ao ambiente.")]))
              : _createCommentVNode("", true),
            loginInspection
              ? (_openBlock(), _createElementBlock("div", {
                  key: 4,
                  class: "panel padded spaced"
                }, [
                  _createElementVNode("h2", null, "Formulário observado — somente leitura"),
                  _createElementVNode("p", { class: "muted" }, "Os nomes podem ser detectados automaticamente. A sugestão não contém valores de CSRF, cookies ou credenciais."),
                  (loginInspection.suggested_login && isAdmin)
                    ? (_openBlock(), _createElementBlock("button", {
                        key: 0,
                        class: "btn secondary",
                        onClick: applyLoginSuggestion,
                        disabled: busy
                      }, "Aplicar campos detectados", 8, ["onClick", "disabled"]))
                    : _createCommentVNode("", true),
                  _createElementVNode("pre", null, _toDisplayString(pretty(loginInspection)), 1)
                ]))
              : _createCommentVNode("", true),
            (activeConnection && isAdmin)
              ? (_openBlock(), _createElementBlock("form", {
                  key: 5,
                  class: "panel padded spaced",
                  onSubmit: _withModifiers(saveCredentials, ["prevent"])
                }, [
                  _createElementVNode("h2", null, "Atualizar credenciais da conexão ativa"),
                  _createElementVNode("p", { class: "muted small" }, "Somente campos preenchidos são alterados. Campos vazios mantêm os valores salvos. A sessão será invalidada; para remover um valor, use Editar."),
                  _createElementVNode("div", { class: "form-grid" }, [_createElementVNode("label", { class: "field" }, [_createTextVNode("Usuário"), _withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": $event => ((credentialForm.username) = $event),
                    autocomplete: "off"
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, credentialForm.username]])]), _createElementVNode("label", { class: "field" }, [_createTextVNode("Senha"), _withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": $event => ((credentialForm.password) = $event),
                    type: "password",
                    autocomplete: "new-password"
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, credentialForm.password]])]), _createElementVNode("label", { class: "field" }, [_createTextVNode("Token"), _withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": $event => ((credentialForm.token) = $event),
                    type: "password",
                    autocomplete: "off"
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, credentialForm.token]])])]),
                  _createElementVNode("button", {
                    class: "btn secondary",
                    disabled: busy
                  }, "Atualizar credenciais", 8, ["disabled"])
                ], 40, ["onSubmit"]))
              : _createCommentVNode("", true)
          ], 512), [[_vShow, page==='connections']]),
          _withDirectives(_createElementVNode("section", null, [
            _createElementVNode("div", { class: "panel padded" }, [_createElementVNode("div", { class: "actions wrap" }, [
              _withDirectives(_createElementVNode("input", {
                class: "search-input",
                "onUpdate:modelValue": $event => ((clientSearch) = $event),
                onKeyup: _withKeys($event => {clientStart=0;loadClients()}, ["enter"]),
                placeholder: "Pesquisar clientes"
              }, null, 40, ["onUpdate:modelValue", "onKeyup"]), [[_vModelText, clientSearch]]),
              _createElementVNode("button", {
                class: "btn primary",
                onClick: $event => {clientStart=0;loadClients()},
                disabled: !connectionId || busy
              }, "Consultar painel", 8, ["onClick", "disabled"]),
              _createElementVNode("button", {
                class: "btn secondary",
                onClick: $event => {clientStart=0;loadClients(true)},
                disabled: !connectionId || busy
              }, "Consultar cache local", 8, ["onClick", "disabled"]),
              _createElementVNode("button", {
                class: "btn secondary",
                onClick: $event => (beginAction('create_client')),
                disabled: !can('create_client')
              }, "＋ Novo cliente", 8, ["onClick", "disabled"])
            ]), _createElementVNode("p", { class: "small muted spaced" }, _toDisplayString(clientsSource==='local_cache'?'Cache local incremental; não é uma sincronização completa do painel.':'A listagem usa o contrato da conexão ativa, sem inferir nomes de colunas.'), 1), clientMappingRequired
              ? (_openBlock(), _createElementBlock("p", {
                  key: 0,
                  class: "notice spaced"
                }, [_createTextVNode("O painel retornou registros, mas as colunas não estão mapeadas. Configure "), _createElementVNode("code", null, "fields"), _createTextVNode(" no perfil; valores brutos podem conter senhas e não são exibidos.")]))
              : _createCommentVNode("", true)]),
            _createElementVNode("div", { class: "panel table-scroll spaced" }, [_createElementVNode("table", null, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [
              _createElementVNode("th", null, "Cliente"),
              _createElementVNode("th", null, "Login"),
              _createElementVNode("th", null, "Plano / tecnologia"),
              _createElementVNode("th", null, "Vencimento"),
              _createElementVNode("th", null, "Telas"),
              _createElementVNode("th", null, "Ação")
            ])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(clients, (c) => {
              return (_openBlock(), _createElementBlock("tr", { key: String(c.id) }, [
                _createElementVNode("td", null, [_createElementVNode("b", null, _toDisplayString(c.name || c.id || 'Sem ID mapeado'), 1), _createElementVNode("small", null, _toDisplayString(c.id), 1)]),
                _createElementVNode("td", null, _toDisplayString(c.username || '—'), 1),
                _createElementVNode("td", null, [_createTextVNode(_toDisplayString(c.plan || '—'), 1), _createElementVNode("small", null, _toDisplayString(c.technology || ''), 1)]),
                _createElementVNode("td", null, _toDisplayString(c.expires_at || '—'), 1),
                _createElementVNode("td", null, _toDisplayString(c.screens ?? '—'), 1),
                _createElementVNode("td", null, [_createElementVNode("button", {
                  class: "btn secondary small-button",
                  onClick: $event => (beginAction('renew_client',c.id)),
                  disabled: !c.id || !can('renew_client')
                }, "Renovar", 8, ["onClick", "disabled"])])
              ]))
            }), 128)), (!clients.length)
              ? (_openBlock(), _createElementBlock("tr", { key: 0 }, [_createElementVNode("td", {
                  colspan: "6",
                  class: "empty"
                }, "Nenhum cliente carregado. Consulte o painel ou o cache local.")]))
              : _createCommentVNode("", true)])])]),
            _createElementVNode("div", { class: "actions spaced" }, [_createElementVNode("button", {
              class: "btn secondary",
              onClick: $event => {clientStart=Math.max(0,clientStart-50);loadClients(clientsSource==='local_cache')},
              disabled: clientStart===0 || busy
            }, "← Anterior", 8, ["onClick", "disabled"]), _createElementVNode("span", { class: "muted small" }, "A partir de " + _toDisplayString(clientStart+1) + " · " + _toDisplayString(clients.length) + " registros nesta página", 1), _createElementVNode("button", {
              class: "btn secondary",
              onClick: $event => {clientStart+=50;loadClients(clientsSource==='local_cache')},
              disabled: clients.length<50 || busy
            }, "Próxima →", 8, ["onClick", "disabled"])]),
            _createElementVNode("div", { class: "panel padded spaced" }, [_createElementVNode("h2", null, "Planos, tecnologias e saldo"), _createElementVNode("div", { class: "actions wrap spaced" }, [_withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((queryAction) = $event) }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(readActions.filter(x=>x!=='list_clients'), (a) => {
              return (_openBlock(), _createElementBlock("option", { value: a }, _toDisplayString(label(a)), 9, ["value"]))
            }), 256))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, queryAction]]), _withDirectives(_createElementVNode("input", {
              "onUpdate:modelValue": $event => ((queryParams) = $event),
              class: "grow code-input",
              placeholder: "{\"client_id\":\"...\"}"
            }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, queryParams]]), _createElementVNode("button", {
              class: "btn secondary",
              onClick: runQuery,
              disabled: !connectionId || busy
            }, "Consultar", 8, ["onClick", "disabled"])]), queryResult
              ? (_openBlock(), _createElementBlock("pre", { key: 0 }, _toDisplayString(pretty(queryResult)), 1))
              : _createCommentVNode("", true)])
          ], 512), [[_vShow, page==='clients']]),
          _withDirectives(_createElementVNode("section", null, [
            canOperate
              ? (_openBlock(), _createElementBlock("form", {
                  key: 0,
                  class: "panel padded",
                  onSubmit: _withModifiers(submitOperation, ["prevent"])
                }, [
                  _createElementVNode("h2", null, "Nova operação"),
                  _createElementVNode("p", { class: "muted small" }, "Somente ações habilitadas no perfil podem ser executadas. Não há simulação silenciosa de sucesso."),
                  _createElementVNode("div", { class: "form-grid" }, [_createElementVNode("label", { class: "field" }, [_createTextVNode("Operação"), _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((operationAction) = $event) }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(writeActions, (a) => {
                    return (_openBlock(), _createElementBlock("option", { value: a }, _toDisplayString(label(a)) + _toDisplayString(can(a)?'':' — não validada'), 9, ["value"]))
                  }), 256))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, operationAction]])]), _createElementVNode("label", { class: "field" }, [_createTextVNode("Chave de idempotência"), _withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": $event => ((operationKey) = $event),
                    required: "",
                    minlength: "8"
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, operationKey]])])]),
                  _createElementVNode("label", { class: "field" }, [_createTextVNode("Parâmetros JSON"), _withDirectives(_createElementVNode("textarea", {
                    "onUpdate:modelValue": $event => ((operationParams) = $event),
                    class: "code-input",
                    rows: "5",
                    required: ""
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, operationParams]])]),
                  (selectedRequired.length)
                    ? (_openBlock(), _createElementBlock("p", {
                        key: 0,
                        class: "small muted"
                      }, "Obrigatórios no contrato: " + _toDisplayString(selectedRequired.join(', ')), 1))
                    : _createCommentVNode("", true),
                  _createElementVNode("label", { class: "check" }, [_withDirectives(_createElementVNode("input", {
                    type: "checkbox",
                    "onUpdate:modelValue": $event => ((operationConfirmed) = $event)
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, operationConfirmed]]), _createTextVNode("Confirmo esta operação e os possíveis custos/créditos no painel.")]),
                  _createElementVNode("button", {
                    class: "btn primary spaced",
                    disabled: !connectionId || !can(operationAction) || !operationConfirmed || busy
                  }, "Enviar para fila", 8, ["disabled"])
                ], 40, ["onSubmit"]))
              : _createCommentVNode("", true),
            _createElementVNode("div", { class: "panel table-scroll spaced" }, [_createElementVNode("table", null, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [
              _createElementVNode("th", null, "Operação"),
              _createElementVNode("th", null, "Estado"),
              _createElementVNode("th", null, "Referência"),
              _createElementVNode("th", null, "Atualizada"),
              _createElementVNode("th", null, "Ações")
            ])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(operations, (o) => {
              return (_openBlock(), _createElementBlock("tr", null, [
                _createElementVNode("td", null, [_createElementVNode("b", null, _toDisplayString(label(o.action)), 1), _createElementVNode("small", null, _toDisplayString(o.resource), 1)]),
                _createElementVNode("td", null, [_createElementVNode("span", { class: _normalizeClass(["badge", {warning:o.status!=='succeeded'}]) }, _toDisplayString(statusLabel(o.status)), 3), _createElementVNode("small", null, _toDisplayString(o.error_code), 1)]),
                _createElementVNode("td", null, [_createElementVNode("small", null, _toDisplayString(o.id), 1)]),
                _createElementVNode("td", null, _toDisplayString(date(o.updated_at)), 1),
                _createElementVNode("td", null, [(o.status==='queued' && canOperate)
                  ? (_openBlock(), _createElementBlock("button", {
                      key: 0,
                      class: "link-button",
                      onClick: $event => (cancelOperation(o))
                    }, "Cancelar", 8, ["onClick"]))
                  : _createCommentVNode("", true), (o.status==='reconciliation_required' && isAdmin)
                  ? (_openBlock(), _createElementBlock("button", {
                      key: 1,
                      class: "link-button",
                      onClick: $event => (reconcileId=o.id)
                    }, "Conferir", 8, ["onClick"]))
                  : _createCommentVNode("", true), _createElementVNode("button", {
                  class: "link-button",
                  onClick: $event => (operationDetail=o)
                }, "Detalhes", 8, ["onClick"])])
              ]))
            }), 256)), (!operations.length)
              ? (_openBlock(), _createElementBlock("tr", { key: 0 }, [_createElementVNode("td", {
                  colspan: "5",
                  class: "empty"
                }, "Nenhuma operação registrada.")]))
              : _createCommentVNode("", true)])])]),
            (reconcileId && isAdmin)
              ? (_openBlock(), _createElementBlock("form", {
                  key: 1,
                  class: "panel padded spaced",
                  onSubmit: _withModifiers(reconcile, ["prevent"])
                }, [
                  _createElementVNode("h2", null, "Conciliação manual"),
                  _createElementVNode("p", { class: "muted" }, "Confira primeiro o vencimento e o consumo de créditos no painel. Esta ação só registra o resultado; não envia nova renovação."),
                  _createElementVNode("p", { class: "small spaced" }, _toDisplayString(reconcileId), 1),
                  _createElementVNode("label", { class: "field" }, [_createTextVNode("Resultado confirmado"), _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((reconcileOutcome) = $event) }, [_createElementVNode("option", { value: "succeeded" }, "Executada no painel"), _createElementVNode("option", { value: "failed" }, "Não executada no painel")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, reconcileOutcome]])]),
                  _createElementVNode("label", { class: "field" }, [_createTextVNode("Evidência da conferência"), _withDirectives(_createElementVNode("textarea", {
                    "onUpdate:modelValue": $event => ((reconcileEvidence) = $event),
                    rows: "3",
                    minlength: "15",
                    required: ""
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, reconcileEvidence]])]),
                  _createElementVNode("button", { class: "btn primary" }, "Registrar conferência")
                ], 40, ["onSubmit"]))
              : _createCommentVNode("", true),
            operationDetail
              ? (_openBlock(), _createElementBlock("pre", {
                  key: 2,
                  class: "panel padded spaced"
                }, _toDisplayString(pretty(operationDetail)), 1))
              : _createCommentVNode("", true)
          ], 512), [[_vShow, page==='operations']]),
          _withDirectives(_createElementVNode("section", null, [_createElementVNode("div", { class: "notice" }, [_createTextVNode("Agendamentos são ordens expressas de renovação. Não consultam nem presumem pagamento. Para renovar após pagamento, seu ERP deve usar o endpoint autenticado "), _createElementVNode("code", null, "/payments/confirmed"), _createTextVNode(" com uma referência única.")]), isAdmin
            ? (_openBlock(), _createElementBlock("form", {
                key: 0,
                class: "panel padded spaced",
                onSubmit: _withModifiers(createSchedule, ["prevent"])
              }, [
                _createElementVNode("h2", null, "Programar renovação"),
                _createElementVNode("div", { class: "form-grid" }, [
                  _createElementVNode("label", { class: "field" }, [_createTextVNode("Nome"), _withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": $event => ((scheduleForm.name) = $event),
                    required: ""
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, scheduleForm.name]])]),
                  _createElementVNode("label", { class: "field" }, [_createTextVNode("ID do cliente"), _withDirectives(_createElementVNode("input", {
                    "onUpdate:modelValue": $event => ((scheduleForm.client_id) = $event),
                    required: ""
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, scheduleForm.client_id]])]),
                  _createElementVNode("label", { class: "field" }, [_createTextVNode("Primeira execução (seu horário local)"), _withDirectives(_createElementVNode("input", {
                    type: "datetime-local",
                    "onUpdate:modelValue": $event => ((scheduleForm.run_at) = $event),
                    required: ""
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, scheduleForm.run_at]])]),
                  _createElementVNode("label", { class: "field" }, [_createTextVNode("Repetir a cada N dias (vazio = única)"), _withDirectives(_createElementVNode("input", {
                    type: "number",
                    min: "1",
                    max: "366",
                    "onUpdate:modelValue": $event => ((scheduleForm.interval_days) = $event)
                  }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, scheduleForm.interval_days]])])
                ]),
                _createElementVNode("label", { class: "field" }, [_createTextVNode("Parâmetros de renovação"), _withDirectives(_createElementVNode("textarea", {
                  class: "code-input",
                  rows: "3",
                  "onUpdate:modelValue": $event => ((scheduleForm.parameters) = $event),
                  required: ""
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, scheduleForm.parameters]])]),
                _createElementVNode("label", { class: "check" }, [_withDirectives(_createElementVNode("input", {
                  type: "checkbox",
                  "onUpdate:modelValue": $event => ((scheduleForm.authorized) = $event)
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, scheduleForm.authorized]]), _createTextVNode("Autorizo a execução e o consumo de créditos nas datas programadas.")]),
                _createElementVNode("button", {
                  class: "btn primary spaced",
                  disabled: !can('renew_client') || !scheduleForm.authorized || busy
                }, "Salvar agendamento", 8, ["disabled"])
              ], 40, ["onSubmit"]))
            : _createCommentVNode("", true), _createElementVNode("div", { class: "panel table-scroll spaced" }, [_createElementVNode("table", null, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [
            _createElementVNode("th", null, "Agendamento"),
            _createElementVNode("th", null, "Cliente"),
            _createElementVNode("th", null, "Próxima execução"),
            _createElementVNode("th", null, "Estado"),
            _createElementVNode("th")
          ])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(schedules, (s) => {
            return (_openBlock(), _createElementBlock("tr", null, [
              _createElementVNode("td", null, [_createTextVNode(_toDisplayString(s.name), 1), _createElementVNode("small", null, _toDisplayString(s.interval_days ? 'A cada '+s.interval_days+' dias':'Execução única'), 1)]),
              _createElementVNode("td", null, _toDisplayString(s.client_id), 1),
              _createElementVNode("td", null, _toDisplayString(date(s.run_at)), 1),
              _createElementVNode("td", null, [_createElementVNode("span", { class: "badge warning" }, _toDisplayString(statusLabel(s.status)), 1)]),
              _createElementVNode("td", null, [(isAdmin && !['paused','completed'].includes(s.status))
                ? (_openBlock(), _createElementBlock("button", {
                    key: 0,
                    class: "link-button",
                    onClick: $event => (pauseSchedule(s))
                  }, "Pausar", 8, ["onClick"]))
                : _createCommentVNode("", true)])
            ]))
          }), 256)), (!schedules.length)
            ? (_openBlock(), _createElementBlock("tr", { key: 0 }, [_createElementVNode("td", {
                colspan: "5",
                class: "empty"
              }, "Nenhum agendamento. A aplicação precisa permanecer em execução para processar a fila.")]))
            : _createCommentVNode("", true)])])])], 512), [[_vShow, page==='automation']]),
          _withDirectives(_createElementVNode("section", null, [_createElementVNode("div", { class: "notice" }, "O contrato inicial não é homologado. Não habilite operações apenas porque existe um botão no painel. Confirme método, parâmetros, autenticação e resposta."), (!isAdmin)
            ? (_openBlock(), _createElementBlock("div", {
                key: 0,
                class: "panel padded spaced"
              }, "A edição de contratos exige administrador."))
            : (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [_createElementVNode("div", { class: "two-col spaced" }, [_createElementVNode("section", { class: "panel padded" }, [
                _createElementVNode("h2", null, "Inspecionar Postman ou HAR"),
                _createElementVNode("p", { class: "muted small" }, "Leitura local, sem executar scripts, importar sessões ou enviar requisições."),
                _createElementVNode("label", { class: "field" }, [_createTextVNode("Arquivo JSON / HAR"), _createElementVNode("input", {
                  type: "file",
                  accept: ".json,.har",
                  onChange: inspectFile
                }, null, 40, ["onChange"])]),
                (imported.length)
                  ? _withDirectives((_openBlock(), _createElementBlock("select", {
                      key: 0,
                      "onUpdate:modelValue": $event => ((importIndex) = $event)
                    }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(imported, (r, i) => {
                      return (_openBlock(), _createElementBlock("option", { value: i }, _toDisplayString(r.name), 9, ["value"]))
                    }), 256))], 8, ["onUpdate:modelValue"])), [[_vModelSelect, importIndex]])
                  : _createCommentVNode("", true),
                (imported.length)
                  ? (_openBlock(), _createElementBlock("label", {
                      key: 1,
                      class: "field"
                    }, [_createTextVNode("Associar à operação"), _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((mapAction) = $event) }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(allActions, (a) => {
                      return (_openBlock(), _createElementBlock("option", { value: a }, _toDisplayString(label(a)), 9, ["value"]))
                    }), 256))], 8, ["onUpdate:modelValue"]), [[_vModelSelect, mapAction]])]))
                  : _createCommentVNode("", true),
                (imported.length)
                  ? (_openBlock(), _createElementBlock("button", {
                      key: 2,
                      class: "btn secondary",
                      onClick: applyDraft,
                      disabled: !connectionId
                    }, "Adicionar ao rascunho do perfil", 8, ["onClick", "disabled"]))
                  : _createCommentVNode("", true),
                (imported.length)
                  ? (_openBlock(), _createElementBlock("pre", { key: 3 }, _toDisplayString(pretty(imported[importIndex])), 1))
                  : _createCommentVNode("", true)
              ]), _createElementVNode("section", { class: "panel padded" }, [_createElementVNode("h2", null, "Capacidades da conexão"), _createElementVNode("div", { class: "capability-list" }, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(capabilities, (c) => {
                return (_openBlock(), _createElementBlock("div", null, [_createElementVNode("span", null, _toDisplayString(label(c.name)), 1), _createElementVNode("span", { class: _normalizeClass(["badge", {warning:!c.enabled}]) }, _toDisplayString(c.enabled?'Habilitada':'Não validada'), 3)]))
              }), 256))])])]), _createElementVNode("form", {
                class: "panel padded spaced",
                onSubmit: _withModifiers(saveProfile, ["prevent"])
              }, [
                _createElementVNode("div", { class: "actions wrap" }, [_createElementVNode("div", { class: "grow" }, [_createElementVNode("h2", null, "Perfil de integração · revisão " + _toDisplayString(activeConnection?.revision || '—'), 1), _createElementVNode("p", { class: "muted small" }, "Selecione uma conexão. Alterações simultâneas são recusadas com HTTP 409.")]), _createElementVNode("button", {
                  type: "button",
                  class: "btn secondary",
                  onClick: loadObserved
                }, "Carregar referência observada", 8, ["onClick"])]),
                _createElementVNode("label", { class: "field" }, [_createTextVNode("Contrato JSON"), _withDirectives(_createElementVNode("textarea", {
                  "onUpdate:modelValue": $event => ((profileText) = $event),
                  rows: "24",
                  class: "code-input",
                  spellcheck: "false"
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, profileText]])]),
                _createElementVNode("div", { class: "notice" }, [
                  _createTextVNode("Para habilitar: "),
                  _createElementVNode("code", null, "verified: true"),
                  _createTextVNode(" e "),
                  _createElementVNode("code", null, "evidence"),
                  _createTextVNode(" com a origem da confirmação. Alterações exigem "),
                  _createElementVNode("code", null, "success_path"),
                  _createTextVNode(" e "),
                  _createElementVNode("code", null, "success_value"),
                  _createTextVNode(". "),
                  _createElementVNode("code", null, "fields"),
                  _createTextVNode(" deve mapear só dados de gestão, nunca senhas.")
                ]),
                _createElementVNode("button", {
                  class: "btn primary spaced",
                  disabled: !connectionId || busy
                }, "Salvar perfil e invalidar sessão anterior", 8, ["disabled"])
              ], 40, ["onSubmit"])], 64))], 512), [[_vShow, page==='contracts']]),
          _withDirectives(_createElementVNode("section", null, [(!isAdmin)
            ? (_openBlock(), _createElementBlock("div", {
                key: 0,
                class: "panel padded"
              }, "A administração de tokens e webhooks exige administrador."))
            : (_openBlock(), _createElementBlock(_Fragment, { key: 1 }, [_createElementVNode("div", { class: "two-col" }, [_createElementVNode("form", {
                class: "panel padded",
                onSubmit: _withModifiers(createToken, ["prevent"])
              }, [
                _createElementVNode("h2", null, "Token para ERP / chatbot"),
                _createElementVNode("label", { class: "field" }, [_createTextVNode("Nome"), _withDirectives(_createElementVNode("input", {
                  "onUpdate:modelValue": $event => ((tokenForm.name) = $event),
                  required: ""
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, tokenForm.name]])]),
                _createElementVNode("label", { class: "field" }, [_createTextVNode("Permissão"), _withDirectives(_createElementVNode("select", { "onUpdate:modelValue": $event => ((tokenForm.scope) = $event) }, [_createElementVNode("option", { value: "read" }, "Somente leitura"), _createElementVNode("option", { value: "operate" }, "Leitura e operações"), _createElementVNode("option", { value: "admin" }, "Administrador global")], 8, ["onUpdate:modelValue"]), [[_vModelSelect, tokenForm.scope]])]),
                (tokenForm.scope!=='admin')
                  ? (_openBlock(), _createElementBlock("label", {
                      key: 0,
                      class: "check"
                    }, [_withDirectives(_createElementVNode("input", {
                      type: "checkbox",
                      "onUpdate:modelValue": $event => ((tokenForm.restrict) = $event)
                    }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, tokenForm.restrict]]), _createTextVNode("Restringir à conexão ativa")]))
                  : _createCommentVNode("", true),
                _createElementVNode("button", {
                  class: "btn primary spaced",
                  disabled: busy || (tokenForm.restrict && tokenForm.scope!=='admin' && !connectionId)
                }, "Gerar token", 8, ["disabled"]),
                newToken
                  ? (_openBlock(), _createElementBlock("div", {
                      key: 1,
                      class: "notice spaced"
                    }, [
                      _createElementVNode("strong", null, "Copie agora; não será exibido novamente."),
                      _createElementVNode("code", { class: "secret" }, _toDisplayString(newToken), 1),
                      _createElementVNode("button", {
                        type: "button",
                        class: "link-button",
                        onClick: $event => (copy(newToken))
                      }, "Copiar token", 8, ["onClick"]),
                      _createElementVNode("button", {
                        type: "button",
                        class: "link-button",
                        onClick: $event => (newToken='')
                      }, "Ocultar", 8, ["onClick"])
                    ]))
                  : _createCommentVNode("", true)
              ], 40, ["onSubmit"]), _createElementVNode("form", {
                class: "panel padded",
                onSubmit: _withModifiers(createWebhook, ["prevent"])
              }, [
                _createElementVNode("h2", null, "Notificar seu sistema"),
                _createElementVNode("p", { class: "muted small" }, "Eventos assinados com HMAC-SHA256. Entrega com até 8 tentativas e ID estável."),
                _createElementVNode("label", { class: "field" }, [_createTextVNode("URL HTTPS autorizada"), _withDirectives(_createElementVNode("input", {
                  type: "url",
                  "onUpdate:modelValue": $event => ((hookForm.url) = $event),
                  required: ""
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, hookForm.url]])]),
                _createElementVNode("label", { class: "field" }, [_createTextVNode("Segredo HMAC (mínimo 32 caracteres)"), _withDirectives(_createElementVNode("input", {
                  type: "password",
                  "onUpdate:modelValue": $event => ((hookForm.secret) = $event),
                  minlength: "32",
                  required: "",
                  autocomplete: "new-password"
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelText, hookForm.secret]])]),
                _createElementVNode("label", { class: "check" }, [_withDirectives(_createElementVNode("input", {
                  type: "checkbox",
                  "onUpdate:modelValue": $event => ((hookForm.enabled) = $event)
                }, null, 8, ["onUpdate:modelValue"]), [[_vModelCheckbox, hookForm.enabled]]), _createTextVNode("Ativar entrega")]),
                _createElementVNode("button", {
                  class: "btn primary spaced",
                  disabled: busy
                }, "Cadastrar webhook", 8, ["disabled"]),
                _createElementVNode("p", { class: "muted small spaced" }, "O host também precisa estar permitido em RESMAN_ALLOWED_HOSTS.")
              ], 40, ["onSubmit"])]), _createElementVNode("div", { class: "panel table-scroll spaced" }, [_createElementVNode("table", null, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [
                _createElementVNode("th", null, "Token"),
                _createElementVNode("th", null, "Permissão"),
                _createElementVNode("th", null, "Estado"),
                _createElementVNode("th")
              ])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(tokens, (t) => {
                return (_openBlock(), _createElementBlock("tr", null, [
                  _createElementVNode("td", null, _toDisplayString(t.name), 1),
                  _createElementVNode("td", null, [_createTextVNode(_toDisplayString(t.scope), 1), _createElementVNode("small", null, _toDisplayString(t.connection_ids===null?'Todas as conexões':t.connection_ids.join(', ')), 1)]),
                  _createElementVNode("td", null, _toDisplayString(t.revoked?'Revogado':'Ativo'), 1),
                  _createElementVNode("td", null, [(!t.revoked)
                    ? (_openBlock(), _createElementBlock("button", {
                        key: 0,
                        class: "link-button",
                        onClick: $event => (revokeToken(t))
                      }, "Revogar", 8, ["onClick"]))
                    : _createCommentVNode("", true)])
                ]))
              }), 256))])])]), _createElementVNode("div", { class: "panel table-scroll spaced" }, [_createElementVNode("table", null, [_createElementVNode("thead", null, [_createElementVNode("tr", null, [_createElementVNode("th", null, "Webhook"), _createElementVNode("th", null, "Estado"), _createElementVNode("th")])]), _createElementVNode("tbody", null, [(_openBlock(true), _createElementBlock(_Fragment, null, _renderList(hooks, (h) => {
                return (_openBlock(), _createElementBlock("tr", null, [_createElementVNode("td", null, _toDisplayString(h.url), 1), _createElementVNode("td", null, _toDisplayString(h.enabled?'Ativo':'Desativado'), 1), _createElementVNode("td", null, [(h.enabled)
                  ? (_openBlock(), _createElementBlock("button", {
                      key: 0,
                      class: "link-button",
                      onClick: $event => (disableHook(h))
                    }, "Desativar", 8, ["onClick"]))
                  : _createCommentVNode("", true)])]))
              }), 256)), (!hooks.length)
                ? (_openBlock(), _createElementBlock("tr", { key: 0 }, [_createElementVNode("td", {
                    colspan: "3",
                    class: "empty"
                  }, "Nenhum webhook cadastrado.")]))
                : _createCommentVNode("", true)])])])], 64))], 512), [[_vShow, page==='integrations']]),
          _withDirectives(_createElementVNode("section", { class: "panel padded" }, [
            _createElementVNode("p", { class: "eyebrow" }, "DOCUMENTAÇÃO LOCAL"),
            _createElementVNode("h2", null, "API e operação"),
            _createElementVNode("p", { class: "spaced" }, "A documentação e a especificação OpenAPI funcionam sem CDN. O token da sua API não é o token do fornecedor."),
            _createElementVNode("div", { class: "actions spaced" }, [_createElementVNode("a", {
              class: "btn primary",
              href: "/docs",
              target: "_blank",
              rel: "noopener"
            }, "Abrir referência da API ↗"), _createElementVNode("a", {
              class: "btn secondary",
              href: "/openapi.json",
              download: "reseller-manager-openapi.json"
            }, "Exportar OpenAPI JSON")]),
            _createElementVNode("div", { class: "notice spaced" }, "A fila é persistente em SQLite. Use apenas um processo por pasta de dados. Ao reiniciar após uma interrupção, alterações que estavam em execução exigem conferência, sem reenvio cego."),
            _createElementVNode("h3", { class: "spaced" }, "Documentos incluídos no pacote"),
            _createElementVNode("p", { class: "spaced" }, [
              _createElementVNode("code", null, "docs/INTEGRACAO.md"),
              _createTextVNode(" · "),
              _createElementVNode("code", null, "docs/OPERACAO.md"),
              _createTextVNode(" · "),
              _createElementVNode("code", null, "docs/SEGURANCA.md"),
              _createTextVNode(" · "),
              _createElementVNode("code", null, "docs/VALIDACAO.md"),
              _createTextVNode(" · "),
              _createElementVNode("code", null, "docs/TEMPLATE.md")
            ])
          ], 512), [[_vShow, page==='documentation']]),
          _createElementVNode("footer", { class: "content-footer" }, [_createElementVNode("span", null, "Reseller Manager · v0.1.5"), _createElementVNode("span", null, "Wallace Kleiton — WWSoftware’s")])
        ])])]))]))
  }
};
