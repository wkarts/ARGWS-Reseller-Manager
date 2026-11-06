from dataclasses import dataclass, field
from pathlib import Path
import os

@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("RESMAN_DATA", "./data")).resolve())
    host: str = field(default_factory=lambda: os.getenv("RESMAN_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("RESMAN_PORT", "48190")))
    # Exact hosts only. Private targets additionally require the second allowlist.
    allowed_hosts: tuple[str, ...] = field(default_factory=lambda: tuple(x.strip().lower() for x in os.getenv("RESMAN_ALLOWED_HOSTS", "servip2p.com").split(",") if x.strip()))
    private_hosts: tuple[str, ...] = field(default_factory=lambda: tuple(x.strip().lower() for x in os.getenv("RESMAN_PRIVATE_HOSTS", "").split(",") if x.strip()))
    public_origin: str = field(default_factory=lambda: os.getenv("RESMAN_PUBLIC_ORIGIN", ""))
    worker_enabled: bool = True
    request_timeout: float = 30.0
    max_upstream_bytes: int = 8 * 1024 * 1024
    browser_enabled: bool = field(default_factory=lambda: os.getenv("RESMAN_BROWSER_ENABLED", "0") == "1")
    browser_headless: bool = field(default_factory=lambda: os.getenv("RESMAN_BROWSER_HEADLESS", "1") != "0")
    # Dependency injection only in tests, never enabled by an environment variable.
    test_network: bool = False
