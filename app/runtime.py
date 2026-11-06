"""Single-process runtime shared by Docker, source execution and Windows bundle."""
from __future__ import annotations
import argparse
import asyncio
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import uvicorn
from .main import create_app
from .settings import Settings


def configure_logs(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(directory / "application.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers): root.addHandler(handler)
    # Upstream libraries may include URLs with secret query parameters.
    for name in ("httpx", "httpcore", "urllib3", "playwright"):
        logger = logging.getLogger(name); logger.setLevel(logging.CRITICAL); logger.propagate = False


def make_server(settings):
    configure_logs(settings.data_dir / "logs")
    return uvicorn.Server(uvicorn.Config(create_app(settings), host=settings.host, port=settings.port, loop="asyncio", http="h11", ws="websockets", workers=1, reload=False, log_config=None, access_log=False, proxy_headers=False, timeout_graceful_shutdown=40))


def run_server(server):
    # asyncio.run uses Proactor on Windows; don't let a reload supervisor select a different loop.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(server.serve())


def main(argv=None):
    parser = argparse.ArgumentParser(description="Reseller Manager — API e painel web")
    parser.add_argument("--host", default=os.getenv("RESMAN_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("RESMAN_PORT", "48190")))
    parser.add_argument("--data", default=os.getenv("RESMAN_DATA", "./data"))
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args(argv)
    if args.version:
        from . import __version__
        print(__version__); return
    if not 1024 <= args.port <= 65535: parser.error("Porta deve estar entre 1024 e 65535.")
    settings = Settings(data_dir=Path(args.data).expanduser().resolve(), host=args.host, port=args.port)
    server = make_server(settings)
    if sys.stdout:
        print(f"Reseller Manager: http://{args.host}:{args.port}")
        print(f"Token inicial: {settings.data_dir / 'admin.token'} (não compartilhe)")
    run_server(server)


if __name__ == "__main__": main()
