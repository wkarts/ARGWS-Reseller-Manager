from __future__ import annotations
import asyncio
import hashlib
import hmac
import json
import logging
import time
import httpx
from .errors import BridgeError
from .network import limited_request
from .store import canonical

LOG = logging.getLogger("reseller.worker")


class Worker:
    def __init__(self, store, connector):
        self.store, self.connector = store, connector
        self.stop_event = asyncio.Event()

    async def step(self):
        self.store.tick_schedules()
        operation = self.store.claim()
        if operation:
            try:
                await self.connector.ensure_session_before_write(operation["connection_id"], operation["profile_revision"])
                result = await self.connector.execute(operation["connection_id"], operation["action"], operation["parameters"], expected_revision=operation["profile_revision"])
                self.store.finish(operation["id"], "succeeded", result=result)
            except BridgeError as exc:
                self.store.finish(operation["id"], "reconciliation_required" if exc.uncertain else "failed", error=exc.code)
            except asyncio.CancelledError:
                self.store.finish(operation["id"], "reconciliation_required", error="worker_interrupted")
                raise
            except Exception:
                # Never log HTTP exceptions with request URLs/credentials or replay a mutation.
                self.store.finish(operation["id"], "reconciliation_required", error="internal_error")
                LOG.error("Operação %s requer conferência; detalhes sensíveis omitidos.", operation["id"])
        await self.deliver_one()
        return bool(operation)

    async def deliver_one(self):
        d = self.store.pending_delivery()
        if not d: return
        delivered = False
        try:
            await self.connector.policy.validate(d["url"])
            body = canonical({"id": d["event_id"], "type": d["type"], "connection_id": d["connection_id"], "data": json.loads(d["data"]), "created_at": d["created_at"]}).encode()
            stamp = str(int(time.time()))
            secret = self.store.vault.open(d["secret"])
            signature = hmac.new(secret.encode(), stamp.encode() + b"." + body, hashlib.sha256).hexdigest()
            async with httpx.AsyncClient(timeout=10, follow_redirects=False, trust_env=False, transport=self.connector.transport) as client:
                r = await limited_request(client, self.connector.settings, "POST", d["url"], content=body, headers={"Content-Type": "application/json", "X-Reseller-Event": d["event_id"], "X-Reseller-Timestamp": stamp, "X-Reseller-Signature": "sha256=" + signature})
                delivered = 200 <= r.status_code < 300
        except (BridgeError, httpx.HTTPError): pass
        self.store.finish_delivery(d["id"], delivered)

    async def run(self):
        while not self.stop_event.is_set():
            try:
                done = await self.step()
            except asyncio.CancelledError: raise
            except Exception:
                LOG.error("Falha no ciclo da fila. Verifique disponibilidade do banco; nenhuma operação é repetida automaticamente.")
                done = False
            try: await asyncio.wait_for(self.stop_event.wait(), timeout=0.05 if done else 1.0)
            except asyncio.TimeoutError: pass
