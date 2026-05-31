"""Startup service health check and auto-start for hypertension dependencies.

Call ensure_services(hypertension_dir) from FastAPI lifespan.
Returns ServiceStatus; never raises — failures are logged as warnings.
"""
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx


@dataclass
class ServiceStatus:
    docker: bool = False
    qdrant: bool = False
    hypertensiondb: bool = False
    messages: list[str] = field(default_factory=list)


# ── Low-level checks ─────────────────────────────────────────────────────────

def _check_docker() -> bool:
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        return r.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _check_qdrant() -> bool:
    try:
        r = httpx.get("http://localhost:6333/", timeout=3.0)
        return r.status_code < 500
    except Exception:
        return False


def _check_hypertensiondb() -> bool:
    try:
        r = httpx.get("http://localhost:8000/health", timeout=3.0)
        return r.status_code < 500
    except Exception:
        return False


def _poll_until(check_fn, timeout_s: int = 30, interval_s: float = 1.0) -> bool:
    for _ in range(int(timeout_s / interval_s)):
        try:
            if check_fn():
                return True
        except Exception:
            pass
        time.sleep(interval_s)
    return False


# ── Starters ─────────────────────────────────────────────────────────────────

def _start_docker_desktop() -> bool:
    if sys.platform != "win32":
        return False
    candidates = [
        r"C:\Program Files\Docker\Docker\Docker Desktop.exe",
        r"C:\Program Files (x86)\Docker\Docker\Docker Desktop.exe",
    ]
    exe = next((p for p in candidates if Path(p).exists()), None)
    if exe is None:
        return False
    subprocess.Popen([exe])
    return _poll_until(_check_docker, timeout_s=60)


def _start_qdrant(hypertension_dir: Path) -> bool:
    try:
        subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd=hypertension_dir,
            capture_output=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    return _poll_until(_check_qdrant, timeout_s=30)


def _start_hypertensiondb(hypertension_dir: Path) -> bool:
    try:
        subprocess.Popen(
            ["hdb", "serve", "run"],
            cwd=hypertension_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return False
    return _poll_until(_check_hypertensiondb, timeout_s=30)


# ── Public entry point ────────────────────────────────────────────────────────

def ensure_services(hypertension_dir: Path) -> ServiceStatus:
    """Check and start Docker → Qdrant → Hypertensiondb in order.

    Never raises. Failures are recorded as WARNING messages in status.messages.
    """
    s = ServiceStatus()

    # 1. Docker
    if _check_docker():
        s.docker = True
        s.messages.append("Docker: already running")
    else:
        s.messages.append("Docker: not running, attempting to start...")
        if _start_docker_desktop():
            s.docker = True
            s.messages.append("Docker: started successfully")
        else:
            s.messages.append("WARNING: Docker failed to start — RAG unavailable")
            return s

    # 2. Qdrant
    if _check_qdrant():
        s.qdrant = True
        s.messages.append("Qdrant: already running")
    else:
        s.messages.append("Qdrant: starting via docker compose...")
        if _start_qdrant(hypertension_dir):
            s.qdrant = True
            s.messages.append("Qdrant: started")
        else:
            s.messages.append("WARNING: Qdrant failed to start — RAG unavailable")
            return s

    # 3. Hypertensiondb API
    if _check_hypertensiondb():
        s.hypertensiondb = True
        s.messages.append("Hypertensiondb API: already running")
    else:
        s.messages.append("Hypertensiondb API: starting hdb serve run...")
        if _start_hypertensiondb(hypertension_dir):
            s.hypertensiondb = True
            s.messages.append("Hypertensiondb API: started")
        else:
            s.messages.append("WARNING: Hypertensiondb API failed to start — RAG unavailable")

    return s
