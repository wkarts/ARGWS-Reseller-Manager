"""Offline inspection only: Postman v2/v2.1 and HAR. Never execute scripts or requests."""
from __future__ import annotations
import json
import re
from urllib.parse import urlsplit, parse_qsl
from .security import SENSITIVE
from .errors import BridgeError

VAR = re.compile(r"\{\{([^{}]+)\}\}")


def placeholders(value, key=""):
    if isinstance(value, dict): return {k: placeholders(v, k) for k, v in value.items()}
    if isinstance(value, list): return [placeholders(v, key) for v in value]
    if SENSITIVE.search(key): return "{{input." + re.sub(r"\W", "_", key) + "}}"
    if isinstance(value, str):
        return VAR.sub(lambda m: m[0] if m[1].startswith(("input.", "secret.", "session.")) else "{{input." + re.sub(r"\W", "_", m[1]) + "}}", value)
    return value


def auth_info(auth):
    if not isinstance(auth, dict): return None
    type_ = auth.get("type")
    if type_ == "bearer": return {"location": "header", "name": "Authorization", "prefix": "Bearer "}
    if type_ == "apikey":
        values = {v.get("key"): v.get("value") for v in auth.get("apikey", []) if isinstance(v, dict)}
        return {"location": "query" if values.get("in") == "query" else "header", "name": values.get("key", ""), "prefix": ""}
    return None


def draft(name, request, inherited_auth=None):
    url = request.get("url", "")
    raw = url.get("raw", "") if isinstance(url, dict) else url
    if not isinstance(raw, str): raw = ""
    # Remove a host variable, never evaluate its value from a collection environment.
    raw = re.sub(r"^\{\{[^{}]+\}\}(?=/|$)", "https://placeholder.invalid", raw)
    parsed = urlsplit(raw)
    path = parsed.path or "/"
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if isinstance(url, dict):
        query.update({x["key"]: x.get("value", "") for x in url.get("query", []) if not x.get("disabled") and x.get("key")})
    method = request.get("method", "GET").upper()
    headers = {}
    warnings = []
    auth = auth_info(request.get("auth") or inherited_auth)
    for h in request.get("header", request.get("headers", [])):
        if h.get("disabled"): continue
        key, val = h.get("key", h.get("name", "")), h.get("value", "")
        if not key: continue
        if SENSITIVE.search(key) or key.lower() in {"host", "connection", "content-length", "content-type", "transfer-encoding"}: continue
        # Preserve only clearly non-sensitive standard headers.
        if key.lower() in {"accept", "x-requested-with"}: headers[key] = val
    body = request.get("body", {})
    encoding, data = "query", {}
    if body.get("mode") == "raw":
        encoding = "json"
        try:
            data = json.loads(body.get("raw", "{}"))
            if not isinstance(data, dict): data = {}; warnings.append("Corpo JSON não é objeto; mapeamento manual necessário.")
        except (ValueError, TypeError): warnings.append("Corpo não interpretado como JSON; ajuste manualmente.")
    elif body.get("mode") in {"urlencoded", "formdata"}:
        encoding = "form"
        data = {x["key"]: x.get("value", "") for x in body.get(body["mode"], []) if x.get("key") and not x.get("disabled") and x.get("type") != "file"}
    if method == "GET": data = {}; encoding = "query"
    data, query = placeholders(data), placeholders(query)
    result = {"method": method, "path": placeholders(path), "encoding": encoding, "params": query, "body": data, "headers": headers, "required": [], "verified": False, "evidence": "", "data_path": "data", "fields": {}, "success_path": None, "success_value": True, "success_status": [200, 201]}
    references = re.findall(r"\{\{input\.([^{}]+)\}\}", json.dumps(result))
    result["required"] = sorted(set(references))
    if request.get("event"): warnings.append("Scripts ignorados.")
    return {"name": str(name)[:200], "host_hint": parsed.hostname, "draft": result, "token_auth_hint": auth, "warnings": warnings, "state": "unverified"}


def inspect_document(document):
    if not isinstance(document, dict): raise BridgeError("invalid_import", "Envie um objeto JSON de coleção Postman ou HAR.", 422)
    if isinstance(document.get("collection"), dict): document = document["collection"]
    results = []
    if "item" in document:
        def walk(items, parent="", inherited=None, depth=0):
            if depth > 12: raise BridgeError("import_too_deep", "Coleção muito profunda.", 422)
            for item in items:
                if len(results) >= 500: raise BridgeError("import_too_large", "Limite de 500 requisições por importação.", 422)
                name = parent + str(item.get("name", "Requisição"))
                if "item" in item: walk(item["item"], name + " / ", item.get("auth", inherited), depth + 1)
                elif isinstance(item.get("request"), dict): results.append(draft(name, item["request"], inherited))
        walk(document["item"], inherited=document.get("auth"))
        type_ = "postman"
    elif isinstance(document.get("log"), dict):
        entries = document["log"].get("entries", [])
        if len(entries) > 500: raise BridgeError("import_too_large", "Limite de 500 entradas HAR.", 422)
        for e in entries:
            r = e.get("request", {})
            body = r.get("postData", {})
            converted = {"url": r.get("url", ""), "method": r.get("method", "GET"), "headers": r.get("headers", [])}
            if "json" in body.get("mimeType", ""): converted["body"] = {"mode": "raw", "raw": body.get("text", "{}")}
            elif "application/x-www-form-urlencoded" in body.get("mimeType", ""):
                fields = body.get("params") or [{"name": k, "value": v} for k, v in parse_qsl(body.get("text", ""), keep_blank_values=True)]
                converted["body"] = {"mode": "urlencoded", "urlencoded": [{"key": x.get("name"), "value": x.get("value", "")} for x in fields]}
            results.append(draft(urlsplit(r.get("url", "")).path, converted))
        type_ = "har"
    else: raise BridgeError("unsupported_import", "JSON não reconhecido como Postman v2/v2.1 ou HAR.", 422)
    return {"format": type_, "requests": results, "executed": False, "note": "Inspeção local. Não executa scripts nem requisições. Revise parâmetros, autenticação e regra de sucesso antes de habilitar."}
