from __future__ import annotations
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import re
from cryptography.fernet import Fernet, InvalidToken
from .errors import BridgeError

SENSITIVE = re.compile(r"password|passwd|senha|token|secret|cookie|authorization|api.?key|csrf|session", re.I)

def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

def private_write(path: Path, value: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(value)
    if os.name != "nt":
        path.chmod(0o600)

class Vault:
    def __init__(self, path: Path):
        if not path.exists():
            private_write(path, Fernet.generate_key())
        self.fernet = Fernet(path.read_bytes().strip())

    def seal(self, value) -> str:
        return self.fernet.encrypt(json.dumps(value, ensure_ascii=False).encode()).decode()

    def open(self, value: str):
        try:
            return json.loads(self.fernet.decrypt(value.encode()))
        except (InvalidToken, ValueError) as e:
            raise BridgeError("vault_unavailable", "Não foi possível abrir os dados protegidos. Restaure a chave original junto ao banco.", 503) from e

def redact(value):
    if isinstance(value, dict):
        return {k: "[PROTEGIDO]" if SENSITIVE.search(k) else redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value

class InstanceLock:
    """One process per data directory: prevents concurrent local queue recovery."""
    def __init__(self, path: Path):
        self.path, self.file = path, None

    def acquire(self):
        self.file = self.path.open("a+b")
        self.file.seek(0)
        if self.path.stat().st_size == 0:
            self.file.write(b"0"); self.file.flush()
        self.file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.file.close(); self.file = None
            raise RuntimeError("Esta pasta de dados já está em uso. Execute somente um processo/worker.")

    def release(self):
        if self.file:
            if os.name == "nt":
                import msvcrt
                self.file.seek(0); msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
            self.file.close(); self.file = None
