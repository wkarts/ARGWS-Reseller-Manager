from __future__ import annotations
from typing import Any, Literal
from urllib.parse import urlsplit, unquote
import re
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

READ_ACTIONS = {"list_clients", "get_client", "list_plans", "list_technologies", "get_balance", "list_resellers", "get_reseller", "list_payments"}
WRITE_ACTIONS = {"create_client", "renew_client", "change_plan", "change_screens", "migrate_technology", "enable_client", "disable_client", "delete_client", "create_reseller", "update_reseller", "credit_transfer", "create_payment"}
ACTIONS = READ_ACTIONS | WRITE_ACTIONS

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")

def relative_path(v: str) -> str:
    # Also reject encoded network paths/traversal and backslashes.
    decoded = unquote(v)
    p = urlsplit(v)
    if not v.startswith("/") or decoded.startswith("//") or p.scheme or p.netloc or p.fragment or "\\" in decoded or any(x == ".." for x in decoded.split("/")) or any(ord(x) < 32 for x in decoded):
        raise ValueError("Use um caminho relativo seguro, iniciando por /, sem host ou fragmento.")
    return v

class Endpoint(Strict):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET"
    path: str
    encoding: Literal["query", "json", "form"] = "query"
    params: dict[str, Any] = Field(default_factory=dict)
    body: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)
    verified: bool = False
    evidence: str = ""
    data_path: str = "data"
    fields: dict[str, str] = Field(default_factory=dict)
    success_path: str | None = None
    success_value: Any = True
    success_status: list[int] = Field(default_factory=lambda: [200, 201])
    _path = field_validator("path")(relative_path)

    @model_validator(mode="after")
    def validate_map(self):
        if self.verified and not self.evidence.strip():
            raise ValueError("Registre a evidência que confirma este contrato.")
        if self.method == "GET" and self.body:
            raise ValueError("GET não aceita corpo neste conector; use params.")
        for key, value in self.headers.items():
            if key.lower() in {"host", "cookie", "authorization", "proxy-authorization", "connection", "content-length", "transfer-encoding"}:
                raise ValueError("Cabeçalho reservado; autenticação deve ser configurada em token_auth.")
            if "\n" in key + value or "\r" in key + value:
                raise ValueError("Cabeçalho inválido.")
        for name in self.fields:
            if name not in {"id", "username", "name", "expires_at", "plan", "screens", "technology", "status", "credits", "amount", "created_at"}:
                raise ValueError("Campo de saída não permitido. Credenciais nunca são exportadas na listagem.")
        return self

class TokenAuth(Strict):
    location: Literal["header", "query", "body"] = "header"
    name: str = ""
    prefix: str = ""
    @field_validator("name", "prefix")
    @classmethod
    def no_controls(cls, value):
        if any(ord(c) < 32 for c in value): raise ValueError("Caracteres de controle não permitidos.")
        return value
    @model_validator(mode="after")
    def header(self):
        if self.location == "header" and self.name.lower() in {"host", "cookie", "connection", "content-length", "transfer-encoding", "proxy-authorization"}:
            raise ValueError("Cabeçalho reservado.")
        return self

class Login(Strict):
    page: str = "/login/"
    username_field: str = ""
    password_field: str = ""
    form_selector: str = "form"
    username_selector: str = 'input[name="username"]'
    password_selector: str = 'input[type="password"]'
    submit_selector: str = 'button[type="submit"], input[type="submit"]'
    success_selector: str = ""
    extra_fields: dict[str, str] = Field(default_factory=dict)
    _path = field_validator("page")(relative_path)

class Profile(Strict):
    name: str = "kOfficePanel - contrato a validar"
    token_auth: TokenAuth = Field(default_factory=TokenAuth)
    login: Login = Field(default_factory=Login)
    endpoints: dict[str, Endpoint] = Field(default_factory=dict)
    @model_validator(mode="after")
    def contracts(self):
        if set(self.endpoints) - ACTIONS: raise ValueError("Ação não reconhecida.")
        for action, endpoint in self.endpoints.items():
            if action in WRITE_ACTIONS and endpoint.verified and not endpoint.success_path:
                raise ValueError("Operação de escrita exige success_path explícito.")
        return self

class Credentials(Strict):
    token: str = Field(default="", max_length=8192)
    username: str = Field(default="", max_length=500)
    password: str = Field(default="", max_length=2048)

class ConnectionCreate(Strict):
    name: str = Field(min_length=1, max_length=100)
    base_url: str
    auth_mode: Literal["token", "form", "browser"] = "form"
    credentials: Credentials = Field(default_factory=Credentials)
    profile: Profile = Field(default_factory=Profile)
    @field_validator("base_url")
    @classmethod
    def base(cls, value):
        p = urlsplit(value)
        if p.scheme not in {"https", "http"} or not p.hostname or p.username or p.password or p.query or p.fragment or p.path not in {"", "/"}:
            raise ValueError("URL base deve conter somente protocolo, host e porta.")
        return value.rstrip("/")

class ProfileUpdate(Strict):
    revision: int = Field(ge=1)
    profile: Profile

class WriteRequest(Strict):
    parameters: dict[str, Any] = Field(default_factory=dict)
    confirmed: bool = False

class Reconcile(Strict):
    outcome: Literal["succeeded", "failed"]
    evidence: str = Field(min_length=15, max_length=2000)

class TokenCreate(Strict):
    name: str = Field(min_length=1, max_length=100)
    scope: Literal["admin", "operate", "read"] = "read"
    connection_ids: list[str] | None = None

class ScheduleCreate(Strict):
    name: str = Field(min_length=1, max_length=100)
    client_id: str = Field(min_length=1, max_length=200)
    parameters: dict[str, Any]
    run_at: str
    interval_days: int | None = Field(default=None, ge=1, le=366)
    authorized: bool = False
    # No assumption of payment: this is an explicit standing renewal order.

class PaymentConfirmed(Strict):
    reference: str = Field(min_length=1, max_length=180)
    client_id: str = Field(min_length=1, max_length=200)
    parameters: dict[str, Any]
    confirmed: bool = False

class WebhookCreate(Strict):
    url: str
    secret: str = Field(min_length=32, max_length=200)
    enabled: bool = False
