"""Integrated browser launch and offline packaging self-test. Never installs software."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

from .errors import BridgeError


async def launch_browser(playwright, *, headless: bool = True):
    """Use the packaged Chromium; report packaging failures separately from login."""
    from playwright.async_api import Error as PlaywrightError

    executable = Path(playwright.chromium.executable_path).resolve()
    if not executable.is_file():
        raise BridgeError("browser_unavailable", "Pacote incompleto: Chromium integrado ausente. Reinstale a distribuição completa, preservando a pasta de dados.", 503)
    if getattr(sys, "frozen", False):
        bundle = Path(sys._MEIPASS).resolve()
        if not executable.is_relative_to(bundle):
            raise BridgeError("browser_unavailable", "O navegador deve pertencer ao pacote da aplicação, não a uma instalação externa.", 503)
    try:
        return await playwright.chromium.launch(headless=headless)
    except PlaywrightError as exc:
        raise BridgeError("browser_unavailable", "Não foi possível iniciar o Chromium integrado. Confira a integridade do pacote e as permissões da instalação.", 503) from exc


async def self_test() -> dict:
    """Open a local document only; no provider credentials or network navigation."""
    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        browser = await launch_browser(playwright)
        try:
            context = await browser.new_context(service_workers="block", accept_downloads=False)
            async def deny_network(route):
                await route.abort()
            await context.route("**/*", deny_network)
            await context.set_offline(True)
            page = await context.new_page()
            await page.set_content("<title>Reseller integrated browser</title><p id='result'>ready</p>")
            if await page.title() != "Reseller integrated browser" or await page.locator("#result").inner_text() != "ready":
                raise RuntimeError("Integrated browser render failed")
            return {"status": "ok", "engine": "chromium", "version": browser.version,
                    "frozen": bool(getattr(sys, "frozen", False)), "network": "offline"}
        finally:
            await browser.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--diagnostic", action="store_true", help="Incluir causa local do teste offline (sem credenciais)")
    args = parser.parse_args(argv)
    try:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        result = asyncio.run(self_test())
        status = 0
    except Exception as exc:
        result = {"status": "error", "error_type": type(exc).__name__}
        if isinstance(exc, BridgeError):
            result["error_code"] = exc.code
        if args.diagnostic:
            # Este teste usa apenas HTML local, sem login, token ou rede.
            # Exibir a causa do Playwright permite distinguir falta de DLL/SO,
            # sandbox, permissões e esgotamento de recursos no Docker.
            cause = exc.__cause__ or exc
            result["cause_type"] = type(cause).__name__
            result["detail"] = str(cause)[-3000:]
        status = 1
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if sys.stdout:
        print(json.dumps(result))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
