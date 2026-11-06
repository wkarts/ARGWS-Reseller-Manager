"""Apply refinements found by real-browser regression tests before preparation."""
from pathlib import Path
import runpy

p = Path('app/login_support.py')
s = p.read_text(encoding='utf-8')
start = s.index('                while time.monotonic() < deadline:')
end = s.index('                if not (positive or transitioned):', start)
s = s[:start] + '''                html = ""
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
''' + s[end:]
s = s.replace('"csrf": csrf_fields(await page.content()), "user_agent": await page.evaluate("navigator.userAgent")', '"csrf": csrf_fields(html), "user_agent": await page.evaluate("navigator.userAgent")')
s = s.replace('if response.status_code == 200 and "json" in response.headers.get("content-type", "").lower():', 'if response.status_code == 200:  # Some PHP installations label JSON as text/html; validate the body strictly.')
p.write_text(s,encoding='utf-8')

p = Path('tests/test_browser_release.py')
s = p.read_text(encoding='utf-8')
a=s.index('def test_browser_connection_reaches_contract_validation_without_opt_in(')
b=s.index('\ndef test_missing_bundled_browser',a)
s=s[:a]+'''def test_browser_connection_reaches_login_without_opt_in(env, monkeypatch):
    from app import login_support
    client, app, panel, token = env
    attempts = []
    async def capture(connector, current, profile):
        attempts.append(current["id"])
        assert not profile.login.success_selector
        raise BridgeError("synthetic_login_reached", "Login de teste alcançado", 409)
    monkeypatch.setattr(login_support, "capture_browser", capture)
    identifier = connection(client, mode="browser")
    result = client.post(f"/api/v1/connections/{identifier}/connect")
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "synthetic_login_reached"
    assert attempts == [identifier]
    assert not panel.requests

''' + s[b:]
p.write_text(s,encoding='utf-8')
p=Path('tests/test_core.py')
s=p.read_text(encoding='utf-8')
s=s.replace('def test_form_fields_must_be_confirmed(env):','def test_explicit_form_fields_must_exist_before_submitting(env):')
s=s.replace("pr['login']['username_field']='';cid=connection(c,mode='form',contract=pr)","pr['login']['username_field']='field_not_present';cid=connection(c,mode='form',contract=pr)")
p.write_text(s,encoding='utf-8')
p=Path('scripts/_prepare_connection_fix.py')
s=p.read_text(encoding='utf-8')
s=s.replace("changed = {'app/connection_management.py',", "changed = {'tests/test_browser_release.py', 'tests/test_core.py', 'app/connection_management.py',")
p.write_text(s,encoding='utf-8')
runpy.run_path(str(p),run_name='__main__')
