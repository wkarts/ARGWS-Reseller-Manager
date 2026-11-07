"""Read-only metadata extraction for saved HTML, HAR and Postman collections.

No HTTP client, browser automation or external requests. Never include supplied
field VALUES, credentials, cookies, response bodies or query values in output.
"""
from __future__ import annotations

import json
import re
from typing import Any, Literal
from urllib.parse import parse_qsl, urljoin, urlsplit
from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, Field
from .errors import BridgeError

MAX_BYTES = 2 * 1024 * 1024
MAX_ITEMS = 400
DANGER = re.compile(r"(?:delete|remove|renew|pay|credit|transfer|recharg|migrat|activate|disable|block|create|edit|update|test|fast_client|logout|reset|save)", re.I)


class EvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: Literal["html", "har", "postman"]
    document: str | dict[str, Any]


def path_info(value: str, origin: str):
    if not isinstance(value, str) or not value or len(value) > 2048:
        return None
    if value.lower().startswith(("javascript:", "data:", "mailto:", "tel:")):
        return None
    base = urlsplit(origin)
    parsed = urlsplit(urljoin(origin + "/", value))
    def authority(p):
        return p.scheme, p.hostname, p.port or (443 if p.scheme == "https" else 80)
    if authority(base) != authority(parsed) or parsed.username or parsed.password:
        return None
    if len(parsed.path) > 240:
        return None
    keys = sorted({str(k)[:80] for k, _ in parse_qsl(parsed.query, keep_blank_values=True)})[:60]
    return (parsed.path or "/"), keys


def body_field_names(postdata):
    if not isinstance(postdata, dict):
        return []
    names = {str(p.get("name", p.get("key")))[:80] for p in postdata.get("params", [])[:100]
             if isinstance(p, dict) and p.get("name", p.get("key"))}
    raw = postdata.get("text", "")
    if not names and isinstance(raw, str) and len(raw) < 100000:
        mime = postdata.get("mimeType", "")
        if "json" in mime:
            try:
                item = json.loads(raw)
                if isinstance(item, dict):
                    names.update(str(k)[:80] for k in item)
            except ValueError:
                pass
        elif "urlencoded" in mime:
            names.update(str(k)[:80] for k, _ in parse_qsl(raw, keep_blank_values=True))
    return sorted(names)[:100]


def classify(method, path, query):
    if method not in ("GET", "HEAD") or DANGER.search(path) or any(DANGER.search(k) for k in query):
        return "possible_side_effect"
    return "read_candidate_not_verified"


def suggestion(path, query):
    if path == "/clients/api/" and "get_clients" in query:
        return ["list_clients"]
    if path == "/clients/":
        return ["list_clients"]
    if path == "/resellers/":
        return ["list_resellers"]
    return []


def record(method, url, origin, body=(), status=None):
    parts = path_info(url, origin)
    if not parts:
        return None
    path, query = parts
    method = str(method).upper()[:8]
    return {"method": method, "path": path,
            "query_field_names": query, "body_field_names": sorted(set(body))[:100],
            "risk": classify(method, path, query),
            "suggested_actions_unverified": suggestion(path, query),
            "observed_http_status": status if isinstance(status, int) else None,
            "verified": False}


def inspect_offline(payload: EvidenceRequest, origin: str):
    raw = payload.document
    length = len(raw.encode("utf-8")) if isinstance(raw, str) else len(json.dumps(raw, ensure_ascii=False).encode("utf-8"))
    if length > MAX_BYTES:
        raise BridgeError("inspection_too_large", "Arquivo maior que 2 MiB. Separe e sanitize as evidências.", 413)
    if urlsplit(origin).scheme != "https":
        raise BridgeError("inspection_origin", "A origem do fornecedor deve ser HTTPS.", 422)
    requests, forms, navigation = [], [], []
    truncated = False
    if payload.format == "html":
        if not isinstance(raw, str):
            raise BridgeError("invalid_html", "Envie o HTML como texto.", 422)
        soup = BeautifulSoup(raw, "html.parser")
        allforms, allanchors = soup.select("form"), soup.select("a[href]")
        truncated = len(allforms) > MAX_ITEMS or len(allanchors) > MAX_ITEMS
        for item in allforms[:MAX_ITEMS]:
            loc = path_info(item.get("action") or "/", origin)
            if not loc:
                continue
            path, query = loc
            method = str(item.get("method", "GET")).upper()
            fields = []
            for node in item.select("input[name],select[name],textarea[name]")[:100]:
                fields.append({"name": str(node.get("name"))[:80],
                               "type": str(node.get("type", node.name))[:32],
                               "required": node.has_attr("required")})
            forms.append({"method": method, "action_path": path, "query_field_names": query,
                          "fields": fields, "risk": classify(method, path, query), "verified": False})
        for item in allanchors[:MAX_ITEMS]:
            loc = path_info(item.get("href"), origin)
            if loc:
                path, query = loc
                navigation.append({"path": path, "query_field_names": query,
                                   "risk": classify("GET", path, query), "verified": False})
    elif payload.format == "har":
        if not isinstance(raw, dict) or not isinstance(raw.get("log"), dict):
            raise BridgeError("invalid_har", "Documento não é HAR.", 422)
        entries = raw["log"].get("entries", [])
        if not isinstance(entries, list):
            raise BridgeError("invalid_har", "Entradas HAR inválidas.", 422)
        truncated = len(entries) > MAX_ITEMS
        for entry in entries[:MAX_ITEMS]:
            if not isinstance(entry, dict):
                continue
            request = entry.get("request", {})
            response = entry.get("response", {})
            if not isinstance(request, dict):
                continue
            found = record(request.get("method", ""), request.get("url", ""), origin,
                           body_field_names(request.get("postData", {})),
                           response.get("status") if isinstance(response, dict) else None)
            if found:
                requests.append(found)
    else:
        if not isinstance(raw, dict):
            raise BridgeError("invalid_postman", "Envie uma coleção JSON.", 422)
        collection = raw.get("collection", raw)
        if not isinstance(collection, dict) or not isinstance(collection.get("item"), list):
            raise BridgeError("invalid_postman", "Coleção Postman inválida.", 422)
        def walk(items, depth=0):
            nonlocal truncated
            if depth > 10:
                truncated = True
                return
            for item in items:
                if len(requests) >= MAX_ITEMS:
                    truncated = True
                    return
                if not isinstance(item, dict):
                    continue
                if isinstance(item.get("item"), list):
                    walk(item["item"], depth + 1)
                    continue
                req = item.get("request", {})
                if not isinstance(req, dict):
                    continue
                addr = req.get("url", "")
                if isinstance(addr, dict):
                    addr = addr.get("raw", "")
                if isinstance(addr, str) and addr.startswith("{{"):
                    addr = re.sub(r"^\{\{[^{}]+\}\}", origin, addr, count=1)
                body = req.get("body", {})
                names = []
                if isinstance(body, dict):
                    if body.get("mode") == "raw":
                        names = body_field_names({"mimeType": "application/json", "text": body.get("raw", "")})
                    elif body.get("mode") in ("urlencoded", "formdata"):
                        names = sorted({str(x.get("key"))[:80] for x in body.get(body["mode"], [])
                                        if isinstance(x, dict) and x.get("key")})
                found = record(req.get("method", "GET"), addr, origin, names)
                if found:
                    requests.append(found)
        walk(collection["item"])
    dedup = {}
    for row in requests:
        key = (row["method"], row["path"], tuple(row["query_field_names"]), tuple(row["body_field_names"]))
        if key not in dedup:
            dedup[key] = {**row, "observations": 0, "observed_status_codes": []}
        dedup[key]["observations"] += 1
        status = row["observed_http_status"]
        if status is not None and status not in dedup[key]["observed_status_codes"]:
            dedup[key]["observed_status_codes"].append(status)
        dedup[key].pop("observed_http_status", None)
    routes = list(dedup.values())
    return {
        "format": payload.format, "dry_run": True, "upstream_request_sent": False,
        "executed": False, "credentials_returned": False, "scripts_executed": False,
        "contracts_auto_verified": False,
        "summary": {"requests": len(routes), "forms": len(forms), "links": len(navigation),
                    "truncated": truncated,
                    "possible_side_effect_items": sum(x["risk"] == "possible_side_effect" for x in routes + forms + navigation)},
        "routes": routes, "forms": forms, "navigation": navigation,
        "suggested_actions_unverified": sorted({name for row in routes for name in row["suggested_actions_unverified"]}),
        "note": "Somente metadados de arquivos locais, sem HTTP remoto. Não valida a existência ou segurança das operações.",
    }
