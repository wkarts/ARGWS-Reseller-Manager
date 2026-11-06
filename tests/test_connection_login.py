import asyncio
import ssl
import httpx
import pytest
from bs4 import BeautifulSoup
from app.errors import BridgeError
from app.models import Login
from app.login_support import detect_form, html_redirect, is_login_response, logout_marker, network_error, tls_context
from tests.conftest import connection, profile


FORM='<form id="form-login" method="POST"><input type="hidden" name="try_login" value="1"><input type="hidden" name="csrf_token" value="SECRET_CSRF"><input name="username"><input name="password" type="password"><button type="submit">Entrar</button></form>'


def test_discover_actual_form_shape_without_fixed_hidden_values():
    form,username,password=detect_form(FORM,Login())
    assert (username,password)==('username','password')
    assert form['id']=='form-login'


def test_ambiguous_form_fails_closed():
    with pytest.raises(BridgeError) as result: detect_form(FORM+FORM,Login())
    assert result.value.code=='login_form_ambiguous'
    with pytest.raises(BridgeError): detect_form(FORM,Login(form_selector='[['))
    with pytest.raises(BridgeError): detect_form(FORM,Login(username_field='absent'))


@pytest.mark.parametrize('html', ['<meta http-equiv="refresh" content="0; url=/home/">','<script>window.location.href = "/home/";</script>',"<script>location='/home/';</script>"])
def test_literal_html_redirects(html):
    assert html_redirect(html)=='/home/'


def test_does_not_execute_conditional_javascript_or_follow_slow_redirects():
    assert html_redirect('<script>if (error) window.location.href="/login/";</script>') is None
    assert html_redirect('<meta http-equiv="refresh" content="60;url=/home/">') is None


def test_dashboard_login_string_is_not_a_login_response():
    request=httpx.Request('GET','https://panel.example/home/')
    response=httpx.Response(200,text='<script>const signIn="/login/";</script><a href="/logout/">Sair</a>',headers={'Content-Type':'text/html'},request=request)
    assert not is_login_response(response)
    assert logout_marker(response.text,'https://panel.example')
    assert not logout_marker('<a href="https://evil.example/logout/">Sair</a>','https://panel.example')
    assert not logout_marker('<a href="/logout-help">Ajuda</a>','https://panel.example')


def test_default_form_names_are_discovered_and_csrf_is_preserved(env):
    client,app,panel,_=env
    contract=profile();contract['login']={'page':'/login/'}
    identifier=connection(client,mode='form',contract=contract)
    result=client.post(f'/api/v1/connections/{identifier}/connect')
    assert result.status_code==200,result.text
    assert result.json()['status']=='authenticated'
    assert panel.logins==1
    assert app.state.store.connection(identifier,True)['session']['csrf']['csrf']=='operation-csrf'


def test_form_inspection_suggests_fields_without_exposing_tokens(env):
    client,_,panel,_=env
    identifier=connection(client,mode='form')
    result=client.get(f'/api/v1/connections/{identifier}/login-form')
    assert result.status_code==200
    assert result.json()['suggested_login']['username_field']=='usuario'
    assert 'login-csrf' not in result.text and 'AUTH_SESSION' not in result.text
    assert panel.logins==0


def test_html_login_redirect_is_followed_once_with_no_post_replay(env):
    client,app,panel,_=env
    original=panel.__call__
    def handler(request):
        response=original(request)
        if request.method=='POST' and request.url.path=='/login/':
            return httpx.Response(200,text='<meta http-equiv="Refresh" content="0;url=/home/">',headers={'Set-Cookie':'PHPSESSID=AUTH_SESSION; Path=/; Secure','Content-Type':'text/html'})
        return response
    app.state.connector.transport=httpx.MockTransport(handler)
    identifier=connection(client,mode='form')
    result=client.post(f'/api/v1/connections/{identifier}/connect')
    assert result.status_code==200,result.text
    assert result.json()['status']=='authenticated' and panel.logins==1


def test_relative_action_resolves_from_document_not_site_root(env):
    client,app,panel,_=env
    def handler(request):
        if request.url.path=='/nested/login/' and request.method=='GET':
            return httpx.Response(200,text='<form method="POST" action="submit"><input name="usuario"><input type="password" name="senha"></form>',headers={'Content-Type':'text/html'})
        if request.method=='POST':
            assert request.url.path=='/nested/login/submit'
            assert b'usuario=upstream-user' in request.content
            return httpx.Response(200,text='<a href="/logout/">Sair</a>',headers={'Set-Cookie':'PHPSESSID=AUTH_SESSION; Path=/; Secure','Content-Type':'text/html'})
        return panel(request)
    app.state.connector.transport=httpx.MockTransport(handler)
    contract=profile();contract['login']['page']='/nested/login/'
    identifier=connection(client,mode='form',contract=contract)
    assert client.post(f'/api/v1/connections/{identifier}/connect').status_code==200


def test_timeout_and_tls_errors_are_specific_and_sanitized(env):
    client,app,_,_=env
    identifier=connection(client,mode='form')
    for exception,code in [(httpx.ReadTimeout('SECRET_IN_EXCEPTION'),'login_timeout'),(httpx.ConnectError('CERTIFICATE_VERIFY_FAILED SECRET_IN_EXCEPTION'),'login_tls_error')]:
        def handler(request): raise exception
        app.state.connector.transport=httpx.MockTransport(handler)
        result=client.post(f'/api/v1/connections/{identifier}/connect')
        assert result.json()['error']['code']==code
        assert 'SECRET_IN_EXCEPTION' not in result.text
        assert app.state.store.connection(identifier)['status']=='requires_action'
    context=tls_context()
    assert context.verify_mode==ssl.CERT_REQUIRED and context.check_hostname


def test_external_redirect_blocked_before_credentials_leave_origin(env):
    client,app,panel,_=env
    def handler(request):
        if request.method=='POST':
            return httpx.Response(200,text='<meta http-equiv="refresh" content="0;url=https://evil.example/login/">',headers={'Content-Type':'text/html'})
        assert request.url.host=='panel.example'
        return panel(request)
    app.state.connector.transport=httpx.MockTransport(handler)
    identifier=connection(client,mode='form')
    result=client.post(f'/api/v1/connections/{identifier}/connect')
    assert result.json()['error']['code']=='external_redirect'


def test_browser_without_success_selector_reaches_capture_not_contract_error(env,monkeypatch):
    client,app,_,_=env
    from app import login_support
    async def capture(*args):
        raise BridgeError('fixture_capture_reached','Navegador de teste alcançado',409)
    monkeypatch.setattr(login_support,'capture_browser',capture)
    identifier=connection(client,mode='browser')
    result=client.post(f'/api/v1/connections/{identifier}/connect')
    assert result.json()['error']['code']=='fixture_capture_reached'


def test_blank_200_is_never_authentication_success(env):
    client,app,panel,_=env
    def handler(request):
        if request.method=='POST': return httpx.Response(200,text='<h1>OK</h1>',headers={'Content-Type':'text/html'})
        return panel(request)
    app.state.connector.transport=httpx.MockTransport(handler)
    contract=profile();contract['endpoints']={}
    identifier=connection(client,mode='form',contract=contract)
    response=client.post(f'/api/v1/connections/{identifier}/connect')
    assert response.status_code==409
    assert response.json()['error']['code']=='login_unconfirmed'
    assert app.state.store.connection(identifier,True)['session']=={}
