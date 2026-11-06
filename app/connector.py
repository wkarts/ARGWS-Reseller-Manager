"""Contract-driven kOffice connector. No guessed writes and no automatic mutation retry."""
from __future__ import annotations
import asyncio
import json
import re
import http.cookiejar
from urllib.parse import quote, urlsplit
from typing import Any
from bs4 import BeautifulSoup
import httpx
from .errors import BridgeError
from .models import Profile, Endpoint, READ_ACTIONS, WRITE_ACTIONS
from .network import NetworkPolicy, limited_request

TOKEN = re.compile(r"\{\{(input|secret|session)\.([\w.-]+)\}\}")


def at(data, path: str):
    if path == "": return data
    for part in path.split("."):
        if isinstance(data, list) and part.isdigit():
            n = int(part)
            if n >= len(data): return None
            data = data[n]
        elif isinstance(data, dict): data = data.get(part)
        else: return None
    return data


def render(value, ctx, path=False):
    if isinstance(value, dict): return {k: render(v, ctx) for k, v in value.items()}
    if isinstance(value, list): return [render(v, ctx) for v in value]
    if not isinstance(value, str): return value
    exact = TOKEN.fullmatch(value)
    def resolve(match):
        result = at(ctx.get(match[1], {}), match[2])
        if result is None: raise BridgeError("parameter_missing", f"Parâmetro obrigatório ausente: {match[1]}.{match[2]}.", 422)
        return result
    if exact and not path: return resolve(exact)
    def substitute(m):
        result = str(resolve(m))
        return quote(result, safe="") if path else result
    return TOKEN.sub(substitute, value)


def looks_like_login(response):
    # HTTP 200 with HTML login is an auth failure, never a successful API result.
    text = response.text[:250_000].lower()
    return ("text/html" in response.headers.get("content-type", "").lower() and any(x in text for x in ('type="password"', "type='password'", "/login/", "window.location", "http-equiv=\"refresh\"")))


def save_cookies(client):
    return [{"name": c.name, "value": c.value, "domain": c.domain, "path": c.path, "secure": c.secure, "expires": c.expires, "rest": c._rest} for c in client.cookies.jar]


def load_cookies(client, cookies, host):
    for c in cookies:
        domain = c.get("domain", host)
        if domain.lstrip(".") != host and not host.endswith("." + domain.lstrip(".")): continue
        cookie = http.cookiejar.Cookie(0, c["name"], c["value"], None, False, domain, bool(domain), domain.startswith("."), c.get("path", "/"), True, c.get("secure", True), c.get("expires"), c.get("expires") is None, None, None, c.get("rest", {}), False)
        client.cookies.jar.set_cookie(cookie)


class Connector:
    def __init__(self, store, settings, transport=None):
        self.store, self.settings = store, settings
        self.policy = NetworkPolicy(settings)
        self.transport = transport
        self.locks: dict[str, asyncio.Lock] = {}

    def lock(self, identifier): return self.locks.setdefault(identifier, asyncio.Lock())

    def client(self, connection):
        client = httpx.AsyncClient(timeout=httpx.Timeout(self.settings.request_timeout), follow_redirects=False, trust_env=False, transport=self.transport, headers={"User-Agent": "ResellerManager/0.1.0", "Accept": "application/json, text/html;q=0.8"})
        load_cookies(client, connection["session"].get("cookies", []), urlsplit(connection["base_url"]).hostname)
        return client

    def endpoint(self, connection, action):
        profile = Profile.model_validate(connection["profile"])
        endpoint = profile.endpoints.get(action)
        if not endpoint or not endpoint.verified:
            raise BridgeError("capability_unverified", "Esta operação ainda não possui contrato confirmado no perfil da conexão.", 409)
        if action in WRITE_ACTIONS and not endpoint.success_path:
            raise BridgeError("success_rule_required", "Operação de alteração exige regra explícita de sucesso.", 409)
        return profile, endpoint

    def prepare(self, connection, action, parameters):
        profile, endpoint = self.endpoint(connection, action)
        for key in endpoint.required:
            if parameters.get(key) in (None, ""): raise BridgeError("parameter_missing", f"Informe o parâmetro obrigatório: {key}.", 422)
        ctx = {"input": parameters, "secret": connection["credentials"], "session": connection["session"]}
        path = render(endpoint.path, ctx, path=True)
        url = self.policy.relative_url(connection["base_url"], path)
        headers = render(endpoint.headers, ctx)
        query = render(endpoint.params, ctx)
        body = render(endpoint.body, ctx)
        if connection["auth_mode"] == "token":
            auth = profile.token_auth
            if not auth.name: raise BridgeError("token_contract_missing", "Configure o nome e o local do token conforme a documentação. Bearer não é presumido.", 409)
            if not connection["credentials"].get("token"): raise BridgeError("token_missing", "Informe o token na conexão.", 409)
            token = auth.prefix + connection["credentials"]["token"]
            if auth.location == "header": headers[auth.name] = token
            elif auth.location == "query": query[auth.name] = token
            else:
                if endpoint.method == "GET" or endpoint.encoding == "query": raise BridgeError("token_contract_invalid", "Token no corpo é incompatível com esta operação.", 409)
                body[auth.name] = token
        kwargs: dict[str, Any] = {"headers": headers, "params": query}
        if endpoint.encoding == "query": kwargs["params"] = {**query, **body}
        elif endpoint.encoding == "form": kwargs["data"] = body
        else: kwargs["json"] = body
        return endpoint, url, kwargs

    def decode(self, response, action, endpoint):
        writing = action in WRITE_ACTIONS
        if response.status_code in {401, 403} or response.is_redirect or looks_like_login(response):
            raise BridgeError("authentication_required", "O painel solicitou autenticação ou negou acesso. Nenhuma repetição automática foi feita.", 401, uncertain=writing)
        if response.status_code >= 400:
            raise BridgeError("upstream_http_error", f"Painel retornou HTTP {response.status_code}. Confira o resultado antes de repetir.", 502, uncertain=writing)
        try: payload = response.json()
        except (ValueError, UnicodeError) as e:
            raise BridgeError("unexpected_response", "O painel não retornou JSON. HTTP 200 não comprova sucesso.", 502, uncertain=writing) from e
        if writing:
            success = at(payload, endpoint.success_path or "")
            # Strict equality avoids True == 1 accepting a different contract by accident.
            if response.status_code not in endpoint.success_status or type(success) is not type(endpoint.success_value) or success != endpoint.success_value:
                raise BridgeError("unconfirmed_result", "A resposta não confirmou a regra de sucesso configurada. Confira no painel.", 502, uncertain=True)
            result = {"confirmed_by": "configured_upstream_response", "http_status": response.status_code}
            if endpoint.fields:
                result["data"] = self.project(payload, endpoint.fields)
            return result
        rows = at(payload, endpoint.data_path)
        if rows is None: raise BridgeError("response_contract_changed", "Campo de dados ausente. Revalide o contrato.", 502)
        if isinstance(rows, list):
            if not endpoint.fields:
                return {"data": [], "received_count": len(rows), "mapping_required": True, "message": "Defina fields para mapear índices/nomes. Dados brutos e possíveis senhas não são expostos.", "records_total": payload.get("recordsTotal") if isinstance(payload, dict) else None}
            data = [self.project(row, endpoint.fields) for row in rows]
            return {"data": data, "received_count": len(rows), "mapping_required": False, "records_total": payload.get("recordsTotal", len(rows)) if isinstance(payload, dict) else len(rows), "records_filtered": payload.get("recordsFiltered") if isinstance(payload, dict) else None}
        if not isinstance(rows, dict): raise BridgeError("response_contract_changed", "Esperada uma lista ou objeto no caminho de dados.", 502)
        if not endpoint.fields: return {"data": {}, "mapping_required": True}
        return {"data": self.project(rows, endpoint.fields), "mapping_required": False}

    @staticmethod
    def project(row, fields):
        output = {}
        for field, path in fields.items():
            value = at(row, path)
            # Never return upstream HTML or arbitrary nested response structures.
            if isinstance(value, str): value = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)[:2000]
            if isinstance(value, (str, int, float, bool)) or value is None: output[field] = value
        return output

    async def ensure_session_before_write(self, identifier, revision):
        """Read-only authentication preflight; login at most once, BEFORE any mutation."""
        c = self.store.connection(identifier, True)
        if c["revision"] != revision:
            raise BridgeError("profile_changed", "Contrato ou credenciais mudaram. Nenhuma alteração foi enviada.", 409)
        if c["auth_mode"] == "token": return
        endpoint = c["profile"].get("endpoints", {}).get("list_clients", {})
        if not endpoint.get("verified"):
            raise BridgeError("authentication_probe_required", "Valide a consulta de clientes antes de automatizar alterações por sessão.", 409)
        if c["session"].get("cookies"):
            try:
                await self.execute(identifier, "list_clients", {"start": 0, "length": 1, "search": "", "draw": 1})
                return
            except BridgeError as exc:
                if exc.code != "authentication_required": raise
        # No retries of the mutation: only the independent login/read probe happens here.
        result = await self.connect(identifier)
        if result.get("status") != "authenticated":
            raise BridgeError("authentication_required", "Login automático não confirmado. Revise a conexão.", 401)

    async def execute(self, identifier, action, parameters, expected_revision=None):
        async with self.lock(identifier):
            c = self.store.connection(identifier, True)
            if expected_revision is not None and c["revision"] != expected_revision:
                raise BridgeError("profile_changed", "Contrato ou credenciais mudaram após o agendamento. A requisição não foi enviada.", 409)
            endpoint, url, kwargs = self.prepare(c, action, parameters)
            await self.policy.validate(url)
            async with self.client(c) as client:
                try:
                    response = await limited_request(client, self.settings, endpoint.method, url, **kwargs)
                    result = self.decode(response, action, endpoint)
                    self.store.set_session(identifier, {**c["session"], "cookies": save_cookies(client)}, "authenticated")
                    if action == "list_clients": self.store.cache_clients(identifier, result.get("data", []))
                    return result
                except httpx.HTTPError as e:
                    raise BridgeError("upstream_network_error", "Falha de comunicação com o painel. Operações de alteração não são repetidas automaticamente.", 502, uncertain=action in WRITE_ACTIONS) from e
                except BridgeError as e:
                    if e.code == "authentication_required": self.store.set_session(identifier, {}, "expired")
                    if action in WRITE_ACTIONS and e.code == "upstream_too_large": e.uncertain = True
                    raise

    async def login_page(self, c, client):
        profile = Profile.model_validate(c["profile"])
        url = self.policy.relative_url(c["base_url"], profile.login.page)
        for _ in range(4):
            await self.policy.validate(url)
            response = await limited_request(client, self.settings, "GET", url)
            if response.is_redirect:
                url = self.policy.same_origin(c["base_url"], response.headers.get("location", "/")); continue
            if response.status_code >= 400: raise BridgeError("login_unavailable", f"Página de login retornou HTTP {response.status_code}.", 502)
            return response, profile
        raise BridgeError("too_many_redirects", "Muitos redirecionamentos no login.", 502)

    async def inspect_login(self, identifier):
        async with self.lock(identifier):
            c = self.store.connection(identifier, True)
            try:
                async with self.client(c) as client:
                    response, profile = await self.login_page(c, client)
                    soup = BeautifulSoup(response.text, "html.parser")
                    forms = []
                    for form in soup.select("form"):
                        action = self.policy.same_origin(c["base_url"], form.get("action") or str(response.url))
                        forms.append({"method": form.get("method", "GET").upper(), "action_path": urlsplit(action).path, "fields": [{"name": i.get("name"), "type": i.get("type", "text")} for i in form.select("input[name],select[name],textarea[name]")]})
                    return {"forms": forms, "note": "Somente leitura. Nenhum valor oculto ou cookie é retornado."}
            except httpx.HTTPError as exc: raise BridgeError("login_unavailable", "Não foi possível consultar a página de login.", 502) from exc

    async def connect(self, identifier):
        c = self.store.connection(identifier, True)
        if c["auth_mode"] == "token":
            result = await self.execute(identifier, "list_clients", {"start": 0, "length": 1, "search": "", "draw": 1})
            return {"status": "authenticated", "probe": result}
        if c["auth_mode"] == "browser": return await self.browser_login(identifier)
        async with self.lock(identifier):
            try:
                async with self.client(c) as client:
                    response, profile = await self.login_page(c, client)
                    soup = BeautifulSoup(response.text, "html.parser")
                    candidates = soup.select(profile.login.form_selector)
                    form = next((x for x in candidates if x.select_one('input[type="password"]')), None)
                    if form is None: raise BridgeError("login_form_missing", "Formulário não identificado. Revise seletores ou use o modo navegador.", 409)
                    action = self.policy.same_origin(c["base_url"], form.get("action") or str(response.url))
                    if form.get("method", "GET").upper() != "POST": raise BridgeError("login_method_unverified", "O formulário não declara POST. Revise o contrato sem enviar senha na URL.", 409)
                    username = profile.login.username_field
                    password = profile.login.password_field
                    if not username or not password:
                        raise BridgeError("login_fields_required", "Use Inspecionar login e configure os nomes reais dos campos usuário e senha no perfil.", 409)
                    names = {i.get("name") for i in form.select("input[name]")}
                    if username not in names or password not in names: raise BridgeError("login_fields_changed", "Campos configurados não encontrados no formulário atual.", 409)
                    if not c["credentials"].get("username") or not c["credentials"].get("password"): raise BridgeError("credentials_missing", "Configure usuário e senha da sua conta.", 409)
                    hidden = {i["name"]: i.get("value", "") for i in form.select('input[type="hidden"][name]')}
                    body = {**hidden, **profile.login.extra_fields, username: c["credentials"]["username"], password: c["credentials"]["password"]}
                    await self.policy.validate(action)
                    result = await limited_request(client, self.settings, "POST", action, data=body, headers={"Origin": c["base_url"], "Referer": str(response.url)})
                    # Follow only same-origin login redirects, always with GET, never replay credentials.
                    for _ in range(3):
                        if not result.is_redirect: break
                        target = self.policy.same_origin(c["base_url"], result.headers.get("location", "/"))
                        await self.policy.validate(target)
                        result = await limited_request(client, self.settings, "GET", target)
                    if result.status_code >= 400 or looks_like_login(result):
                        self.store.set_session(identifier, {}, "requires_action")
                        raise BridgeError("login_requires_action", "Login não confirmado. Confira credenciais, 2FA, CAPTCHA ou bloqueio no painel.", 401)
                    # Hidden CSRF fields on the authenticated page, not stale login CSRF.
                    after = BeautifulSoup(result.text, "html.parser")
                    csrf = {i["name"]: i.get("value", "") for i in after.select('input[type="hidden"][name]')}
                    for meta in after.select('meta[name][content]'):
                        if "csrf" in meta["name"].lower(): csrf[meta["name"]] = meta["content"]
                    self.store.set_session(identifier, {"cookies": save_cookies(client), "csrf": csrf}, "session_received")
            except httpx.HTTPError as exc:
                raise BridgeError("login_network_error", "Falha durante o login. Nenhuma tentativa automática adicional foi feita.", 502) from exc
        # A JSON probe is required to upgrade session_received to authenticated.
        profile = Profile.model_validate(c["profile"])
        endpoint = profile.endpoints.get("list_clients")
        if not endpoint or not endpoint.verified:
            return {"status": "session_received", "message": "Sessão recebida; confirme o contrato de listagem para testar a autenticação."}
        result = await self.execute(identifier, "list_clients", {"start": 0, "length": 1, "search": "", "draw": 1})
        return {"status": "authenticated", "probe": result}

    async def browser_login(self, identifier):
        if not self.settings.browser_enabled: raise BridgeError("browser_disabled", "Autenticação por navegador desabilitada nesta instância.", 409)
        try:
            from playwright.async_api import async_playwright, Error as PlaywrightError
        except ImportError as exc: raise BridgeError("browser_unavailable", "Pacote incompleto: motor de navegador integrado ausente. Reinstale a distribuição completa.", 503) from exc
        async with self.lock(identifier):
            c = self.store.connection(identifier, True)
            p = Profile.model_validate(c["profile"])
            if not p.login.success_selector: raise BridgeError("browser_contract_missing", "Configure success_selector para confirmar o login sem adivinhação.", 409)
            url = self.policy.relative_url(c["base_url"], p.login.page)
            await self.policy.validate(url)
            try:
                async with async_playwright() as pw:
                    from .browser_support import launch_browser
                    browser = await launch_browser(pw, headless=self.settings.browser_headless)
                    try:
                        context = await browser.new_context(accept_downloads=False, service_workers="block")
                        # Restrict every network request made by the login browser.
                        async def guard(route):
                            try:
                                if urlsplit(route.request.url).scheme in {"data", "blob"}: return await route.continue_()
                                self.policy.same_origin(c["base_url"], route.request.url)
                                await self.policy.validate(route.request.url)
                                await route.continue_()
                            except BridgeError: await route.abort()
                        await context.route("**/*", guard)
                        page = await context.new_page()
                        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                        await page.locator(p.login.username_selector).fill(c["credentials"].get("username", ""))
                        await page.locator(p.login.password_selector).fill(c["credentials"].get("password", ""))
                        await page.locator(p.login.submit_selector).first.click()
                        await page.locator(p.login.success_selector).wait_for(state="visible", timeout=30_000 if self.settings.browser_headless else 180_000)
                        self.policy.same_origin(c["base_url"], page.url)
                        cookies = []
                        for cookie in await context.cookies():
                            cookies.append({"name": cookie["name"], "value": cookie["value"], "domain": cookie["domain"], "path": cookie["path"], "secure": cookie["secure"], "expires": int(cookie["expires"]) if cookie["expires"] > 0 else None})
                        csrf = await page.locator('input[type="hidden"][name]').evaluate_all('(nodes) => Object.fromEntries(nodes.map(n => [n.name,n.value]))')
                        self.store.set_session(identifier, {"cookies": cookies, "csrf": csrf}, "session_received")
                    finally: await browser.close()
            except PlaywrightError as exc:
                self.store.set_session(identifier, {}, "requires_action")
                raise BridgeError("browser_requires_action", "Login pelo navegador não confirmado. Revise seletores, credenciais e eventuais desafios. Nenhum bloqueio foi contornado.", 409) from exc
        if p.endpoints.get("list_clients") and p.endpoints["list_clients"].verified:
            await self.execute(identifier, "list_clients", {"start": 0, "length": 1, "search": "", "draw": 1})
            return {"status": "authenticated"}
        return {"status": "session_received"}
