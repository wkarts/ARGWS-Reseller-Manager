import json
import pytest
from tests.conftest import connection
from app.models import ScheduleCreate, WebhookCreate


def edit(client, identifier, **fields):
    revision = client.get('/api/v1/connections/' + identifier).json()['revision']
    return client.patch('/api/v1/connections/' + identifier, json={'revision':revision, **fields})


def test_edit_keeps_blank_credentials_and_invalidates_session(env):
    client, app, panel, _ = env
    identifier = connection(client, mode='form')
    assert client.post(f'/api/v1/connections/{identifier}/connect').status_code == 200
    app.state.store.cache_clients(identifier,[{'id':'a','username':'cache'}])
    before = len(panel.requests)
    result = edit(client, identifier, name='Conta editada', auth_mode='browser', credentials={'username':'','password':'','token':''})
    assert result.status_code == 200, result.text
    saved = app.state.store.connection(identifier, True)
    assert saved['credentials']['password'] == 'upstream-password'
    assert saved['credentials']['username'] == 'upstream-user'
    assert saved['name'] == 'Conta editada' and saved['auth_mode'] == 'browser'
    assert saved['session'] == {} and saved['status'] == 'not_connected'
    assert app.state.store.cached_clients(identifier)['total'] == 0
    assert len(panel.requests) == before
    assert 'upstream-password' not in result.text and 'credentials' not in result.json()


def test_partial_password_and_explicit_clear(env):
    client, app, _, _ = env
    identifier = connection(client)
    assert edit(client, identifier, credentials={'password':'NEW_SECRET'}).status_code == 200
    assert app.state.store.connection(identifier, True)['credentials']['username'] == 'upstream-user'
    assert edit(client, identifier, clear_credentials=['token']).status_code == 200
    assert not app.state.store.connection(identifier, True)['credentials'].get('token')


def test_new_origin_does_not_reuse_previous_provider_password(env):
    client, app, _, _ = env
    identifier = connection(client)
    result = edit(client, identifier, base_url='https://hooks.example')
    assert result.status_code == 200
    assert app.state.store.connection(identifier, True)['credentials'] == {}
    result = edit(client, identifier, base_url='https://unknown.example')
    assert result.status_code == 403
    assert app.state.store.connection(identifier)['base_url'] == 'https://hooks.example'


def test_revision_conflicts_and_readonly_tokens(env):
    client, app, _, _ = env
    identifier = connection(client)
    assert edit(client, identifier, name='Nova conta').status_code == 200
    stale = client.patch(f'/api/v1/connections/{identifier}',json={'revision':1,'name':'Perda'})
    assert stale.status_code == 409
    token = app.state.store.create_token('Somente leitura','read',[identifier])['token']
    for method, url, body in [('PATCH',f'/api/v1/connections/{identifier}',{'revision':2,'name':'X'}),('DELETE',f'/api/v1/connections/{identifier}',{'revision':2,'confirm_name':'Nova conta'}),('GET',f'/api/v1/connections/{identifier}/deletion-preview',None)]:
        kwargs = {'headers':{'Authorization':'Bearer '+token}}
        if body is not None: kwargs['json'] = body
        assert client.request(method,url,**kwargs).status_code == 403


def test_edit_cancels_queued_and_pauses_schedules(env):
    client, app, _, _ = env
    identifier=connection(client)
    op=app.state.store.enqueue(identifier,'renew_client',{'client_id':'a','plan_id':'p'},'edit-pending',1)
    app.state.store.create_schedule(identifier,ScheduleCreate(name='Ordem',client_id='b',parameters={},run_at='2099-01-01T00:00:00+00:00',authorized=True))
    result=edit(client,identifier,name='Alterada')
    assert result.status_code==200
    assert result.json()['cancelled_operations']==1 and result.json()['paused_schedules']==1
    assert app.state.store.operation(op['id'])['status']=='cancelled'
    assert app.state.store.schedules()[0]['status']=='paused'


def test_running_operation_blocks_edit_and_delete(env):
    client,app,_,_=env
    identifier=connection(client)
    app.state.store.enqueue(identifier,'renew_client',{'client_id':'a','plan_id':'p'},'busy-operation',1)
    app.state.store.claim()
    assert edit(client,identifier,name='Alterada').status_code==409
    response=client.request('DELETE',f'/api/v1/connections/{identifier}',json={'revision':1,'confirm_name':'Conexão A'})
    assert response.status_code==409
    assert app.state.store.connection(identifier)['name']=='Conexão A'


def test_delete_cascades_locally_and_never_broadens_scoped_tokens(env):
    client,app,panel,_=env
    store=app.state.store
    a=connection(client,name='Conta A'); b=connection(client,name='Conta B')
    one=store.create_token('A somente','read',[a]); both=store.create_token('A e B','read',[a,b])
    store.add_hook(WebhookCreate(url='https://hooks.example/events',secret='x'*32,enabled=True))
    store.cache_clients(a,[{'id':'a','username':'A'}]); store.cache_clients(b,[{'id':'b','username':'B'}])
    store.enqueue(a,'renew_client',{'client_id':'a','plan_id':'p'},'delete-operation',1)
    store.create_schedule(a,ScheduleCreate(name='Ordem',client_id='a',parameters={},run_at='2099-01-01T00:00:00+00:00',authorized=True))
    store.event(a,'synthetic.private',{'value':'PRIVATE_LOCAL_PAYLOAD'})
    preview=client.get(f'/api/v1/connections/{a}/deletion-preview').json()
    assert preview['impact']['clients']==1 and preview['impact']['deliveries']>0
    before=len(panel.requests)
    denied=client.request('DELETE',f'/api/v1/connections/{a}',json={'revision':1,'confirm_name':'errado'})
    assert denied.status_code==409
    result=client.request('DELETE',f'/api/v1/connections/{a}',json={'revision':1,'confirm_name':'Conta A'})
    assert result.status_code==200,result.text
    assert result.json()['remote_account_changed'] is False
    assert len(panel.requests)==before
    assert client.get(f'/api/v1/connections/{a}').status_code==404
    assert client.get(f'/api/v1/connections/{b}').status_code==200
    assert store.cached_clients(b)['total']==1
    assert store.authenticate(one['token']) is None
    assert store.authenticate(both['token'])['connection_ids']==[b]
    with store.db() as db:
        for table in ('connections','clients','operations','schedules','events'):
            column='id' if table=='connections' else 'connection_id'
            assert db.execute(f'SELECT count(*) FROM {table} WHERE {column}=?',(a,)).fetchone()[0]==0
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
    assert 'PRIVATE_LOCAL_PAYLOAD' not in json.dumps(store.events())


def test_uncertain_delete_requires_additional_acknowledgement(env):
    client,app,_,_=env
    identifier=connection(client)
    operation=app.state.store.enqueue(identifier,'renew_client',{'client_id':'a','plan_id':'p'},'uncertain-delete',1)
    app.state.store.finish(operation['id'],'reconciliation_required',error='timeout')
    body={'revision':1,'confirm_name':'Conexão A'}
    assert client.request('DELETE',f'/api/v1/connections/{identifier}',json=body).status_code==409
    body['acknowledge_uncertain']=True
    assert client.request('DELETE',f'/api/v1/connections/{identifier}',json=body).status_code==200


def test_connection_not_found_and_stale_deletion(env):
    client,_,_,_=env
    identifier=connection(client)
    assert edit(client,identifier,name='B').status_code==200
    assert client.request('DELETE',f'/api/v1/connections/{identifier}',json={'revision':1,'confirm_name':'B'}).status_code==409
    assert client.get('/api/v1/connections/missing/deletion-preview').status_code==404
