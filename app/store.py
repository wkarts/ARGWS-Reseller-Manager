"""SQLite/WAL repository. One worker process; transactions serialize durable state changes."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import uuid
from .security import Vault, private_write, digest, redact
from .errors import BridgeError


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def uid(prefix=""):
    return prefix + uuid.uuid4().hex


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


class Store:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        if __import__("os").name != "nt": self.directory.chmod(0o700)
        self.path = self.directory / "reseller.sqlite3"
        # Never silently generate a replacement key for an existing database.
        if self.path.exists() and not (self.directory / "master.key").exists():
            raise RuntimeError("master.key ausente. Restaure a chave original; o banco existente foi preservado.")
        self.vault = Vault(self.directory / "master.key")
        with self.db() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript('''
            CREATE TABLE IF NOT EXISTS schema_version(version INTEGER NOT NULL);
            INSERT INTO schema_version SELECT 1 WHERE NOT EXISTS(SELECT 1 FROM schema_version);
            CREATE TABLE IF NOT EXISTS tokens (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, hash TEXT NOT NULL UNIQUE,
              scope TEXT NOT NULL, connections TEXT, revoked INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS connections (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, base_url TEXT NOT NULL, auth_mode TEXT NOT NULL,
              credentials TEXT NOT NULL, session TEXT NOT NULL, profile TEXT NOT NULL,
              revision INTEGER NOT NULL DEFAULT 1, status TEXT NOT NULL DEFAULT 'not_connected',
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS operations (
              id TEXT PRIMARY KEY, connection_id TEXT NOT NULL REFERENCES connections(id), action TEXT NOT NULL,
              resource TEXT NOT NULL, idempotency_key TEXT NOT NULL, payload_hash TEXT NOT NULL,
              payload TEXT NOT NULL, profile_revision INTEGER NOT NULL, status TEXT NOT NULL,
              result TEXT, error_code TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
              UNIQUE(connection_id, idempotency_key));
            CREATE INDEX IF NOT EXISTS ops_status ON operations(status, created_at);
            CREATE TABLE IF NOT EXISTS clients (
              connection_id TEXT NOT NULL REFERENCES connections(id), client_id TEXT NOT NULL,
              data TEXT NOT NULL, synced_at TEXT NOT NULL, PRIMARY KEY(connection_id, client_id));
            CREATE TABLE IF NOT EXISTS events (
              seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE, connection_id TEXT,
              type TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS schedules (
              id TEXT PRIMARY KEY, connection_id TEXT NOT NULL REFERENCES connections(id), name TEXT NOT NULL,
              client_id TEXT NOT NULL, parameters TEXT NOT NULL, run_at TEXT NOT NULL, interval_days INTEGER,
              profile_revision INTEGER NOT NULL, status TEXT NOT NULL, last_operation TEXT, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS hooks (
              id TEXT PRIMARY KEY, url TEXT NOT NULL, secret TEXT NOT NULL, enabled INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS deliveries (
              id TEXT PRIMARY KEY, hook_id TEXT NOT NULL REFERENCES hooks(id), event_seq INTEGER NOT NULL REFERENCES events(seq),
              attempts INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'pending', next_at TEXT NOT NULL,
              UNIQUE(hook_id, event_seq));
            ''')
            if db.execute("SELECT version FROM schema_version").fetchone()[0] != 1:
                raise RuntimeError("Versão do banco incompatível; nenhuma migração destrutiva foi executada.")
            count = db.execute("SELECT count(*) FROM tokens").fetchone()[0]
            if not count:
                token = secrets.token_urlsafe(48)
                self._token(db, "Administrador inicial", "admin", None, token)
                private_write(self.directory / "admin.token", (token + "\n").encode())
        if __import__("os").name != "nt": self.path.chmod(0o600)

    @contextmanager
    def db(self, immediate=False):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=15000")
        try:
            if immediate: db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _token(self, db, name, scope, connections, token):
        identifier = uid("key_")
        db.execute("INSERT INTO tokens VALUES(?,?,?,?,?,0,?)", (identifier, name, digest(token), scope, canonical(connections) if connections is not None else None, now()))
        return identifier

    def create_token(self, name, scope, connections):
        value = secrets.token_urlsafe(48)
        with self.db(True) as db:
            if connections is not None:
                for identifier in connections:
                    if not db.execute("SELECT 1 FROM connections WHERE id=?", (identifier,)).fetchone():
                        raise BridgeError("connection_not_found", "Conexão não encontrada.", 404)
            identifier = self._token(db, name, scope, connections, value)
            self._event(db, None, "security.token_created", {"token_id": identifier, "scope": scope})
        return {"id": identifier, "token": value, "scope": scope, "connection_ids": connections}

    def authenticate(self, value: str):
        if not value or len(value) > 512: return None
        with self.db() as db:
            row = db.execute("SELECT * FROM tokens WHERE hash=? AND revoked=0", (digest(value),)).fetchone()
        if row:
            return {"id": row["id"], "name": row["name"], "scope": row["scope"], "connection_ids": json.loads(row["connections"]) if row["connections"] is not None else None}
        return None

    def tokens(self):
        with self.db() as db:
            return [{"id": r["id"], "name": r["name"], "scope": r["scope"], "connection_ids": json.loads(r["connections"]) if r["connections"] else None, "revoked": bool(r["revoked"]), "created_at": r["created_at"]} for r in db.execute("SELECT * FROM tokens ORDER BY created_at")]

    def revoke_token(self, identifier):
        with self.db(True) as db:
            token = db.execute("SELECT * FROM tokens WHERE id=?", (identifier,)).fetchone()
            if not token: raise BridgeError("not_found", "Token não encontrado.", 404)
            if token["scope"] == "admin" and not token["revoked"] and db.execute("SELECT count(*) FROM tokens WHERE scope='admin' AND revoked=0 AND connections IS NULL").fetchone()[0] <= 1:
                raise BridgeError("last_admin", "Crie outro token administrador global antes de revogar o último.", 409)
            db.execute("UPDATE tokens SET revoked=1 WHERE id=?", (identifier,))
            self._event(db, None, "security.token_revoked", {"token_id": identifier})

    def create_connection(self, value):
        identifier = uid("con_"); stamp = now()
        with self.db(True) as db:
            db.execute("INSERT INTO connections(id,name,base_url,auth_mode,credentials,session,profile,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)", (identifier, value.name, value.base_url, value.auth_mode, self.vault.seal(value.credentials.model_dump()), self.vault.seal({}), self.vault.seal(value.profile.model_dump()), stamp, stamp))
            self._event(db, identifier, "connection.created", {"connection_id": identifier})
        return self.connection(identifier)

    def connection(self, identifier, secrets=False):
        with self.db() as db:
            row = db.execute("SELECT * FROM connections WHERE id=?", (identifier,)).fetchone()
        if not row: raise BridgeError("connection_not_found", "Conexão não encontrada.", 404)
        d = dict(row)
        d["profile"] = self.vault.open(d["profile"])
        if secrets:
            d["credentials"] = self.vault.open(d["credentials"])
            d["session"] = self.vault.open(d["session"])
        else:
            d.pop("credentials"); d.pop("session")
        return d

    def connections(self):
        with self.db() as db:
            return [dict(r) for r in db.execute("SELECT id,name,base_url,auth_mode,revision,status,created_at,updated_at FROM connections ORDER BY created_at")]

    def update_profile(self, identifier, revision, profile):
        with self.db(True) as db:
            changed = db.execute("UPDATE connections SET profile=?,revision=revision+1,session=?,status='not_connected',updated_at=? WHERE id=? AND revision=?", (self.vault.seal(profile.model_dump()), self.vault.seal({}), now(), identifier, revision)).rowcount
            if not changed: raise BridgeError("revision_conflict", "Perfil alterado por outra sessão ou conexão inexistente. Recarregue antes de salvar.", 409)
            self._event(db, identifier, "connection.profile_updated", {"revision": revision + 1})
        return self.connection(identifier)

    def set_credentials(self, identifier, value):
        self.connection(identifier)
        with self.db(True) as db:
            db.execute("UPDATE connections SET credentials=?,session=?,status='not_connected',revision=revision+1,updated_at=? WHERE id=?", (self.vault.seal(value), self.vault.seal({}), now(), identifier))
            self._event(db, identifier, "connection.credentials_updated", {})

    def set_session(self, identifier, session, status):
        with self.db(True) as db:
            db.execute("UPDATE connections SET session=?,status=?,updated_at=? WHERE id=?", (self.vault.seal(session), status, now(), identifier))
            self._event(db, identifier, "connection." + status, {"status": status})

    def _event(self, db, connection_id, type_, data):
        result = db.execute("INSERT INTO events(id,connection_id,type,data,created_at) VALUES(?,?,?,?,?)", (uid("evt_"), connection_id, type_, canonical(redact(data)), now()))
        for hook in db.execute("SELECT id FROM hooks WHERE enabled=1").fetchall():
            db.execute("INSERT INTO deliveries(id,hook_id,event_seq,next_at) VALUES(?,?,?,?)", (uid("delivery_"), hook["id"], result.lastrowid, now()))

    def event(self, connection_id, type_, data):
        with self.db(True) as db: self._event(db, connection_id, type_, data)

    def events(self, after=0, allowed=None, limit=200):
        with self.db() as db:
            if allowed is None:
                rows = db.execute("SELECT * FROM events WHERE seq>? ORDER BY seq LIMIT ?", (after, limit)).fetchall()
            elif not allowed: return []
            else:
                rows = db.execute("SELECT * FROM events WHERE seq>? AND connection_id IN (" + ",".join("?" * len(allowed)) + ") ORDER BY seq LIMIT ?", (after, *allowed, limit)).fetchall()
        return [{**dict(r), "data": json.loads(r["data"])} for r in rows]

    def _enqueue(self, db, connection_id, action, parameters, idem, profile_revision):
        payload_hash = digest(canonical({"action": action, "parameters": parameters}))
        old = db.execute("SELECT * FROM operations WHERE connection_id=? AND idempotency_key=?", (connection_id, idem)).fetchone()
        if old:
            if old["payload_hash"] != payload_hash: raise BridgeError("idempotency_conflict", "Chave já usada com outro conteúdo.", 409)
            return old["id"]
        resource = str(parameters.get("client_id") or parameters.get("reseller_id") or "__account__")
        if db.execute("SELECT 1 FROM operations WHERE connection_id=? AND status='reconciliation_required'", (connection_id,)).fetchone():
            raise BridgeError("reconciliation_pending", "Há uma operação incerta nesta conexão. Confira o painel antes de outra alteração.", 409)
        if db.execute("SELECT 1 FROM operations WHERE connection_id=? AND resource=? AND status IN ('queued','running')", (connection_id, resource)).fetchone():
            raise BridgeError("resource_busy", "Já existe operação pendente para este cliente/recurso.", 409)
        identifier = uid("op_"); stamp = now()
        db.execute("INSERT INTO operations(id,connection_id,action,resource,idempotency_key,payload_hash,payload,profile_revision,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (identifier, connection_id, action, resource, idem, payload_hash, self.vault.seal(parameters), profile_revision, "queued", stamp, stamp))
        self._event(db, connection_id, "operation.queued", {"operation_id": identifier, "action": action})
        return identifier

    def enqueue(self, connection_id, action, parameters, idem, revision):
        with self.db(True) as db:
            identifier = self._enqueue(db, connection_id, action, parameters, idem, revision)
        return self.operation(identifier)

    def operation(self, identifier, private=False):
        with self.db() as db: row = db.execute("SELECT * FROM operations WHERE id=?", (identifier,)).fetchone()
        if not row: raise BridgeError("not_found", "Operação não encontrada.", 404)
        d = dict(row)
        if private: d["parameters"] = self.vault.open(d["payload"])
        d.pop("payload"); d.pop("payload_hash")
        d["result"] = json.loads(d["result"]) if d["result"] else None
        return d

    def operations(self, allowed=None, limit=100):
        with self.db() as db:
            if allowed is None:
                rows = db.execute("SELECT id FROM operations ORDER BY created_at DESC,rowid DESC LIMIT ?", (limit,)).fetchall()
            elif not allowed: return []
            else:
                rows = db.execute("SELECT id FROM operations WHERE connection_id IN (" + ",".join("?" * len(allowed)) + ") ORDER BY created_at DESC,rowid DESC LIMIT ?", (*allowed, limit)).fetchall()
        return [self.operation(r["id"]) for r in rows]

    def claim(self):
        with self.db(True) as db:
            row = db.execute("""SELECT * FROM operations o WHERE status='queued' AND NOT EXISTS
                (SELECT 1 FROM operations b WHERE b.connection_id=o.connection_id AND b.status IN ('running','reconciliation_required'))
                ORDER BY created_at,rowid LIMIT 1""").fetchone()
            if not row: return None
            db.execute("UPDATE operations SET status='running',updated_at=? WHERE id=?", (now(), row["id"]))
            self._event(db, row["connection_id"], "operation.started", {"operation_id": row["id"]})
        return self.operation(row["id"], True)

    def finish(self, identifier, status, result=None, error=None):
        with self.db(True) as db:
            row = db.execute("SELECT * FROM operations WHERE id=?", (identifier,)).fetchone()
            db.execute("UPDATE operations SET status=?,result=?,error_code=?,updated_at=? WHERE id=?", (status, canonical(redact(result)) if result is not None else None, error, now(), identifier))
            self._event(db, row["connection_id"], "operation." + status, {"operation_id": identifier, "action": row["action"], "status": status, "error_code": error})

    def recover(self):
        with self.db(True) as db:
            rows = db.execute("SELECT id,connection_id FROM operations WHERE status='running'").fetchall()
            for row in rows:
                db.execute("UPDATE operations SET status='reconciliation_required',error_code='interrupted',updated_at=? WHERE id=?", (now(), row["id"]))
                self._event(db, row["connection_id"], "operation.reconciliation_required", {"operation_id": row["id"], "error_code": "interrupted"})

    def reconcile(self, identifier, outcome, evidence):
        with self.db(True) as db:
            row = db.execute("SELECT * FROM operations WHERE id=?", (identifier,)).fetchone()
            if not row: raise BridgeError("not_found", "Operação não encontrada.", 404)
            if row["status"] != "reconciliation_required": raise BridgeError("invalid_status", "Somente operações incertas podem ser conciliadas.", 409)
            db.execute("UPDATE operations SET status=?,result=?,updated_at=? WHERE id=?", (outcome, canonical({"manual_reconciliation": True, "evidence": evidence}), now(), identifier))
            self._event(db, row["connection_id"], "operation.reconciled", {"operation_id": identifier, "outcome": outcome})
        return self.operation(identifier)

    def cancel(self, identifier):
        with self.db(True) as db:
            row = db.execute("SELECT * FROM operations WHERE id=?", (identifier,)).fetchone()
            if not row: raise BridgeError("not_found", "Operação não encontrada.", 404)
            if row["status"] != "queued": raise BridgeError("invalid_status", "Só é possível cancelar uma operação ainda na fila.", 409)
            db.execute("UPDATE operations SET status='cancelled',updated_at=? WHERE id=?", (now(), identifier))
            self._event(db, row["connection_id"], "operation.cancelled", {"operation_id": identifier})
        return self.operation(identifier)

    def cache_clients(self, connection_id, rows):
        stamp = now()
        with self.db(True) as db:
            for row in rows:
                if row.get("id") is not None:
                    db.execute("INSERT INTO clients VALUES(?,?,?,?) ON CONFLICT(connection_id,client_id) DO UPDATE SET data=excluded.data,synced_at=excluded.synced_at", (connection_id, str(row["id"]), self.vault.seal(row), stamp))
        # Incremental cache: a page never implies removal of clients from other pages.

    def cached_clients(self, connection_id, offset=0, limit=100):
        with self.db() as db:
            total = db.execute("SELECT count(*) FROM clients WHERE connection_id=?", (connection_id,)).fetchone()[0]
            rows = db.execute("SELECT * FROM clients WHERE connection_id=? ORDER BY client_id LIMIT ? OFFSET ?", (connection_id, limit, offset)).fetchall()
        return {"source": "local_cache", "total": total, "data": [{**self.vault.open(r["data"]), "synced_at": r["synced_at"]} for r in rows]}

    def create_schedule(self, connection_id, request):
        identifier = uid("sch_")
        with self.db(True) as db:
            revision = db.execute("SELECT revision FROM connections WHERE id=?", (connection_id,)).fetchone()[0]
            db.execute("INSERT INTO schedules VALUES(?,?,?,?,?,?,?,?,?,?,?)", (identifier, connection_id, request.name, request.client_id, self.vault.seal(request.parameters), request.run_at, request.interval_days, revision, "scheduled", None, now()))
            self._event(db, connection_id, "schedule.created", {"schedule_id": identifier})
        return identifier

    def schedules(self, allowed=None):
        with self.db() as db: rows = db.execute("SELECT * FROM schedules ORDER BY run_at").fetchall()
        return [{**{k: r[k] for k in r.keys() if k != "parameters"}, "parameters": redact(self.vault.open(r["parameters"]))} for r in rows if allowed is None or r["connection_id"] in allowed]

    def pause_schedule(self, identifier):
        with self.db(True) as db:
            row = db.execute("SELECT * FROM schedules WHERE id=?", (identifier,)).fetchone()
            if not row: raise BridgeError("not_found", "Agendamento não encontrado.", 404)
            db.execute("UPDATE schedules SET status='paused' WHERE id=?", (identifier,))
            self._event(db, row["connection_id"], "schedule.paused", {"schedule_id": identifier})

    def tick_schedules(self):
        """At-most-one pending execution per schedule; no catch-up charging."""
        stamp = now()
        with self.db(True) as db:
            for r in db.execute("SELECT * FROM schedules WHERE status='waiting'").fetchall():
                op = db.execute("SELECT status FROM operations WHERE id=?", (r["last_operation"],)).fetchone()
                if op and op["status"] == "succeeded":
                    if not r["interval_days"]:
                        db.execute("UPDATE schedules SET status='completed' WHERE id=?", (r["id"],))
                    else:
                        date = datetime.fromisoformat(r["run_at"]) + timedelta(days=r["interval_days"])
                        while date <= datetime.now(timezone.utc): date += timedelta(days=r["interval_days"])
                        db.execute("UPDATE schedules SET status='scheduled',run_at=? WHERE id=?", (date.isoformat(timespec="seconds"), r["id"]))
                elif op and op["status"] not in {"queued", "running"}:
                    db.execute("UPDATE schedules SET status='paused' WHERE id=?", (r["id"],))
                    self._event(db, r["connection_id"], "schedule.paused", {"schedule_id": r["id"], "reason": op["status"]})
            for r in db.execute("SELECT * FROM schedules WHERE status='scheduled' AND run_at<=?", (stamp,)).fetchall():
                c = db.execute("SELECT revision,profile FROM connections WHERE id=?", (r["connection_id"],)).fetchone()
                if c["revision"] != r["profile_revision"]:
                    db.execute("UPDATE schedules SET status='paused' WHERE id=?", (r["id"],))
                    self._event(db, r["connection_id"], "schedule.paused", {"schedule_id": r["id"], "reason": "profile_changed"})
                    continue
                profile = self.vault.open(c["profile"])
                endpoint = profile.get("endpoints", {}).get("renew_client", {})
                if not endpoint.get("verified") or not endpoint.get("success_path"):
                    db.execute("UPDATE schedules SET status='paused' WHERE id=?", (r["id"],)); continue
                params = {**self.vault.open(r["parameters"]), "client_id": r["client_id"]}
                try:
                    operation = self._enqueue(db, r["connection_id"], "renew_client", params, "schedule:" + r["id"] + ":" + r["run_at"], c["revision"])
                except BridgeError:
                    db.execute("UPDATE schedules SET status='paused' WHERE id=?", (r["id"],))
                    continue
                db.execute("UPDATE schedules SET status='waiting',last_operation=? WHERE id=?", (operation, r["id"]))

    def add_hook(self, request):
        identifier = uid("hook_")
        with self.db(True) as db:
            db.execute("INSERT INTO hooks VALUES(?,?,?,?)", (identifier, request.url, self.vault.seal(request.secret), request.enabled))
        return {"id": identifier, "url": request.url, "enabled": request.enabled}

    def hooks(self):
        with self.db() as db: return [dict(r) for r in db.execute("SELECT id,url,enabled FROM hooks")]

    def disable_hook(self, identifier):
        with self.db(True) as db:
            db.execute("UPDATE hooks SET enabled=0 WHERE id=?", (identifier,))
            db.execute("UPDATE deliveries SET status='cancelled' WHERE hook_id=? AND status='pending'", (identifier,))

    def pending_delivery(self):
        with self.db() as db:
            r = db.execute("SELECT d.*,h.url,h.secret,e.id AS event_id,e.type,e.connection_id,e.data,e.created_at FROM deliveries d JOIN hooks h ON h.id=d.hook_id JOIN events e ON e.seq=d.event_seq WHERE d.status='pending' AND d.next_at<=? AND h.enabled=1 ORDER BY d.next_at LIMIT 1", (now(),)).fetchone()
        return dict(r) if r else None

    def finish_delivery(self, identifier, delivered):
        with self.db(True) as db:
            r = db.execute("SELECT attempts FROM deliveries WHERE id=?", (identifier,)).fetchone()
            attempt = r["attempts"] + 1
            next_at = (datetime.now(timezone.utc) + timedelta(seconds=min(3600, 5 * (2 ** attempt)))).isoformat(timespec="seconds")
            db.execute("UPDATE deliveries SET attempts=?,status=?,next_at=? WHERE id=?", (attempt, "delivered" if delivered else "failed" if attempt >= 8 else "pending", next_at, identifier))
