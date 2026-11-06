"""Session login with DOM discovery, bounded redirects and positive verification.

No provider password is logged, no TLS check is disabled, no CAPTCHA is solved,
and credentials are submitted at most once per explicit connection attempt.
"""
from __future__ import annotations
import asyncio
import json
import os
import re
import ssl
import time
from urllib.parse import urljoin, urlsplit
import certifi
import httpx
from bs4 import BeautifulSoup
from soupsieve import SelectorSyntaxError
from .errors import BridgeError
from .models import Profile
from .network import limited_request


def tls_context():
    # httpx's certifi-only default ignores trusted enterprise roots on Windows.
    # Keep certificate/hostname verification and add certifi to the OS trust store.
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    return context


def select(node, selector):
    try:
        return node.select(selector)
    except SelectorSyntaxError as exc:
        raise BridgeError("login_selector_invalid", "Seletor de login inválido. Revise os campos avançados em Editar conexão.", 422) from exc


def html_redirect(text):
    soup = BeautifulSoup(text[:250_000], "html.parser")
    for meta in soup.select('meta[http-equiv][content]'):
        if meta.get("http-equiv", "").lower() == "refresh":
            match = re.fullmatch(r"\s*[0-5](?:\.0+)?\s*;\s*url\s*=\s*(.*?)\s*", meta["content"], re.I)
            if match:
                return match[1].strip("\"'")
    # Only a standalone, literal redirect. Never execute or infer arbitrary JS.
    for script in soup.select("script:not([src])"):
        match = re.fullmatch(r'''\s*(?:window\.)?location(?:\.href)?\s*=\s*(["'])([^"'\r\n]+)\1\s*;?\s*''', script.get_text())
        if match:
            return match[2]
    return None


def is_login_response(response):
    if "html" not in response.headers.get("content-type", "").lower():
        return False
    soup = BeautifulSoup(response.text[:250_000], "html.parser")
    redirect = html_redirect(response.text)
    if redirect and re.search(r"/(?:login|signin)(?:/|$)", urlsplit(redirect).path, re.I):
        return True
    for form in soup.select("form"):
        if form.select_one('input[type="password"]') and (
            form.select_one('input[name="username"],input[name="usuario"],input[autocomplete="username"]')
            or re.search(r"/(?:login|signin)(?:/|$)", response.url.path, re.I)
        ):
            return True
    return False


def safe_target(connector, base, current, location):
    return connector.policy.same_origin(base, urljoin(current, location))


async def follow(connector, connection, client, response):
    for _ in range(5):
        location = response.headers.get("location") if response.is_redirect else html_redirect(response.text) if "html" in response.headers.get("content-type", "").lower() else None
        if not location:
            return response
        target = safe_target(connector, connection["base_url"], str(response.url), location)
        await connector.policy.validate(target)
        # Even 307/308 do not replay the login body or password.
        response = await limited_request(client, connector.settings, "GET", target)
    raise BridgeError("too_many_redirects", "O painel excedeu cinco redirecionamentos no login.", 502)


async def login_page(connector, connection, client):
    profile = Profile.model_validate(connection["profile"])
    url = connector.policy.relative_url(connection["base_url"], profile.login.page)
    await connector.policy.validate(url)
    response = await limited_request(client, connector.settings, "GET", url)
    response = await follow(connector, connection, client, response)
    if response.status_code >= 400:
        raise BridgeError("login_unavailable", f"Página de login retornou HTTP {response.status_code}. Nenhuma senha foi enviada.", 502)
    return response, profile


def detect_form(html, login):
    soup = BeautifulSoup(html, "html.parser")
    forms = [form for form in select(soup, login.form_selector or "form") if form.select_one('input[type="password"]')]
    if len(forms) != 1:
        raise BridgeError("login_form_ambiguous" if forms else "login_form_missing", "Não foi possível identificar um único formulário de login. Use Inspecionar formulário ou informe o seletor em Editar conexão.", 409)
    form = forms[0]
    inputs = [item for item in form.select("input[name]") if not item.has_attr("disabled")]
    names = {item["name"] for item in inputs}
    password = login.password_field
    if not password:
        choices = [item["name"] for item in inputs if item.get("type", "text").lower() == "password"]
        if len(choices) == 1:
            password = choices[0]
    username = login.username_field
    if not username:
        candidates = [item for item in inputs if item.get("type", "text").lower() in {"text", "email", "tel"}]
        preferred = [item for item in candidates if item.get("autocomplete") == "username" or item["name"].lower() in {"username", "usuario", "user", "login", "email"}]
        choices = preferred or candidates
        if len(choices) == 1:
            username = choices[0]["name"]
    if not username or not password or username == password:
        raise BridgeError("login_fields_required", "Campos de usuário/senha ambíguos. Informe seus nomes em Editar conexão; nenhum login foi enviado.", 409)
    if username not in names or password not in names:
        raise BridgeError("login_fields_changed", "Os campos configurados não existem no formulário. Inspecione novamente ou deixe os nomes vazios para detectar automaticamente.", 409)
    return form, username, password


def logout_marker(html, base_url):
    soup = BeautifulSoup(html[:250_000], "html.parser")
    for link in soup.select("a[href],form[action]"):
        target = urlsplit(urljoin(base_url + "/", link.get("href") or link.get("action")))
        base = urlsplit(base_url)
        if (target.scheme, target.netloc) != (base.scheme, base.netloc):
            continue
        if re.search(r"(?:^|/)(?:logout|signout)(?:\.php)?(?:/|$)", target.path, re.I) or re.search(r"(?:^|&)(?:logout|signout)(?:=|&|$)", target.query, re.I):
            return True
    return False


def csrf_fields(html):
    soup = BeautifulSoup(html[:250_000], "html.parser")
    fields = {i["name"]: i.get("value", "") for i in soup.select('input[type="hidden"][name]')}
    for meta in soup.select("meta[name][content]"):
        if "csrf" in meta["name"].lower():
            fields[meta["name"]] = meta["content"]
    return fields


def network_error(exc, stage):
    # Inspect exception types/causes internally, but never echo URLs or bodies.
    chain, current = [], exc
    for _ in range(5):
        if current is None:
            break
        chain.append(current)
        current = current.__cause__ or current.__context__
    if any(isinstance(e, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(e) for e in chain):
        return BridgeError("login_tls_error", f"Falha ao verificar o certificado TLS ({stage}). Confira a cadeia do servidor e os certificados confiáveis do Windows/antivírus. A validação TLS não foi desativada.", 502)
    if isinstance(exc, httpx.TimeoutException):
        return BridgeError("login_timeout", f"O painel não respondeu no prazo ({stage}). Nenhuma tentativa de login foi repetida.", 504)
    if isinstance(exc, httpx.ConnectError):
        return BridgeError("login_connect_error", f"Não foi possível estabelecer a conexão com o painel ({stage}). Verifique rede, firewall e endereço. Nenhuma tentativa adicional foi feita.", 502)
    return BridgeError("login_network_error", f"Falha de comunicação com o painel ({stage}). Nenhuma tentativa automática adicional foi feita.", 502)


async def inspect_login(connector, identifier):
    async with connector.lock(identifier):
        c = connector.store.connection(identifier, True)
        try:
            async with connector.client(c) as client:
                response, profile = await login_page(connector, c, client)
                soup = BeautifulSoup(response.text, "html.parser")
                forms = []
                for form in soup.select("form"):
                    action = safe_target(connector, c["base_url"], str(response.url), form.get("action") or str(response.url))
                    parts = urlsplit(action)
                    forms.append({"method": form.get("method", "GET").upper(), "action_path": parts.path, "fields": [{"name": i.get("name"), "type": i.get("type", "text")} for i in form.select("input[name],select[name],textarea[name]")]})
                suggestion = None
                try:
                    automatic = profile.login.model_copy(update={"username_field": "", "password_field": ""})
                    form, username, password = detect_form(response.text, automatic)
                    suggestion = {**profile.login.model_dump(), "username_field": username, "password_field": password,
                                  "username_selector": "input[name=" + json.dumps(username) + "]",
                                  "password_selector": "input[name=" + json.dumps(password) + "]"}
                    if form.get("id"):
                        suggestion["form_selector"] = "form[id=" + json.dumps(form["id"]) + "]"
                except BridgeError:
                    pass
                return {"forms": forms, "suggested_login": suggestion, "note": "Somente leitura. Cookies, valores ocultos, senha e token não são expostos. Use Aplicar campos detectados para salvar a configuração local."}
        except httpx.HTTPError as exc:
            raise network_error(exc, "leitura do formulário") from exc


async def confirm_session(connector, c, profile, client, session, ui_confirmed):
    from .connector import save_cookies
    endpoint = profile.endpoints.get("list_clients")
    probe = None
    if endpoint and endpoint.verified:
        prepared, url, kwargs = connector.prepare({**c, "session": session}, "list_clients", {"start": 0, "length": 1, "search": "", "draw": 1})
        await connector.policy.validate(url)
        response = await limited_request(client, connector.settings, prepared.method, url, **kwargs)
        probe = connector.decode(response, "list_clients", prepared)
    elif urlsplit(c["base_url"]).hostname == "servip2p.com" and endpoint and endpoint.path == "/clients/api/?get_clients" and endpoint.method == "GET":
        # This read-only URL was supplied by the account owner in the Network capture.
        # Do not infer write endpoints or enable unverified commercial operations.
        url = connector.policy.relative_url(c["base_url"], endpoint.path)
        await connector.policy.validate(url)
        response = await limited_request(client, connector.settings, "GET", url, params={"draw": 1, "start": 0, "length": 1})
        if response.status_code == 200:  # Some PHP installations label JSON as text/html; validate the body strictly.
            try:
                data = response.json()
            except ValueError:
                data = None
            if isinstance(data, dict) and isinstance(data.get("data"), list) and all(type(data.get(k)) is int and data[k] >= 0 for k in ("recordsTotal", "recordsFiltered")):
                probe = {"confirmed_by": "observed_clients_json", "mapping_required": True}
    if probe is not None:
        session["cookies"] = save_cookies(client)
        connector.store.set_session(c["id"], session, "authenticated")
        return {"status": "authenticated", "probe": probe, "message": "Login confirmado por consulta JSON autenticada. Os contratos de alteração continuam sujeitos à validação."}
    if ui_confirmed and session.get("cookies"):
        connector.store.set_session(c["id"], session, "session_received")
        return {"status": "session_received", "message": "Login confirmado na página do painel e sessão salva. A consulta de clientes ainda precisa ser validada no perfil; nenhuma operação comercial foi habilitada."}
    raise BridgeError("login_unconfirmed", "O painel não forneceu evidência suficiente de autenticação. Confira credenciais/desafios ou configure uma consulta autenticada ou seletor de sucesso em Editar conexão.", 409)


async def connect(connector, identifier):
    c = connector.store.connection(identifier, True)
    if c["auth_mode"] == "token":
        result = await connector.execute(identifier, "list_clients", {"start": 0, "length": 1, "search": "", "draw": 1})
        return {"status": "authenticated", "probe": result}
    if c["auth_mode"] == "browser":
        return await browser_login(connector, identifier)
    async with connector.lock(identifier):
        c = connector.store.connection(identifier, True)
        if not c["credentials"].get("username") or not c["credentials"].get("password"):
            raise BridgeError("credentials_missing", "Informe usuário e senha em Editar conexão. Campos em branco preservam os valores existentes.", 409)
        stage = "leitura do formulário"
        try:
            # A new authentication attempt does not reuse the previous account session.
            async with connector.client({**c, "session": {}}) as client:
                response, profile = await login_page(connector, c, client)
                form, username, password = detect_form(response.text, profile.login)
                if form.get("method", "GET").upper() != "POST":
                    raise BridgeError("login_method_unverified", "O formulário não declara POST. Selecione Login com navegador em Editar conexão; a senha não será enviada na URL.", 409)
                if form.select_one('.h-captcha,.g-recaptcha,iframe[src*="captcha"]'):
                    raise BridgeError("login_challenge_required", "O formulário exige CAPTCHA. Use o fluxo autorizado do painel; não houve envio automático de credenciais.", 409)
                action = safe_target(connector, c["base_url"], str(response.url), form.get("action") or str(response.url))
                hidden = {i["name"]: i.get("value", "") for i in form.select('input[type="hidden"][name]') if not i.has_attr("disabled")}
                body = {**hidden, **profile.login.extra_fields, username: c["credentials"]["username"], password: c["credentials"]["password"]}
                await connector.policy.validate(action)
                stage = "envio único do formulário"
                result = await limited_request(client, connector.settings, "POST", action, data=body, headers={"Origin": c["base_url"], "Referer": str(response.url)})
                stage = "redirecionamento após login"
                result = await follow(connector, c, client, result)
                if result.status_code >= 400 or is_login_response(result):
                    raise BridgeError("login_requires_action", f"Login não confirmado pelo painel (HTTP {result.status_code}). Verifique usuário, senha, CSRF ou desafio. Nenhum envio foi repetido.", 401)
                from .connector import save_cookies
                session = {"cookies": save_cookies(client), "csrf": csrf_fields(result.text)}
                soup = BeautifulSoup(result.text, "html.parser")
                positive = bool(select(soup, profile.login.success_selector)) if profile.login.success_selector else logout_marker(result.text, c["base_url"])
                stage = "verificação da sessão"
                return await confirm_session(connector, c, profile, client, session, positive)
        except httpx.HTTPError as exc:
            connector.store.set_session(identifier, {}, "requires_action")
            raise network_error(exc, stage) from exc
        except BridgeError:
            connector.store.set_session(identifier, {}, "requires_action")
            raise


async def capture_browser(connector, c, profile):
    from playwright.async_api import async_playwright, Error as PlaywrightError, TimeoutError as PlaywrightTimeout
    from .browser_support import launch_browser
    login = profile.login
    stage = "abertura do navegador"
    try:
        async with async_playwright() as pw:
            browser = await launch_browser(pw, headless=connector.settings.browser_headless)
            try:
                context = await browser.new_context(accept_downloads=False, service_workers="block")
                async def guard(route):
                    try:
                        if urlsplit(route.request.url).scheme in {"data", "blob"}:
                            return await route.continue_()
                        connector.policy.same_origin(c["base_url"], route.request.url)
                        await connector.policy.validate(route.request.url)
                        await route.continue_()
                    except BridgeError:
                        await route.abort()
                await context.route("**/*", guard)
                page = await context.new_page()
                page.set_default_timeout(30_000)
                url = connector.policy.relative_url(c["base_url"], login.page)
                await connector.policy.validate(url)
                stage = "abertura do formulário"
                await page.goto(url, wait_until="domcontentloaded")
                initial_url = page.url
                connector.policy.same_origin(c["base_url"], initial_url)
                form, username, password = detect_form(await page.content(), login)
                connector.policy.same_origin(c["base_url"], urljoin(page.url, form.get("action") or page.url))
                # Default selectors follow the detected form; custom selectors remain explicit.
                user_selector = login.username_selector
                if not user_selector or user_selector == 'input[name="username"]':
                    user_selector = "input[name=" + json.dumps(username) + "]"
                password_selector = login.password_selector or "input[name=" + json.dumps(password) + "]"
                scope = page.locator(login.form_selector or "form").filter(has=page.locator('input[type="password"]'))
                stage = "preenchimento dos campos"
                await scope.locator(user_selector).fill(c["credentials"]["username"])
                await scope.locator(password_selector).fill(c["credentials"]["password"])
                stage = "envio único do login"
                await scope.locator(login.submit_selector or 'button[type="submit"],input[type="submit"]').first.click()
                stage = "confirmação do login"
                deadline = time.monotonic() + (30 if connector.settings.browser_headless else 180)
                positive = False
                transitioned = False
                html = ""
                while time.monotonic() < deadline:
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=5000)
                        snapshot_url = page.url
                        connector.policy.same_origin(c["base_url"], snapshot_url)
                        html = await page.content()
                        visible_password = await page.locator('form input[type="password"]:visible').count()
                        explicit = bool(login.success_selector) and await page.locator(login.success_selector).first.is_visible()
                        alert = await page.locator('.alert-danger:visible,.alert-error:visible,[role="alert"]:visible').count()
                        if page.url != snapshot_url:
                            await asyncio.sleep(0.1)
                            continue
                        marker = logout_marker(html, c["base_url"])
                        positive = not visible_password and (explicit or marker)
                        transitioned = page.url != initial_url and not visible_password
                        if positive or (transitioned and profile.endpoints.get("list_clients")):
                            break
                        if alert and visible_password:
                            raise BridgeError("login_requires_action", "O painel exibiu um aviso e manteve o formulário de login. Confira credenciais ou desafio; nenhuma tentativa foi repetida.", 401)
                    except PlaywrightError as exc:
                        # A meta-refresh may replace the execution context between
                        # DOM reads. Wait for it; never click or POST a second time.
                        transient = any(message in str(exc).lower() for message in (
                            "page is navigating", "execution context was destroyed",
                            "cannot find context with specified id", "most likely because of a navigation"))
                        if page.is_closed() or not transient:
                            raise
                    await asyncio.sleep(0.25)
                if not (positive or transitioned):
                    raise BridgeError("browser_login_unconfirmed", "O navegador enviou o login uma vez, mas o painel não confirmou a entrada. Confira credenciais, CAPTCHA/2FA e os seletores em Editar conexão.", 409)
                cookies = [{"name": x["name"], "value": x["value"], "domain": x["domain"], "path": x["path"], "secure": x["secure"], "expires": int(x["expires"]) if x["expires"] > 0 else None, "rest": {"HttpOnly": x.get("httpOnly", False)}} for x in await context.cookies(c["base_url"])]
                return {"cookies": cookies, "csrf": csrf_fields(html), "user_agent": await page.evaluate("navigator.userAgent")}, positive
            finally:
                await browser.close()
    except PlaywrightTimeout as exc:
        raise BridgeError("browser_login_timeout", f"Tempo esgotado no navegador ({stage}). Revise a página e os campos em Editar conexão. O login não foi reenviado.", 504) from exc
    except PlaywrightError as exc:
        raise BridgeError("browser_requires_action", f"Falha no navegador ({stage}). Confira endereço, campos e eventuais desafios. Nenhum bloqueio foi contornado e nenhum login foi repetido.", 409) from exc


async def browser_login(connector, identifier):
    if not connector.settings.browser_enabled:
        raise BridgeError("browser_disabled", "Autenticação por navegador desabilitada nesta instância.", 409)
    async with connector.lock(identifier):
        c = connector.store.connection(identifier, True)
        if not c["credentials"].get("username") or not c["credentials"].get("password"):
            raise BridgeError("credentials_missing", "Informe usuário e senha em Editar conexão.", 409)
        profile = Profile.model_validate(c["profile"])
        try:
            if os.name == "nt":
                # Windows subprocess support is not available in SelectorEventLoop.
                # Keep Playwright on a dedicated Proactor loop, away from the API loop.
                def capture():
                    with asyncio.Runner(loop_factory=asyncio.ProactorEventLoop) as runner:
                        return runner.run(capture_browser(connector, c, profile))
                session, positive = await asyncio.to_thread(capture)
            else:
                session, positive = await capture_browser(connector, c, profile)
            async with connector.client({**c, "session": session}) as client:
                return await confirm_session(connector, c, profile, client, session, positive)
        except ImportError as exc:
            raise BridgeError("browser_unavailable", "Distribuição incompleta: navegador integrado ausente. Use o pacote completo da aplicação.", 503) from exc
        except httpx.HTTPError as exc:
            connector.store.set_session(identifier, {}, "requires_action")
            raise network_error(exc, "verificação da sessão do navegador") from exc
        except BridgeError:
            connector.store.set_session(identifier, {}, "requires_action")
            raise
