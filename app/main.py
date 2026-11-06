from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib.parse import urlsplit
from fastapi import FastAPI, Depends, Request, Header, Query, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from . import __version__
from .errors import BridgeError
from .settings import Settings
from .store import Store, digest
from .models import (ConnectionCreate, Credentials, ProfileUpdate, WriteRequest, Reconcile,
                     TokenCreate, ScheduleCreate, PaymentConfirmed, WebhookCreate,
                     READ_ACTIONS, WRITE_ACTIONS, ACTIONS)
from .security import InstanceLock
from .connector import Connector
from .worker import Worker
from .importers import inspect_document
from .dry_run import DryRunRequest, preview as dry_run_preview, matrix as dry_run_matrix

STATIC = Path(__file__).resolve().parent / "static"
BEARER = HTTPBearer(auto_error=False)


class BodyLimit:
    def __init__(self, app, limit=4 * 1024 * 1024): self.app, self.limit = app, limit
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http": return await self.app(scope, receive, send)
        messages, total = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect": return
            total += len(message.get("body", b""))
            if total > self.limit:
                return await JSONResponse({"error": {"code": "body_too_large", "message": "Limite de envio: 4 MiB."}}, status_code=413)(scope, receive, send)
            messages.append(message)
            if not message.get("more_body", False): break
        async def replay():
            return messages.pop(0) if messages else await receive()
        return await self.app(scope, replay, send)


def allowed(principal, connection_id):
    return principal["connection_ids"] is None or connection_id in principal["connection_ids"]


def authorize(principal, scope="read", connection_id=None):
    levels = {"read": 0, "operate": 1, "admin": 2}
    if levels[principal["scope"]] < levels[scope] or (connection_id and not allowed(principal, connection_id)):
        raise BridgeError("forbidden", "Seu token não possui acesso a esta operação/conexão.", 403)
    if scope == "admin" and principal["connection_ids"] is not None:
        raise BridgeError("global_admin_required", "Esta configuração exige administrador global.", 403)


def create_app(settings: Settings | None = None, transport=None):
    settings = settings or Settings()
    store = Store(settings.data_dir)
    connector = Connector(store, settings, transport)
    worker = Worker(store, connector)
    lock = InstanceLock(settings.data_dir / "instance.lock")
    @asynccontextmanager
    async def lifespan(app):
        lock.acquire()
        task = None
        try:
            store.recover()
            if settings.worker_enabled: task = asyncio.create_task(worker.run())
            yield
        finally:
            worker.stop_event.set()
            if task:
                try: await asyncio.wait_for(task, timeout=settings.request_timeout + 5)
                except asyncio.TimeoutError:
                    task.cancel()
                    try: await task
                    except asyncio.CancelledError: pass
            lock.release()
    app = FastAPI(title="Reseller Manager", version=__version__, description="API própria para operações de revenda. Os contratos do painel externo são configurados e validados separadamente; nenhuma compatibilidade não testada é presumida.", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.store, app.state.connector, app.state.worker, app.state.settings = store, connector, worker, settings
    app.add_middleware(BodyLimit)

    @app.exception_handler(BridgeError)
    async def bridge_error(request, exc):
        return JSONResponse({"error": {"code": exc.code, "message": exc.message, "uncertain": exc.uncertain}}, status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        # Pydantic's default errors may contain complete credential input: omit it.
        errors = [{"location": list(e["loc"]), "type": e["type"]} for e in exc.errors()]
        return JSONResponse({"error": {"code": "validation_error", "message": "Revise os campos informados.", "fields": errors}}, status_code=422)

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        return JSONResponse({"error": {"code": "internal_error", "message": "Falha interna. Nenhuma repetição automática foi autorizada."}}, status_code=500)

    @app.middleware("http")
    async def security_headers(request, call_next):
        origin = request.headers.get("origin")
        own = settings.public_origin.rstrip("/") or str(request.base_url).rstrip("/")
        if origin and origin.rstrip("/") != own and request.url.path.startswith("/api/"):
            return JSONResponse({"error": {"code": "origin_denied", "message": "Origem não autorizada."}}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        return response

    async def principal(credentials: HTTPAuthorizationCredentials | None = Depends(BEARER)):
        value = store.authenticate(credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else "")
        if not value: raise BridgeError("unauthorized", "Informe um token válido desta API, não o token do kOfficePanel.", 401)
        return value

    from .connection_management import register_connection_management
    register_connection_management(app, store, connector, principal, authorize)

    def connection_access(connection_id, p, scope="read", private=False):
        authorize(p, scope, connection_id)
        return store.connection(connection_id, private)

    def operation_access(identifier, p, scope="read"):
        op = store.operation(identifier)
        authorize(p, scope, op["connection_id"])
        return op

    def submit(connection_id, action, payload, idem, p):
        c = connection_access(connection_id, p, "operate", True)
        if action not in WRITE_ACTIONS: raise BridgeError("invalid_action", "Ação de alteração desconhecida.", 422)
        if not payload.confirmed: raise BridgeError("confirmation_required", "Confirme explicitamente a operação e seus possíveis custos.", 409)
        if not idem or not 8 <= len(idem) <= 200 or any(ord(x) < 32 for x in idem):
            raise BridgeError("idempotency_key_required", "Idempotency-Key deve ter entre 8 e 200 caracteres.", 422)
        connector.prepare(c, action, payload.parameters)  # validates without any network call
        return store.enqueue(connection_id, action, payload.parameters, idem, c["revision"])

    @app.get("/audit", include_in_schema=False)
    async def audit_page():
        return FileResponse(STATIC / "audit.html")

    @app.get("/health", tags=["Instalação"])
    async def health(): return {"status": "ok", "version": __version__, "service": "reseller-manager"}

    @app.get("/api/v1/me", tags=["Autenticação"])
    async def me(p=Depends(principal)): return p

    @app.get("/api/v1/tokens", tags=["Autenticação"])
    async def tokens(p=Depends(principal)):
        authorize(p, "admin"); return store.tokens()

    @app.post("/api/v1/tokens", status_code=201, tags=["Autenticação"])
    async def token_create(payload: TokenCreate, p=Depends(principal)):
        authorize(p, "admin")
        if payload.scope == "admin" and payload.connection_ids is not None:
            raise BridgeError("invalid_scope", "Tokens admin devem ser globais. Para restringir conexões, use operate ou read.", 422)
        return store.create_token(payload.name, payload.scope, payload.connection_ids)

    @app.delete("/api/v1/tokens/{token_id}", tags=["Autenticação"])
    async def token_revoke(token_id: str, p=Depends(principal)):
        authorize(p, "admin"); store.revoke_token(token_id); return {"revoked": True}

    @app.get("/api/v1/connections", tags=["Conexões"])
    async def connections(p=Depends(principal)):
        return [c for c in store.connections() if allowed(p, c["id"])]

    @app.post("/api/v1/connections", status_code=201, tags=["Conexões"])
    async def connection_create(payload: ConnectionCreate, p=Depends(principal)):
        authorize(p, "admin")
        await connector.policy.validate(payload.base_url)
        return store.create_connection(payload)

    @app.get("/api/v1/connections/{connection_id}", tags=["Conexões"])
    async def connection_get(connection_id: str, p=Depends(principal)):
        c = connection_access(connection_id, p)
        if p["scope"] != "admin": c.pop("profile", None)
        return c

    @app.put("/api/v1/connections/{connection_id}/profile", tags=["Contratos"])
    async def profile_update(connection_id: str, payload: ProfileUpdate, p=Depends(principal)):
        connection_access(connection_id, p, "admin")
        async with connector.lock(connection_id):
            return store.update_profile(connection_id, payload.revision, payload.profile)

    @app.put("/api/v1/connections/{connection_id}/credentials", tags=["Conexões"])
    async def credentials_update(connection_id: str, payload: Credentials, p=Depends(principal)):
        connection_access(connection_id, p, "admin")
        async with connector.lock(connection_id): store.set_credentials(connection_id, payload.model_dump())
        return {"updated": True, "requires_reconnect": True}

    @app.post("/api/v1/connections/{connection_id}/connect", tags=["Conexões"])
    async def connect(connection_id: str, p=Depends(principal)):
        connection_access(connection_id, p, "admin")
        return await connector.connect(connection_id)

    @app.post("/api/v1/connections/{connection_id}/disconnect", tags=["Conexões"])
    async def disconnect(connection_id: str, p=Depends(principal)):
        connection_access(connection_id, p, "admin")
        async with connector.lock(connection_id): store.set_session(connection_id, {}, "not_connected")
        return {"status": "not_connected", "note": "Sessão local descartada; não executa logout remoto."}

    @app.get("/api/v1/connections/{connection_id}/login-form", tags=["Contratos"])
    async def login_form(connection_id: str, p=Depends(principal)):
        connection_access(connection_id, p, "admin")
        return await connector.inspect_login(connection_id)

    @app.get("/api/v1/connections/{connection_id}/capabilities", tags=["Contratos"])
    async def capabilities(connection_id: str, p=Depends(principal)):
        c = connection_access(connection_id, p)
        return {"connection_id": connection_id, "revision": c["revision"], "actions": [{"name": a, "kind": "read" if a in READ_ACTIONS else "write", "enabled": bool(c["profile"].get("endpoints", {}).get(a, {}).get("verified")), "evidence": c["profile"].get("endpoints", {}).get(a, {}).get("evidence", "")} for a in sorted(ACTIONS)]}

    @app.get("/api/v1/connections/{connection_id}/dry-run", tags=["Dry-run"])
    async def dry_run_all(connection_id: str, p=Depends(principal)):
        # Administrator-only: inspect local metadata; never send provider requests.
        c = connection_access(connection_id, p, "admin", True)
        return dry_run_matrix(c)

    @app.post("/api/v1/connections/{connection_id}/dry-run/{action}", tags=["Dry-run"])
    async def dry_run_one(connection_id: str, action: str, request: DryRunRequest, p=Depends(principal)):
        c = connection_access(connection_id, p, "admin", True)
        return dry_run_preview(c, action, request.parameters)

    @app.post("/api/v1/contracts/inspect", tags=["Contratos"])
    async def contracts_inspect(document: dict, p=Depends(principal)):
        authorize(p, "admin"); return inspect_document(document)

    @app.get("/api/v1/profiles/koffice-observed", tags=["Contratos"])
    async def observed_profile(p=Depends(principal)):
        authorize(p, "admin")
        return json.loads((STATIC / "koffice-observed.json").read_text(encoding="utf-8"))

    @app.get("/api/v1/connections/{connection_id}/clients", tags=["Clientes"])
    async def clients(connection_id: str, start: int = Query(0, ge=0), length: int = Query(50, ge=1, le=500), search: str = Query("", max_length=200), cached: bool = False, p=Depends(principal)):
        connection_access(connection_id, p)
        if cached: return store.cached_clients(connection_id, start, length)
        return await connector.execute(connection_id, "list_clients", {"start": start, "length": length, "search": search, "draw": 1})

    @app.get("/api/v1/connections/{connection_id}/clients/{client_id}", tags=["Clientes"])
    async def client_get(connection_id: str, client_id: str, p=Depends(principal)):
        connection_access(connection_id, p)
        return await connector.execute(connection_id, "get_client", {"client_id": client_id})

    @app.post("/api/v1/connections/{connection_id}/queries/{action}", tags=["Consultas"])
    async def query(connection_id: str, action: str, parameters: dict, p=Depends(principal)):
        connection_access(connection_id, p)
        if action not in READ_ACTIONS: raise BridgeError("invalid_action", "Use somente ações de consulta neste endpoint.", 422)
        return await connector.execute(connection_id, action, parameters)

    @app.post("/api/v1/connections/{connection_id}/operations/{action}", status_code=202, tags=["Operações"])
    async def operation_submit(connection_id: str, action: str, payload: WriteRequest, idempotency_key: str = Header(alias="Idempotency-Key"), p=Depends(principal)):
        return submit(connection_id, action, payload, idempotency_key, p)

    @app.post("/api/v1/connections/{connection_id}/clients", status_code=202, tags=["Clientes"])
    async def client_create(connection_id: str, payload: WriteRequest, idempotency_key: str = Header(alias="Idempotency-Key"), p=Depends(principal)):
        return submit(connection_id, "create_client", payload, idempotency_key, p)

    @app.post("/api/v1/connections/{connection_id}/clients/{client_id}/renewals", status_code=202, tags=["Clientes"])
    async def client_renew(connection_id: str, client_id: str, payload: WriteRequest, idempotency_key: str = Header(alias="Idempotency-Key"), p=Depends(principal)):
        payload.parameters["client_id"] = client_id
        return submit(connection_id, "renew_client", payload, idempotency_key, p)

    @app.get("/api/v1/operations", tags=["Operações"])
    async def operations(limit: int = Query(100, ge=1, le=500), p=Depends(principal)):
        return store.operations(p["connection_ids"], limit)

    @app.get("/api/v1/operations/{operation_id}", tags=["Operações"])
    async def operation_get(operation_id: str, p=Depends(principal)):
        return operation_access(operation_id, p)

    @app.post("/api/v1/operations/{operation_id}/cancel", tags=["Operações"])
    async def operation_cancel(operation_id: str, p=Depends(principal)):
        operation_access(operation_id, p, "operate"); return store.cancel(operation_id)

    @app.post("/api/v1/operations/{operation_id}/reconcile", tags=["Operações"])
    async def operation_reconcile(operation_id: str, payload: Reconcile, p=Depends(principal)):
        operation_access(operation_id, p, "admin"); return store.reconcile(operation_id, payload.outcome, payload.evidence)

    @app.post("/api/v1/connections/{connection_id}/schedules", status_code=201, tags=["Automação"])
    async def schedule_create(connection_id: str, payload: ScheduleCreate, p=Depends(principal)):
        c = connection_access(connection_id, p, "admin", True)
        if not payload.authorized: raise BridgeError("authorization_required", "Autorize expressamente a renovação agendada e seu consumo de créditos.", 409)
        try:
            when = datetime.fromisoformat(payload.run_at.replace("Z", "+00:00"))
            if when.tzinfo is None or when <= datetime.now(timezone.utc): raise ValueError()
        except ValueError: raise BridgeError("invalid_date", "Informe data futura ISO 8601 com fuso horário.", 422)
        payload.run_at = when.astimezone(timezone.utc).isoformat(timespec="seconds")
        connector.prepare(c, "renew_client", {**payload.parameters, "client_id": payload.client_id})
        identifier = store.create_schedule(connection_id, payload)
        return next(x for x in store.schedules() if x["id"] == identifier)

    @app.get("/api/v1/schedules", tags=["Automação"])
    async def schedules(p=Depends(principal)): return store.schedules(p["connection_ids"])

    @app.post("/api/v1/schedules/{schedule_id}/pause", tags=["Automação"])
    async def schedule_pause(schedule_id: str, p=Depends(principal)):
        authorize(p, "admin"); store.pause_schedule(schedule_id)
        return {"status": "paused", "note": "Uma operação já enviada não é desfeita. Cancele separadamente operações ainda na fila."}

    @app.post("/api/v1/connections/{connection_id}/payments/confirmed", status_code=202, tags=["Automação"])
    async def payment_confirmed(connection_id: str, payload: PaymentConfirmed, p=Depends(principal)):
        # Trusted ERP assertion, not a bank webhook verifier; do not expose to anonymous callbacks.
        request = WriteRequest(parameters={**payload.parameters, "client_id": payload.client_id}, confirmed=payload.confirmed)
        return submit(connection_id, "renew_client", request, "payment:" + digest(payload.reference), p)

    @app.get("/api/v1/events", tags=["Eventos"])
    async def events(after: int = Query(0, ge=0), p=Depends(principal)):
        return store.events(after, p["connection_ids"])

    @app.websocket("/ws/events")
    async def websocket(ws: WebSocket):
        origin = ws.headers.get("origin")
        expected = settings.public_origin.rstrip("/") or ("https" if ws.url.scheme == "wss" else "http") + "://" + ws.headers.get("host", "")
        if origin and origin.rstrip("/") != expected:
            await ws.close(code=1008); return
        await ws.accept()
        try:
            first = await asyncio.wait_for(ws.receive_json(), timeout=5)
            token = first.get("token", "")
            p = store.authenticate(token)
            if not p:
                await ws.close(code=1008); return
            after = max(0, int(first.get("after", 0)))
            await ws.send_json({"type": "authenticated"})
            # Recheck token revocation each cycle. Credentials never travel in the URL.
            while True:
                if not store.authenticate(token):
                    await ws.close(code=1008); return
                batch = store.events(after, p["connection_ids"])
                for event in batch:
                    await ws.send_json(event); after = event["seq"]
                try:
                    message = await asyncio.wait_for(ws.receive_json(), timeout=1)
                    if message.get("type") == "ping": await ws.send_json({"type": "pong"})
                except asyncio.TimeoutError: pass
        except (WebSocketDisconnect, asyncio.TimeoutError, ValueError, TypeError, AttributeError):
            try: await ws.close(code=1008)
            except RuntimeError: pass

    @app.get("/api/v1/webhooks", tags=["Webhooks"])
    async def hooks(p=Depends(principal)):
        authorize(p, "admin"); return store.hooks()

    @app.post("/api/v1/webhooks", status_code=201, tags=["Webhooks"])
    async def hook_create(payload: WebhookCreate, p=Depends(principal)):
        authorize(p, "admin"); await connector.policy.validate(payload.url)
        return store.add_hook(payload)

    @app.delete("/api/v1/webhooks/{hook_id}", tags=["Webhooks"])
    async def hook_disable(hook_id: str, p=Depends(principal)):
        authorize(p, "admin"); store.disable_hook(hook_id); return {"enabled": False}

    @app.get("/", include_in_schema=False)
    async def index(): return FileResponse(STATIC / "index.html")

    @app.get("/docs", include_in_schema=False)
    async def docs(): return FileResponse(STATIC / "api.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app
