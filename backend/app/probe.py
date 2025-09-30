# backend/app/probe.py
from __future__ import annotations

import platform
import os
import re
import socket
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal, Optional

import requests
from requests.exceptions import RequestException

from .models import ChecksConfig, PortCheck, Protocol
from .utils import load_and_validate


# ---------- gateway discovery ----------

def find_default_gateway() -> str:
    """
    Return the default gateway (router) IPv4 address as a string.
    Cross-platform, no admin required.
    """
    system = platform.system().lower()

    try:
        if "linux" in system:
            out = subprocess.check_output(["ip", "route"], text=True, stderr=subprocess.DEVNULL)
            m = re.search(r"default\s+via\s+(\d+\.\d+\.\d+\.\d+)", out)
            if m:
                return m.group(1)

        elif "darwin" in system:  # macOS
            out = subprocess.check_output(["route", "-n", "get", "default"], text=True, stderr=subprocess.DEVNULL)
            m = re.search(r"gateway:\s+(\d+\.\d+\.\d+\.\d+)", out)
            if m:
                return m.group(1)

        elif "windows" in system:
            out = subprocess.check_output(["route", "print", "-4"], text=True, stderr=subprocess.DEVNULL)
            # Row looks like:  0.0.0.0    0.0.0.0    <gateway>   <iface>  metric
            m = re.search(r"^\s*0\.0\.0\.0\s+0\.0\.0\.0\s+(\d+\.\d+\.\d+\.\d+)\s", out, re.MULTILINE)
            if m:
                return m.group(1)

    except Exception:
        pass

    raise RuntimeError("Could not determine default gateway IP on this OS.")


# ---------- result structs ----------

@dataclass
class HTTPProbe:
    status: Optional[int] = None
    headers: Optional[str] = None
    body_snippet: Optional[str] = None

@dataclass
class CheckResult:
    name: str
    port: int
    protocol: Literal["tcp", "http", "https"]
    tcp_connect: Optional[Literal["open", "closed", "timeout"]] = None
    http: Optional[HTTPProbe] = None
    error: Optional[str] = None
    duration_ms: int = 0


# ---------- low-level probes ----------

def tcp_connect(host: str, port: int, timeout_s: float = 1.0) -> Literal["open", "closed", "timeout"]:
    """
    Attempt a single TCP connect; no retries, short timeout.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout_s)
    try:
        rc = s.connect_ex((host, port))
        # 0=open; timeout raises socket.timeout; refused -> WSAECONNREFUSED/ECONNREFUSED etc.
        if rc == 0:
            return "open"
        return "closed"
    except socket.timeout:
        return "timeout"
    except Exception:
        return "closed"
    finally:
        try:
            s.close()
        except Exception:
            pass


def http_fetch(scheme: str, host: str, port: int, timeout_s: float = 1.5) -> HTTPProbe:
    """
    GET / and return status, headers (normalized), and a short body snippet.
    For local HTTPS we don't care about certs; mark verify=False.
    """
    url = f"{scheme}://{host}:{port}/"
    try:
        resp = requests.get(url, timeout=timeout_s, verify=(scheme != "https"))
        # Normalize headers into single string "key: value" with canonical casing
        headers_str = "\r\n".join(f"{k}: {v}" for k, v in resp.headers.items())
        # Prefer text; fallback to bytes decode with replacement
        try:
            body_snippet = resp.text[:512]
        except Exception:
            body_snippet = resp.content.decode("utf-8", errors="replace")[:512]

        return HTTPProbe(status=resp.status_code, headers=headers_str, body_snippet=body_snippet)

    except RequestException as e:
        return HTTPProbe(status=None, headers=None, body_snippet=f"(request error: {e})")


def resolve_target_ip():
    return os.getenv("TARGET_IP") or find_default_gateway()

# ---------- high-level scan ----------

def scan_once() -> dict:
    """
    Load checks.yaml, discover the router IP, run probes, and return a snapshot dict.
    """
    # 1) load config
    checks_cfg: ChecksConfig = load_and_validate("checks.yaml", ChecksConfig)

    # 2) find target
    target_ip = resolve_target_ip()

    started = time.perf_counter()
    results: list[CheckResult] = []

    for chk in checks_cfg.checks:
        assert isinstance(chk, PortCheck)
        t0 = time.perf_counter()
        item = CheckResult(name=chk.name, port=chk.port, protocol=chk.protocol.value)

        # Run per-protocol logic
        if chk.protocol == Protocol.tcp:
            item.tcp_connect = tcp_connect(target_ip, chk.port)

        elif chk.protocol in (Protocol.http, Protocol.https):
            # First: TCP connectivity (optional but helpful context)
            item.tcp_connect = tcp_connect(target_ip, chk.port)
            # Then: HTTP(S) GET
            try:
                item.http = http_fetch(chk.protocol.value, target_ip, chk.port)
            except Exception as e:
                item.error = f"http_fetch error: {e}"

        else:
            item.error = f"unknown protocol: {chk.protocol.value}"

        item.duration_ms = int((time.perf_counter() - t0) * 1000)
        results.append(item)

    total_ms = int((time.perf_counter() - started) * 1000)

    # 3) build snapshot
    snapshot = {
        "target": target_ip,
        "started_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "duration_ms": total_ms,
        "checks": [
            {
                **{k: v for k, v in asdict(r).items() if k not in {"http"}},
                "http": (asdict(r.http) if r.http else None),
            }
            for r in results
        ],
    }
    return snapshot

