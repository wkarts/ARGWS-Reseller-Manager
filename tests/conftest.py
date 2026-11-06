from pathlib import Path
import json
import pytest
import httpx
from fastapi.testclient import TestClient
from app.main import create_app
from app.settings import Settings


def profile():
    return {
      "name":"CONTRATO SINTÉTICO — SOMENTE TESTES",
      "token_auth":{"location":"header","name":"X-Panel-Key","prefix":""},
      "login":{"page":"/login/","username_field":"usuario","password_field":"senha"},
      "endpoints":{
        "list_clients":{"method":"GET","path":"/clients/api/?get_clients","params":{"start":"{{input.start}}","length":"{{input.length}}","search[value]":"{{input.search}}"},"verified":True,"evidence":"Fixture sintética; não é documentação kOffice.","data_path":"data","fields":{"id":"0","username":"1","expires_at":"3","plan":"4","screens":"5","technology":"6"}},
        "get_client":{"method":"GET","path":"/synthetic/clients/{{input.client_id}}","required":["client_id"],"verified":True,"evidence":"Fixture sintética","data_path":"data","fields":{"id":"id","username":"username"}},
        "renew_client":{"method":"POST","path":"/synthetic/renew","encoding":"json","body":{"client_id":"{{input.client_id}}","plan_id":"{{input.plan_id}}"},"required":["client_id","plan_id"],"verified":True,"evidence":"Fixture sintética","success_path":"success","success_value":True},
        "create_client":{"method":"POST","path":"/synthetic/create","encoding":"form","body":{"username":"{{input.username}}","password":"{{input.password}}"},"required":["username","password"],"verified":True,"evidence":"Fixture sintética","success_path":"success","success_value":True}
      }}


class Panel:
    def __init__(self):
        self.requests=[];self.writes=0;self.mode="ok";self.expire=False;self.logins=0
    def __call__(self,r):
        self.requests.append((r.method,str(r.url),r.content))
        if r.url.host=="hooks.example": return httpx.Response(204)
        if r.url.path=="/login/" and r.method=="GET":
            if self.mode=="external_form":return httpx.Response(200,text='<form method="post" action="https://evil.example/login"><input name="usuario"><input name="senha" type="password"></form>',headers={"Content-Type":"text/html"})
            return httpx.Response(200,text='<form method="post" action="/login/"><input name="usuario"><input name="senha" type="password"><input type="hidden" name="csrf" value="login-csrf"></form>',headers={"Content-Type":"text/html","Set-Cookie":"pre_session=start; Path=/; Secure"})
        if r.url.path=="/login/" and r.method=="POST":
            assert b"usuario=upstream-user" in r.content and b"senha=upstream-password" in r.content and b"csrf=login-csrf" in r.content
            self.logins+=1;self.expire=False
            return httpx.Response(303,headers={"Location":"/home/","Set-Cookie":"PHPSESSID=AUTH_SESSION; Path=/; Secure; HttpOnly"})
        if r.url.path=="/home/":
            return httpx.Response(200,text='<div id="home">Connected</div><input type="hidden" name="csrf" value="operation-csrf">',headers={"Content-Type":"text/html"})
        authorized=(r.headers.get("X-Panel-Key")=="upstream-token" or "PHPSESSID=AUTH_SESSION" in r.headers.get("cookie", "")) and not self.expire
        if not authorized:
            return httpx.Response(200,text='<meta http-equiv="Refresh" content="0;url=/login/"><script>window.location.href="/login/";</script>',headers={"Content-Type":"text/html"})
        if r.url.path=="/clients/api/":
            if self.mode=="bad_json":return httpx.Response(200,text="<p>Not JSON</p>")
            if self.mode=="missing_data":return httpx.Response(200,json={"other":[]})
            return httpx.Response(200,json={"draw":1,"recordsTotal":2,"recordsFiltered":2,"data":[["c1","cliente-1","CUSTOMER_SECRET","2030-12-31","p1",2,"P2P"],["c2","<b>cliente-2</b>","CUSTOMER_SECRET_2","2030-12-31","p2",1,"IPTV"]]})
        if r.url.path.startswith("/synthetic/clients/"):
            return httpx.Response(200,json={"data":{"id":"c1","username":"cliente-1","password":"SECRET"}})
        if r.url.path.startswith("/synthetic/") and r.method=="POST":
            self.writes+=1
            if self.mode=="timeout":raise httpx.ReadTimeout("Simulated after commit",request=r)
            if self.mode=="http500":return httpx.Response(500,json={"error":"unavailable"})
            if self.mode=="false":return httpx.Response(200,json={"success":False})
            if self.mode=="integer":return httpx.Response(200,json={"success":1})
            return httpx.Response(200,json={"success":True,"password":"DO_NOT_RETURN"})
        return httpx.Response(404)


@pytest.fixture
def env(tmp_path):
    panel=Panel()
    settings=Settings(data_dir=tmp_path,allowed_hosts=("panel.example","hooks.example"),worker_enabled=False,test_network=True)
    app=create_app(settings,httpx.MockTransport(panel))
    with TestClient(app) as client:
        token=(tmp_path/"admin.token").read_text().strip()
        client.headers["Authorization"]="Bearer "+token
        yield client, app, panel, token


def connection(client,mode="token",name="Conexão A",contract=None):
    r=client.post('/api/v1/connections',json={"name":name,"base_url":"https://panel.example","auth_mode":mode,"credentials":{"token":"upstream-token","username":"upstream-user","password":"upstream-password"},"profile":contract or profile()})
    assert r.status_code==201,r.text
    return r.json()['id']
