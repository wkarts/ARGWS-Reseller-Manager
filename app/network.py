"""Restrict integration traffic to explicitly allowed hosts and same-origin paths."""
from __future__ import annotations
import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit, urljoin
import httpx
from .errors import BridgeError
from .models import relative_path


class NetworkPolicy:
    def __init__(self, settings): self.settings = settings

    async def validate(self, url: str):
        p = urlsplit(url)
        host = (p.hostname or "").lower()
        if p.scheme not in {"https", "http"} or not host or p.username or p.password or p.fragment:
            raise BridgeError("invalid_target", "URL de destino inválida.", 422)
        if host not in self.settings.allowed_hosts:
            raise BridgeError("host_not_allowed", "Host não permitido. Configure RESMAN_ALLOWED_HOSTS no servidor.", 403)
        private_allowed = host in self.settings.private_hosts
        if p.scheme != "https" and not private_allowed:
            raise BridgeError("https_required", "O destino exige HTTPS. HTTP somente para hosts privados explicitamente autorizados.", 422)
        if self.settings.test_network: return
        try:
            records = await asyncio.get_running_loop().getaddrinfo(host, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)
        except (OSError, ValueError) as exc:
            raise BridgeError("dns_unavailable", "Não foi possível resolver o host configurado.", 502) from exc
        if not records: raise BridgeError("dns_unavailable", "Host sem endereço.", 502)
        if not private_allowed and any(not ipaddress.ip_address(r[4][0]).is_global for r in records):
            raise BridgeError("private_target_blocked", "Destino privado/reservado não autorizado.", 403)

    def relative_url(self, base: str, path: str) -> str:
        try: relative_path(path)
        except ValueError as exc: raise BridgeError("invalid_path", str(exc), 422) from exc
        return base.rstrip("/") + path

    def same_origin(self, base: str, url: str) -> str:
        url = urljoin(base + "/", url)
        a, b = urlsplit(base), urlsplit(url)
        def origin(p): return (p.scheme, p.hostname, p.port or (443 if p.scheme == "https" else 80))
        if origin(a) != origin(b) or b.username or b.password:
            raise BridgeError("external_redirect", "Redirecionamento ou formulário externo bloqueado.", 502)
        return url


async def limited_request(client, settings, method, url, **kwargs):
    async with client.stream(method, url, **kwargs) as response:
        content = bytearray()
        async for part in response.aiter_bytes():
            content.extend(part)
            if len(content) > settings.max_upstream_bytes:
                raise BridgeError("upstream_too_large", "Resposta do painel ultrapassou o limite configurado.", 502)
        # aiter_bytes() already decoded gzip/deflate/br and checked the
        # decompressed payload size. Reusing Content-Encoding here would make
        # the new Response decode the same content a second time.
        headers = httpx.Headers(response.headers)
        for name in ("content-encoding", "content-length", "transfer-encoding"):
            if name in headers:
                del headers[name]
        return httpx.Response(response.status_code, headers=headers,
                              content=bytes(content), request=response.request,
                              extensions=response.extensions)
