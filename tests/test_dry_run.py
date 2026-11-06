"""Dry-run must be strictly local and free of upstream side effects."""
from __future__ import annotations
import json

from tests.conftest import connection


def test_dry_run_matrix_does_not_contact_provider_or_modify_operations(env):
    client, app, panel, _ = env
    identifier = connection(client, mode="form")
    before = app.state.store.connection(identifier, True)
    operations_before = app.state.store.operations()
    requests_before = len(panel.requests)
    response = client.get(f"/api/v1/connections/{identifier}/dry-run")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["dry_run"] and not payload["upstream_request_sent"]
    assert len(payload["operations"]) == 20
    assert all(row["result"] == "NOT_EXECUTED" for row in payload["operations"])
    assert len(panel.requests) == requests_before
    assert app.state.store.operations() == operations_before
    assert app.state.store.connection(identifier, True)["session"] == before["session"]


def test_dry_run_renewal_does_not_spend_credit_or_enqueue(env):
    client, app, panel, _ = env
    identifier = connection(client, mode="form")
    before = len(panel.requests)
    response = client.post(f"/api/v1/connections/{identifier}/dry-run/renew_client",
        json={"parameters": {"client_id": "fake-123", "plan_id": "test-plan"}})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["kind"] == "write"
    assert data["dry_run"] and not data["upstream_request_sent"]
    assert not data["queued"] and not data["executed"] and not data["credits_charged"]
    assert data["result"] == "NOT_EXECUTED"
    assert "session_read_probe_pending" in data["issues"]
    assert not app.state.store.operations()
    assert len(panel.requests) == before


def test_dry_run_hides_values_secret_credentials_and_paths(env):
    client, app, panel, _ = env
    identifier = connection(client, mode="form")
    secret = "VERY_SENSITIVE_DRYRUN_VALUE"
    before = len(panel.requests)
    response = client.post(f"/api/v1/connections/{identifier}/dry-run/create_client",
        json={"parameters": {"username": secret, "password": secret}})
    assert response.status_code == 200
    body = response.text
    assert secret not in body
    assert "upstream-password" not in body and "upstream-token" not in body
    assert "panel.example" not in body
    assert "password" in body  # Parameter NAME is allowed; value is never returned.
    assert len(panel.requests) == before


def test_missing_contract_and_bad_action_do_not_contact_provider(env):
    client, app, panel, _ = env
    identifier = connection(client)
    before = len(panel.requests)
    ok = client.post(f"/api/v1/connections/{identifier}/dry-run/credit_transfer",
                     json={"parameters": {"amount": 10}})
    assert ok.status_code == 200
    assert ok.json()["status"] == "contract_missing"
    bad = client.post(f"/api/v1/connections/{identifier}/dry-run/arbitrary_path",
                      json={"parameters": {}})
    assert bad.status_code == 422
    assert len(panel.requests) == before


def test_dry_run_is_admin_only(env):
    client, app, panel, _ = env
    identifier = connection(client)
    result = client.post("/api/v1/tokens", json={"name":"limited", "scope":"read", "connection_ids":[identifier]})
    assert result.status_code == 201
    token = result.json()["token"]
    headers={"Authorization": "Bearer "+token}
    assert client.get(f"/api/v1/connections/{identifier}/dry-run",headers=headers).status_code == 403
    assert client.post(f"/api/v1/connections/{identifier}/dry-run/renew_client",
                       json={"parameters":{}}, headers=headers).status_code == 403


def test_audit_page_is_local_static_without_external_scripts(env):
    client, _, panel, _ = env
    before = len(panel.requests)
    response = client.get("/audit")
    assert response.status_code == 200
    assert b"/static/audit.js" in response.content
    assert b"fonts.googleapis.com" not in response.content
    assert len(panel.requests) == before
