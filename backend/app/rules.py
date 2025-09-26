# backend/app/rules.py
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
from .models import RulesConfig  # rules: List[Rule] with fields id, target, pattern, severity, advice

def _blob_for(chk: Dict[str, Any], target: str) -> Optional[str]:
    http = chk.get("http") or {}
    if target == "headers":
        return http.get("headers")
    if target == "status":
        s = http.get("status")
        return str(s) if s is not None else None
    if target == "body":
        return http.get("body_snippet")
    return None

def apply_rules(snapshot: Dict[str, Any], rules_cfg: RulesConfig) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for chk in snapshot.get("checks", []):
        chk_name = chk.get("name")
        for rule in rules_cfg.rules:
            target = getattr(rule.target, "value", rule.target)  # enum or str
            blob = _blob_for(chk, target)
            if not blob:
                continue
            try:
                rx = re.compile(rule.pattern)  # inline flags (?i)(?m)(?s) supported
            except re.error as e:
                findings.append({
                    "rule_id": getattr(rule, "id", "<invalid-regex>"),
                    "check": chk_name,
                    "severity": "warning",
                    "advice": f"Invalid regex in rules.yaml: {e}",
                    "evidence": None,
                })
                continue
            m = rx.search(blob)
            if m:
                findings.append({
                    "rule_id": rule.id,
                    "check": chk_name,
                    "severity": getattr(rule.severity, "value", rule.severity),
                    "advice": rule.advice,
                    "evidence": blob[m.start():m.end()][:160],
                })
    return findings