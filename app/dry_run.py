"""Local-only contract previews. Never contact an upstream server or enqueue work."""
from __future__ import annotations

from typing import Any
from pydantic import Field

from .connector import TOKEN, at
from .errors import BridgeError
from .models import ACTIONS, READ_ACTIONS, Profile, Strict


class DryRunRequest(Strict):
    parameters: dict[str, Any] = Field(default_factory=dict)


def _inputs(value: Any) -> set[str]:
    if isinstance(value, dict):
        names: set[str] = set()
        for item in value.values():
            names.update(_inputs(item))
        return names
    if isinstance(value, list):
        names: set[str] = set()
        for item in value:
            names.update(_inputs(item))
        return names
    if isinstance(value, str):
        return {match.group(2) for match in TOKEN.finditer(value)
                if match.group(1) == "input"}
    return set()


def preview(connection: dict, action: str, params: dict[str, Any] | None = None) -> dict:
    """Return safe metadata, never parameter values, cookies, paths or secrets.

    prepared_locally means the configuration is syntactically ready, NOT that
    the remote endpoint exists or would accept/charge a mutation.
    """
    if action not in ACTIONS:
        raise BridgeError("invalid_action", "Ação desconhecida.", 422)
    params = params or {}
    profile = Profile.model_validate(connection["profile"])
    endpoint = profile.endpoints.get(action)
    kind = "read" if action in READ_ACTIONS else "write"
    result = {
        "action": action, "kind": kind, "dry_run": True,
        "upstream_request_sent": False, "queued": False,
        "executed": False, "credits_charged": False,
        "result": "NOT_EXECUTED",
        "connection_status": connection.get("status", "unknown"),
        "contract_state": "missing", "required_parameter_names": [],
        "missing_parameter_names": [], "request_shape": None,
        "ready_for_live_execution": False,
        "issues": [], "notes": [
            "Verificação exclusivamente local; nenhuma requisição foi enviada ao kOfficePanel.",
            "Não comprova endpoint, permissão, custo, sucesso ou efeito remoto.",
        ],
    }
    if not endpoint:
        result["status"] = "contract_missing"
        result["issues"] = ["contract_missing"]
        return result

    required = set(endpoint.required) | _inputs({
        "path": endpoint.path, "params": endpoint.params,
        "body": endpoint.body, "headers": endpoint.headers,
    })
    missing = sorted(name for name in required if at(params, name) in (None, ""))
    result.update(
        contract_state="verified" if endpoint.verified else "draft",
        required_parameter_names=sorted(required),
        missing_parameter_names=missing,
        request_shape={
            "method": endpoint.method,
            "encoding": endpoint.encoding,
            "query_field_names": sorted(endpoint.params),
            "body_field_names": sorted(endpoint.body),
            "success_rule_defined": bool(endpoint.success_path) if kind == "write" else None,
        },
    )
    issues = []
    if not endpoint.verified:
        issues.append("contract_unverified")
    if missing:
        issues.append("missing_parameters")
    if kind == "write":
        if not endpoint.success_path:
            issues.append("success_rule_missing")
        if endpoint.method == "GET":
            issues.append("write_method_requires_review")
        if (connection.get("auth_mode") != "token"
                and connection.get("status") != "authenticated"):
            issues.append("session_read_probe_pending")
    if connection.get("auth_mode") == "token" and not profile.token_auth.name:
        issues.append("token_contract_missing")
    result["issues"] = issues
    result["status"] = "needs_validation" if issues else "prepared_locally"
    result["notes"].append(
        "Nenhum parâmetro é transmitido ou armazenado no dry-run. Não use este resultado como autorização para operações reais.")
    return result


def matrix(connection: dict) -> dict:
    return {
        "dry_run": True, "upstream_request_sent": False,
        "connection_status": connection.get("status", "unknown"),
        "operations": [preview(connection, action) for action in sorted(ACTIONS)],
        "note": "Inventário local de contratos, sem execução de ações remotas.",
    }
