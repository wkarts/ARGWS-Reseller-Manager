"""Offline inspection regression tests: no upstream calls, no secrets, no mutations."""
import json
import pytest
from app.offline_audit import EvidenceRequest, inspect_offline
from app.errors import BridgeError
from tests.conftest import connection

ORIGIN = "https://servip2p.com"


def test_html_inventory_never_returns_values_or_executes():
    html = """<html><script>const jwt='PRIVATE_SCRIPT_SECRET';</script>
    <form method="post" action="/clients/create/">
      <input name="username" value="CUSTOMER_PRIVATE_VALUE">
      <input type="password" name="password" value="SENSITIVE_PASSWORD">
      <input type="hidden" name="csrf_token" value="PRIVATE_CSRF">
    </form>
    <a href="/clients/?search=PRIVATE_CUSTOMER">Ver</a>
    <a href="https://other.example/steal?token=SECRET">Sair</a></html>"""
    report = inspect_offline(EvidenceRequest(format="html", document=html), ORIGIN)
    serialized = json.dumps(report)
    assert all(value not in serialized for value in
               ("PRIVATE_SCRIPT_SECRET", "CUSTOMER_PRIVATE_VALUE",
                "SENSITIVE_PASSWORD", "PRIVATE_CSRF", "PRIVATE_CUSTOMER", "steal"))
    assert report["summary"]["forms"] == 1 and report["summary"]["links"] == 1
    assert report["forms"][0]["risk"] == "possible_side_effect"
    assert report["scripts_executed"] is False
    assert report["contracts_auto_verified"] is False


def test_har_metadata_drops_body_and_cookie_values_and_external_hosts():
    document = {"log": {"entries": [
        {"request": {"method": "GET",
                     "url": "https://servip2p.com/clients/api/?get_clients&draw=1",
                     "headers": [{"name": "Cookie", "value": "SESSION_PASSWORD"}]},
         "response": {"status": 200, "content": {"text": "PRIVATE_CUSTOMER"}}},
        {"request": {"method": "POST", "url": "https://servip2p.com/clients/renew/",
                     "postData": {"mimeType": "application/json",
                                  "text": "{\"client_id\":\"REAL_USER_SECRET\",\"plan_id\":1}"}},
         "response": {"status": 200}},
        {"request": {"method": "GET", "url": "https://evil.example/?token=PRIVATE_KEY"},
         "response": {"status": 200}}
    ]}}
    report = inspect_offline(EvidenceRequest(format="har", document=document), ORIGIN)
    value = json.dumps(report)
    for secret in ("SESSION_PASSWORD", "PRIVATE_CUSTOMER", "REAL_USER_SECRET", "PRIVATE_KEY"):
        assert secret not in value
    assert report["summary"]["requests"] == 2
    assert report["routes"][0]["suggested_actions_unverified"] == ["list_clients"]
    assert report["routes"][1]["risk"] == "possible_side_effect"
    assert report["routes"][1]["body_field_names"] == ["client_id", "plan_id"]
    assert all(not r["verified"] for r in report["routes"])


def test_postman_collection_detects_requests_without_running_scripts():
    collection = {"item": [
        {"name": "Clients", "request": {"method": "GET",
           "url": "{{baseUrl}}/clients/api/?get_clients", "event": [{"script": "PRIVATE"}]}},
        {"name": "Renew", "request": {"method": "POST",
           "url": "{{baseUrl}}/clients/renew/",
           "body": {"mode": "urlencoded", "urlencoded": [
             {"key": "client_id", "value": "REAL_CLIENT"},
             {"key": "months", "value": "1"}]}}}
    ]}
    report = inspect_offline(EvidenceRequest(format="postman", document=collection), ORIGIN)
    value = json.dumps(report)
    assert "REAL_CLIENT" not in value and "PRIVATE" not in value
    assert report["summary"]["requests"] == 2
    assert report["routes"][1]["risk"] == "possible_side_effect"


def test_inspection_api_does_not_touch_upstream_operations_or_session(env):
    client, app, panel, _ = env
    cid = connection(client, mode="form")
    before = app.state.store.connection(cid, True)
    operations = app.state.store.operations()
    count = len(panel.requests)
    document = {"log": {"entries": [{"request": {
        "method": "GET", "url": "https://panel.example/clients/api/?get_clients"},
        "response": {"status": 200}}]}}
    response = client.post(f"/api/v1/connections/{cid}/audit/inspect",
                           json={"format": "har", "document": document})
    assert response.status_code == 200, response.text
    assert response.json()["dry_run"] is True
    assert len(panel.requests) == count
    assert app.state.store.operations() == operations
    assert app.state.store.connection(cid, True)["session"] == before["session"]


def test_inspection_restricted_to_admin(env):
    client, app, panel, _ = env
    cid = connection(client)
    created = client.post("/api/v1/tokens",
       json={"name": "viewer", "scope": "read", "connection_ids": [cid]})
    token = created.json()["token"]
    response = client.post(f"/api/v1/connections/{cid}/audit/inspect",
       headers={"Authorization": "Bearer " + token},
       json={"format": "html", "document": "<form></form>"})
    assert response.status_code == 403
    assert panel.requests == []


def test_inspection_never_reports_validated_contract():
    report = inspect_offline(EvidenceRequest(
        format="har", document={"log": {"entries": [{
            "request": {"method": "GET", "url": ORIGIN + "/clients/"},
            "response": {"status": 200}}]}}), ORIGIN)
    assert report["contracts_auto_verified"] is False
    assert all(row["verified"] is False for row in report["routes"])
