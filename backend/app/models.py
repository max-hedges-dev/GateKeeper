from enum import Enum
from typing import List
from pydantic import BaseModel, Field

class Severity(str, Enum):
    info = "info"
    warning = "warning"
    issue = "issue"


class Protocol(str, Enum):
    tcp = "tcp"
    http = "http"
    https = "https"


class PortCheck(BaseModel):
    name: str = Field(..., description="Human name for the check")
    port: int = Field(..., ge=1, le=65535)
    protocol: Protocol = Protocol.tcp
    severity: Severity
    advice: str


class ChecksConfig(BaseModel):
    checks: List[PortCheck]

class RuleTarget(str, Enum):
    headers = "headers"
    body = "body"
    status = "status"

class RegexRule(BaseModel):
    id: str
    description: str
    target: RuleTarget
    pattern: str = Field(..., description="Python-style regex")
    severity: Severity
    advice: str

class RulesConfig(BaseModel):
    rules: List[RegexRule]