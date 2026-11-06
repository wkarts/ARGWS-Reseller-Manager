import asyncio
import json
from datetime import datetime,timezone,timedelta
import sqlite3
import pytest
from pydantic import ValidationError
from app.models import Profile, Endpoint, TokenAuth
from app.settings import Settings
from app.security import InstanceLock
from app.errors import BridgeError
from app.store import Store
from app.connector import render
from app.importers import inspect_document
from .conftest import connection,profile


def write(client,cid,key='test-key-0001',params=None,confirmed=True):
    return client.post(f'/api/v1/connections/{cid}/operations/renew_client',headers={'Idempotency-Key':key},json={'parameters':params or {'client_id':'c1','plan_id':'p1'},'confirmed':confirmed})


def test_health_public_and_auth_required(env):
    c,a,p,t=env
    assert c.get('/health').json()['status']=='ok'
    assert c.get('/api/v1/me',headers={'Authorization':'Bearer invalid'}).status_code==401
    assert c.get('/api/v1/me').json()['scope']=='admin'
    assert c.get('/openapi.json').status_code==200


def test_secrets_never_returned_or_plain_in_db(env):
    c,a,p,t=env;cid=connection(c)
    response=c.get('/api/v1/connections/'+cid)
    assert 'upstream-password' not in response.text and 'upstream-token' not in response.text
    with a.state.store.db() as db:
        r=db.execute('SELECT credentials FROM connections WHERE id=?',(cid,)).fetchone()
        assert 'upstream-password' not in r['credentials']
    assert c.get('/api/v1/tokens').json()[0].get('hash') is None


def test_token_listing_projects_and_sanitizes(env):
    c,a,p,t=env;cid=connection(c)
    r=c.get(f'/api/v1/connections/{cid}/clients')
    assert r.status_code==200,r.text
    assert r.json()['data'][0]['id']=='c1'
    assert r.json()['data'][1]['username']=='cliente-2'
    assert 'CUSTOMER_SECRET' not in r.text and '<b>' not in r.text
    assert 'start=0' in p.requests[-1][1]
    cached=c.get(f'/api/v1/connections/{cid}/clients?cached=true').json()
    assert cached['total']==2 and cached['source']=='local_cache'


def test_no_guessing_field_indices(env):
    c,a,p,t=env;pr=profile();pr['endpoints']['list_clients']['fields']={};cid=connection(c,contract=pr)
    r=c.get(f'/api/v1/connections/{cid}/clients').json()
    assert r['mapping_required'] and r['data']==[] and r['received_count']==2


def test_login_html_200_is_not_success(env):
    c,a,p,t=env;cid=connection(c);p.expire=True
    r=c.get(f'/api/v1/connections/{cid}/clients')
    assert r.status_code==401 and r.json()['error']['code']=='authentication_required'
    assert a.state.store.connection(cid)['status']=='expired'


def test_token_header_not_presumed(env):
    c,a,p,t=env;pr=profile();pr['token_auth']['name']='';cid=connection(c,contract=pr)
    r=c.get(f'/api/v1/connections/{cid}/clients')
    assert r.status_code==409 and not p.requests


def test_unverified_endpoint_never_sent(env):
    c,a,p,t=env;pr=profile();pr['endpoints']['list_clients']['verified']=False;cid=connection(c,contract=pr)
    assert c.get(f'/api/v1/connections/{cid}/clients').status_code==409
    assert not p.requests


def test_form_login_preserves_cookies_and_csrf(env):
    c,a,p,t=env;cid=connection(c,mode='form')
    inspected=c.get(f'/api/v1/connections/{cid}/login-form')
    assert inspected.status_code==200 and 'login-csrf' not in inspected.text
    r=c.post(f'/api/v1/connections/{cid}/connect')
    assert r.status_code==200,r.text
    assert r.json()['status']=='authenticated' and p.logins==1
    data=a.state.store.connection(cid,True)
    assert data['session']['csrf']['csrf']=='operation-csrf'
    assert 'AUTH_SESSION' not in c.get(f'/api/v1/connections/{cid}').text
    assert c.get(f'/api/v1/connections/{cid}/clients').status_code==200


def test_external_form_action_blocked(env):
    c,a,p,t=env;cid=connection(c,mode='form');p.mode='external_form'
    r=c.post(f'/api/v1/connections/{cid}/connect')
    assert r.status_code==502 and p.logins==0
    assert len(p.requests)==1


def test_form_fields_must_be_confirmed(env):
    c,a,p,t=env;pr=profile();pr['login']['username_field']='';cid=connection(c,mode='form',contract=pr)
    assert c.post(f'/api/v1/connections/{cid}/connect').status_code==409 and p.logins==0


def test_scoped_tokens_isolate_connections(env):
    c,a,p,t=env;c1=connection(c);c2=connection(c,name='B')
    key=c.post('/api/v1/tokens',json={'name':'read A','scope':'read','connection_ids':[c1]}).json()['token']
    h={'Authorization':'Bearer '+key}
    assert len(c.get('/api/v1/connections',headers=h).json())==1
    assert c.get(f'/api/v1/connections/{c2}',headers=h).status_code==403
    assert 'profile' not in c.get(f'/api/v1/connections/{c1}',headers=h).json()
    assert c.post(f'/api/v1/connections/{c1}/connect',headers=h).status_code==403
    assert c.post('/api/v1/tokens',headers=h,json={'name':'evil','scope':'admin'}).status_code==403


def test_idempotency_and_only_one_mutation(env):
    c,a,p,t=env;cid=connection(c)
    first=write(c,cid);assert first.status_code==202,first.text
    second=write(c,cid);assert second.json()['id']==first.json()['id']
    asyncio.run(a.state.worker.step())
    assert p.writes==1
    third=write(c,cid);assert third.json()['status']=='succeeded'
    asyncio.run(a.state.worker.step());assert p.writes==1
    assert 'DO_NOT_RETURN' not in c.get('/api/v1/operations').text


def test_idempotency_conflict(env):
    c,a,p,t=env;cid=connection(c);write(c,cid)
    r=write(c,cid,params={'client_id':'c1','plan_id':'different'})
    assert r.status_code==409 and r.json()['error']['code']=='idempotency_conflict'


def test_busy_client_protection(env):
    c,a,p,t=env;cid=connection(c);write(c,cid)
    assert write(c,cid,key='different-key').status_code==409
    assert write(c,cid,key='different-other-client',params={'client_id':'c2','plan_id':'p2'}).status_code==202


@pytest.mark.parametrize('mode',['timeout','http500','false','integer'])
def test_uncertain_mutation_never_retries(env,mode):
    c,a,p,t=env;cid=connection(c);op=write(c,cid).json();p.mode=mode
    asyncio.run(a.state.worker.step())
    assert a.state.store.operation(op['id'])['status']=='reconciliation_required'
    asyncio.run(a.state.worker.step());assert p.writes==1
    assert write(c,cid,key='do-not-repeat-this').status_code==409


def test_restart_moves_running_to_reconcile(env):
    c,a,p,t=env;cid=connection(c);op=write(c,cid).json()
    a.state.store.claim();a.state.store.recover()
    assert a.state.store.operation(op['id'])['status']=='reconciliation_required'
    asyncio.run(a.state.worker.step());assert p.writes==0


def test_profile_revision_conflict_and_job_guard(env):
    c,a,p,t=env;cid=connection(c);op=write(c,cid).json()
    r=c.put(f'/api/v1/connections/{cid}/profile',json={'revision':1,'profile':profile()});assert r.status_code==200
    assert c.put(f'/api/v1/connections/{cid}/profile',json={'revision':1,'profile':profile()}).status_code==409
    asyncio.run(a.state.worker.step())
    assert a.state.store.operation(op['id'])['error_code']=='profile_changed' and p.writes==0


def test_reconciliation_requires_evidence_and_uncertain_status(env):
    c,a,p,t=env;cid=connection(c);op=write(c,cid).json()
    assert c.post(f"/api/v1/operations/{op['id']}/reconcile",json={'outcome':'succeeded','evidence':'Conferência no painel manual.'}).status_code==409
    p.mode='timeout';asyncio.run(a.state.worker.step())
    r=c.post(f"/api/v1/operations/{op['id']}/reconcile",json={'outcome':'succeeded','evidence':'Vencimento conferido no painel; crédito debitado uma vez.'})
    assert r.status_code==200 and r.json()['status']=='succeeded' and p.writes==1


def test_cancel_queue_no_remote_side_effect(env):
    c,a,p,t=env;cid=connection(c);op=write(c,cid).json()
    assert c.post(f"/api/v1/operations/{op['id']}/cancel").json()['status']=='cancelled'
    asyncio.run(a.state.worker.step());assert p.writes==0


def test_explicit_confirmation_required(env):
    c,a,p,t=env;cid=connection(c)
    assert write(c,cid,confirmed=False).status_code==409
    assert c.post(f'/api/v1/connections/{cid}/operations/renew_client',json={'parameters':{},'confirmed':True}).status_code==422
    assert p.writes==0


def test_required_fields_enforced_before_queue(env):
    c,a,p,t=env;cid=connection(c)
    assert write(c,cid,params={'client_id':'c1'}).status_code==422
    assert not a.state.store.operations()


def test_credentials_update_invalidates_session(env):
    c,a,p,t=env;cid=connection(c)
    c.post(f'/api/v1/connections/{cid}/connect')
    assert c.put(f'/api/v1/connections/{cid}/credentials',json={'token':'new-token'}).status_code==200
    data=a.state.store.connection(cid,True)
    assert data['status']=='not_connected' and not data['session'] and data['revision']==2


def test_no_static_secrets_in_validation_errors(env):
    c,a,p,t=env
    r=c.post('/api/v1/connections',json={'name':'x','base_url':'INVALID','credentials':{'password':'NEVER_ECHO_ME'}})
    assert r.status_code==422 and 'NEVER_ECHO_ME' not in r.text


def test_origin_security(env):
    c,a,p,t=env
    assert c.get('/api/v1/me',headers={'Origin':'https://evil.example'}).status_code==403
    assert "'unsafe-eval'" not in c.get('/').headers['content-security-policy']


@pytest.mark.parametrize('path',['https://evil.example/x','//evil.example/x','/%2fevil.example/x','/../../x','/x#fragment','/foo\\bar'])
def test_relative_path_restrictions(path):
    with pytest.raises(ValidationError):Endpoint(path=path)


def test_write_contract_needs_success_and_evidence():
    with pytest.raises(ValidationError):Profile.model_validate({'endpoints':{'renew_client':{'method':'POST','path':'/x','verified':True,'evidence':'test'}}})
    with pytest.raises(ValidationError):Endpoint(path='/x',verified=True)
    with pytest.raises(ValidationError):Endpoint(path='/x',fields={'password':'1'})
    with pytest.raises(ValidationError):TokenAuth(name='Host')


def test_render_preserves_types_encodes_paths():
    ctx={'input':{'screens':3,'client_id':'a/b?c','plan':{'id':'p1'}}}
    assert render('{{input.screens}}',ctx)==3
    assert render('/c/{{input.client_id}}',ctx,path=True)=='/c/a%2Fb%3Fc'
    assert render('{{input.plan.id}}',ctx)=='p1'
    with pytest.raises(BridgeError):render('{{input.absent}}',ctx)


def test_host_allowlist(env):
    c,a,p,t=env
    r=c.post('/api/v1/connections',json={'name':'bad','base_url':'https://unapproved.example'})
    assert r.status_code==403 and not p.requests
    r=c.post('/api/v1/connections',json={'name':'bad','base_url':'http://panel.example'})
    assert r.status_code==422


def test_master_key_missing_fails_closed(env):
    c,a,p,t=env;path=a.state.store.directory/'master.key';data=path.read_bytes();path.unlink()
    with pytest.raises(RuntimeError):Store(a.state.store.directory)
    path.write_bytes(data)


def test_second_instance_lock_rejected(tmp_path):
    first=InstanceLock(tmp_path/'test.lock');first.acquire()
    try:
        with pytest.raises(RuntimeError):InstanceLock(tmp_path/'test.lock').acquire()
    finally:first.release()


def test_bootstrap_token_stable(env):
    c,a,p,t=env
    again=Store(a.state.store.directory)
    assert (again.directory/'admin.token').read_text().strip()==t
    assert len(again.tokens())==1


def test_last_admin_cannot_be_revoked(env):
    c,a,p,t=env
    id_=c.get('/api/v1/me').json()['id']
    assert c.delete('/api/v1/tokens/'+id_).status_code==409


def test_revoke_token(env):
    c,a,p,t=env
    token=c.post('/api/v1/tokens',json={'name':'read','scope':'read'}).json()
    assert c.delete('/api/v1/tokens/'+token['id']).status_code==200
    assert c.get('/api/v1/me',headers={'Authorization':'Bearer '+token['token']}).status_code==401


def test_postman_import_is_draft_and_omits_secrets(env):
    c,a,p,t=env
    doc={'info':{'name':'Example'},'auth':{'type':'bearer','bearer':[{'key':'token','value':'LEAK_ME'}]},'item':[{'name':'Clients','request':{'method':'GET','url':'{{baseUrl}}/clients?token=HIDDEN_TOKEN&start={{offset}}','header':[{'key':'Cookie','value':'HIDDEN_COOKIE'}]}}]}
    result=c.post('/api/v1/contracts/inspect',json=doc)
    assert result.status_code==200,result.text
    assert 'HIDDEN_TOKEN' not in result.text and 'HIDDEN_COOKIE' not in result.text and 'LEAK_ME' not in result.text
    parsed=result.json();assert parsed['executed'] is False and len(p.requests)==0
    assert parsed['requests'][0]['draft']['verified'] is False
    assert parsed['requests'][0]['token_auth_hint']['prefix']=='Bearer '


def test_har_import_redacts_body_password():
    doc={'log':{'entries':[{'request':{'url':'https://panel.example/form','method':'POST','postData':{'mimeType':'application/x-www-form-urlencoded','text':'username=client&password=SECRET123'}}}]}}
    r=inspect_document(doc)
    assert 'SECRET123' not in json.dumps(r) and r['requests'][0]['draft']['body']['password']=='{{input.password}}'


def test_unknown_import_rejected(env):
    c,a,p,t=env
    assert c.post('/api/v1/contracts/inspect',json={'foo':'bar'}).status_code==422


def test_schedule_requires_explicit_authorization_and_timezone(env):
    c,a,p,t=env;cid=connection(c)
    req={'name':'Test','client_id':'c1','parameters':{'plan_id':'p1'},'run_at':'2030-01-01T00:00:00','authorized':True}
    assert c.post(f'/api/v1/connections/{cid}/schedules',json=req).status_code==422
    req['run_at']='2030-01-01T00:00:00Z';req['authorized']=False
    assert c.post(f'/api/v1/connections/{cid}/schedules',json=req).status_code==409


def test_schedule_executes_once_and_completes(env):
    c,a,p,t=env;cid=connection(c)
    when=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
    r=c.post(f'/api/v1/connections/{cid}/schedules',json={'name':'Test','client_id':'c1','parameters':{'plan_id':'p1'},'run_at':when,'authorized':True})
    assert r.status_code==201,r.text
    with a.state.store.db() as db:db.execute("UPDATE schedules SET run_at='2000-01-01T00:00:00+00:00' WHERE id=?",(r.json()['id'],))
    asyncio.run(a.state.worker.step());asyncio.run(a.state.worker.step())
    assert p.writes==1 and c.get('/api/v1/schedules').json()[0]['status']=='completed'


def test_recurring_schedule_pauses_on_uncertainty(env):
    c,a,p,t=env;cid=connection(c)
    when=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
    r=c.post(f'/api/v1/connections/{cid}/schedules',json={'name':'Test','client_id':'c1','parameters':{'plan_id':'p1'},'run_at':when,'interval_days':30,'authorized':True})
    with a.state.store.db() as db:db.execute("UPDATE schedules SET run_at='2000-01-01T00:00:00+00:00' WHERE id=?",(r.json()['id'],))
    p.mode='timeout';asyncio.run(a.state.worker.step());asyncio.run(a.state.worker.step())
    assert p.writes==1 and c.get('/api/v1/schedules').json()[0]['status']=='paused'


def test_confirmed_payment_deduplicates_by_reference(env):
    c,a,p,t=env;cid=connection(c)
    request={'reference':'fatura-400','client_id':'c1','parameters':{'plan_id':'p1'},'confirmed':True}
    r1=c.post(f'/api/v1/connections/{cid}/payments/confirmed',json=request)
    r2=c.post(f'/api/v1/connections/{cid}/payments/confirmed',json=request)
    assert r1.status_code==202,r1.text
    assert r1.json()['id']==r2.json()['id']
    asyncio.run(a.state.worker.step());assert p.writes==1


def test_websocket_auth_and_scoped_events(env):
    c,a,p,t=env;cid=connection(c)
    token=c.post('/api/v1/tokens',json={'name':'Reader','scope':'read','connection_ids':[cid]}).json()['token']
    with c.websocket_connect('/ws/events') as ws:
        ws.send_json({'token':token,'after':0})
        assert ws.receive_json()['type']=='authenticated'
        event=ws.receive_json()
        assert event['connection_id']==cid and 'token' not in event['data']


def test_websocket_invalid_token(env):
    from starlette.websockets import WebSocketDisconnect
    c,a,p,t=env
    with c.websocket_connect('/ws/events') as ws:
        ws.send_json({'token':'invalid'})
        with pytest.raises(WebSocketDisconnect):ws.receive_json()


def test_webhooks_omit_secret_and_deliver(env):
    c,a,p,t=env
    response=c.post('/api/v1/webhooks',json={'url':'https://hooks.example/receiver','secret':'x'*48,'enabled':True})
    assert response.status_code==201 and 'x'*48 not in response.text
    cid=connection(c)
    asyncio.run(a.state.worker.deliver_one())
    with a.state.store.db() as db:
        assert db.execute("SELECT status FROM deliveries LIMIT 1").fetchone()['status']=='delivered'
    assert any(r[1]=='https://hooks.example/receiver' for r in p.requests)


def test_public_observed_profile_disabled(env):
    c,a,p,t=env
    data=c.get('/api/v1/profiles/koffice-observed').json()
    assert data['endpoints']['list_clients']['verified'] is False
    assert data['token_auth']['name']=='' and len(data['endpoints'])==1


def test_browser_mode_not_silently_emulated(env):
    c,a,p,t=env;cid=connection(c,mode='browser')
    r=c.post(f'/api/v1/connections/{cid}/connect')
    assert r.status_code==409 and r.json()['error']['code']=='browser_disabled' and not p.requests


@pytest.mark.parametrize('mode',['bad_json','missing_data'])
def test_read_response_contract_errors(env,mode):
    c,a,p,t=env;cid=connection(c);p.mode=mode
    assert c.get(f'/api/v1/connections/{cid}/clients').status_code==502


def test_create_client_form_encoding(env):
    c,a,p,t=env;cid=connection(c)
    r=c.post(f'/api/v1/connections/{cid}/clients',headers={'Idempotency-Key':'create-client-1'},json={'parameters':{'username':'new-user','password':'new-secret'},'confirmed':True})
    assert r.status_code==202,r.text
    asyncio.run(a.state.worker.step())
    assert b'username=new-user&password=new-secret'==p.requests[-1][2]
    assert 'new-secret' not in c.get('/api/v1/operations').text


def test_form_automation_authenticates_before_first_mutation(env):
    c,a,p,t=env;cid=connection(c,mode='form')
    op=write(c,cid).json();asyncio.run(a.state.worker.step())
    assert p.logins==1 and p.writes==1
    assert a.state.store.operation(op['id'])['status']=='succeeded'


def test_expired_session_reauth_once_before_mutation(env):
    c,a,p,t=env;cid=connection(c,mode='form')
    c.post(f'/api/v1/connections/{cid}/connect');p.expire=True
    op=write(c,cid).json();asyncio.run(a.state.worker.step())
    assert p.logins==2 and p.writes==1
    assert a.state.store.operation(op['id'])['status']=='succeeded'


def test_schedule_profile_change_requires_new_authorization(env):
    c,a,p,t=env;cid=connection(c)
    when=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
    r=c.post(f'/api/v1/connections/{cid}/schedules',json={'name':'Test','client_id':'c1','parameters':{'plan_id':'p1'},'run_at':when,'authorized':True})
    c.put(f'/api/v1/connections/{cid}/profile',json={'revision':1,'profile':profile()})
    with a.state.store.db() as db:db.execute("UPDATE schedules SET run_at='2000-01-01T00:00:00+00:00' WHERE id=?",(r.json()['id'],))
    asyncio.run(a.state.worker.step())
    assert p.writes==0 and c.get('/api/v1/schedules').json()[0]['status']=='paused'


def test_scoped_events_do_not_stall_after_other_accounts(env):
    c,a,p,t=env;c1=connection(c);c2=connection(c,name='B')
    for i in range(210):a.state.store.event(c1,'other.account',{'i':i})
    a.state.store.event(c2,'target.account',{})
    result=a.state.store.events(after=3,allowed=[c2])
    assert any(r['type']=='target.account' for r in result)
