"""Local connection lifecycle. Never deletes or changes an account at the provider."""
from __future__ import annotations
import json
from typing import Literal
from fastapi import Depends
from pydantic import Field, field_validator
from .errors import BridgeError
from .models import Strict, ConnectionCreate, Login, TokenAuth
from .store import canonical, now


class CredentialPatch(Strict):
    username: str = Field(default="", max_length=500)
    password: str = Field(default="", max_length=2048)
    token: str = Field(default="", max_length=8192)


class ConnectionPatch(Strict):
    revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    base_url: str | None = None
    auth_mode: Literal["token", "form", "browser"] | None = None
    credentials: CredentialPatch | None = None
    clear_credentials: list[Literal["username", "password", "token"]] = Field(default_factory=list)
    login: Login | None = None
    token_auth: TokenAuth | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Nome obrigatório")
        return value

    @field_validator("base_url")
    @classmethod
    def clean_url(cls, value):
        return ConnectionCreate.base(value) if value is not None else None


class ConnectionDelete(Strict):
    revision: int = Field(ge=1)
    confirm_name: str = Field(min_length=1, max_length=100)
    acknowledge_uncertain: bool = False


def impact(db, identifier):
    counts = {table: db.execute(f"SELECT count(*) FROM {table} WHERE connection_id=?", (identifier,)).fetchone()[0]
              for table in ("clients", "operations", "schedules", "events")}
    counts["deliveries"] = db.execute("SELECT count(*) FROM deliveries WHERE event_seq IN (SELECT seq FROM events WHERE connection_id=?)", (identifier,)).fetchone()[0]
    counts["running"] = db.execute("SELECT count(*) FROM operations WHERE connection_id=? AND status='running'", (identifier,)).fetchone()[0]
    counts["uncertain"] = db.execute("SELECT count(*) FROM operations WHERE connection_id=? AND status='reconciliation_required'", (identifier,)).fetchone()[0]
    counts["scoped_tokens"] = sum(identifier in json.loads(r[0]) for r in db.execute("SELECT connections FROM tokens WHERE connections IS NOT NULL"))
    return counts


def checked_row(db, identifier, revision=None):
    row = db.execute("SELECT * FROM connections WHERE id=?", (identifier,)).fetchone()
    if not row:
        raise BridgeError("connection_not_found", "Conexão não encontrada.", 404)
    if revision is not None and row["revision"] != revision:
        raise BridgeError("revision_conflict", "A conexão foi alterada. Recarregue antes de confirmar.", 409)
    return row


def update_connection(store, identifier, payload):
    with store.db(True) as db:
        row = checked_row(db, identifier, payload.revision)
        if db.execute("SELECT 1 FROM operations WHERE connection_id=? AND status IN ('running','reconciliation_required')", (identifier,)).fetchone():
            raise BridgeError("connection_busy", "Há operação em execução ou exigindo conferência. Conclua a conferência antes de editar.", 409)
        profile = store.vault.open(row["profile"])
        credentials = store.vault.open(row["credentials"])
        base_url = payload.base_url or row["base_url"]
        # Changing the destination must not send the previous provider's password to it.
        if base_url != row["base_url"]:
            credentials = {}
        for key in payload.clear_credentials:
            credentials.pop(key, None)
        if payload.credentials:
            credentials.update({k: v for k, v in payload.credentials.model_dump().items() if v != ""})
        if payload.login is not None:
            profile["login"] = payload.login.model_dump()
        if payload.token_auth is not None:
            profile["token_auth"] = payload.token_auth.model_dump()
        stamp = now()
        cancelled = db.execute("UPDATE operations SET status='cancelled',error_code='connection_updated',updated_at=? WHERE connection_id=? AND status='queued'", (stamp, identifier)).rowcount
        paused = db.execute("UPDATE schedules SET status='paused' WHERE connection_id=? AND status IN ('scheduled','waiting')", (identifier,)).rowcount
        db.execute("DELETE FROM clients WHERE connection_id=?", (identifier,))
        db.execute("UPDATE connections SET name=?,base_url=?,auth_mode=?,credentials=?,profile=?,session=?,status='not_connected',revision=revision+1,updated_at=? WHERE id=?", (payload.name or row["name"], base_url, payload.auth_mode or row["auth_mode"], store.vault.seal(credentials), store.vault.seal(profile), store.vault.seal({}), stamp, identifier))
        store._event(db, identifier, "connection.updated", {"revision": row["revision"] + 1, "cancelled": cancelled, "paused": paused})
    return {**store.connection(identifier), "requires_reconnect": True, "cancelled_operations": cancelled, "paused_schedules": paused}


def delete_connection(store, identifier, payload):
    with store.db(True) as db:
        row = checked_row(db, identifier, payload.revision)
        if payload.confirm_name != row["name"]:
            raise BridgeError("confirmation_required", "Digite o nome exato da conexão para excluir seus dados locais.", 409)
        counts = impact(db, identifier)
        if counts["running"]:
            raise BridgeError("connection_busy", "Aguarde a operação em execução antes de excluir a conexão.", 409)
        if counts["uncertain"] and not payload.acknowledge_uncertain:
            raise BridgeError("reconciliation_pending", "Existem operações incertas. Confira o fornecedor ou confirme expressamente a perda desse histórico.", 409)
        db.execute("DELETE FROM deliveries WHERE event_seq IN (SELECT seq FROM events WHERE connection_id=?)", (identifier,))
        for table in ("events", "schedules", "clients", "operations"):
            db.execute(f"DELETE FROM {table} WHERE connection_id=?", (identifier,))
        for token in db.execute("SELECT id,connections FROM tokens WHERE connections IS NOT NULL").fetchall():
            ids = json.loads(token["connections"])
            if identifier in ids:
                ids = [value for value in ids if value != identifier]
                # [] is never changed to NULL (which would grant access to every connection).
                db.execute("UPDATE tokens SET connections=?,revoked=CASE WHEN ?=0 THEN 1 ELSE revoked END WHERE id=?", (canonical(ids), len(ids), token["id"]))
        db.execute("DELETE FROM connections WHERE id=?", (identifier,))
        # Only aggregate, anonymous audit information remains. No name, URL or identifier.
        store._event(db, None, "connection.deleted", {"local_only": True, "removed": counts})
    return {"deleted": True, "removed": counts, "remote_account_changed": False}


def register_connection_management(app, store, connector, principal, authorize):
    @app.patch("/api/v1/connections/{connection_id}", tags=["Conexões"])
    async def connection_patch(connection_id: str, payload: ConnectionPatch, p=Depends(principal)):
        authorize(p, "admin", connection_id)
        async with connector.lock(connection_id):
            current = store.connection(connection_id)
            await connector.policy.validate(payload.base_url or current["base_url"])
            return update_connection(store, connection_id, payload)

    @app.get("/api/v1/connections/{connection_id}/deletion-preview", tags=["Conexões"])
    async def deletion_preview(connection_id: str, p=Depends(principal)):
        authorize(p, "admin", connection_id)
        with store.db() as db:
            row = checked_row(db, connection_id)
            return {"name": row["name"], "revision": row["revision"], "impact": impact(db, connection_id), "local_only": True}

    @app.delete("/api/v1/connections/{connection_id}", tags=["Conexões"])
    async def connection_delete(connection_id: str, payload: ConnectionDelete, p=Depends(principal)):
        authorize(p, "admin", connection_id)
        async with connector.lock(connection_id):
            return delete_connection(store, connection_id, payload)
