from __future__ import annotations
import platform
import re
import subprocess
import time
from dataclasses import dataclass

@dataclass
class PingResult:
    success: bool
    latency_ms: float | None
    raw: str

def ping_once(target: str, timeout_ms: int = 1200) -> PingResult:
    target = target.strip()
    if not target:
        return PingResult(False, None, "Target is empty.")
    if platform.system() == "Windows":
        command = ["ping", "-n", "1", "-w", str(max(100, timeout_ms)), target]
    else:
        command = ["ping", "-c", "1", "-W", str(max(1, timeout_ms // 1000)), target]
    start = time.perf_counter()
    try:
        completed = subprocess.run(command, capture_output=True, text=True, errors="replace", timeout=max(2.0, timeout_ms / 1000 + 1), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        elapsed = (time.perf_counter() - start) * 1000
        raw = (completed.stdout or completed.stderr or "").strip()
        match = re.search(r"(?:time[=<]\s*)(\d+(?:[.,]\d+)?)\s*ms", raw, re.I)
        latency = float(match.group(1).replace(",", ".")) if match else (round(elapsed, 1) if completed.returncode == 0 else None)
        return PingResult(completed.returncode == 0, latency, raw)
    except subprocess.TimeoutExpired:
        return PingResult(False, None, "Request timed out.")
    except OSError as exc:
        return PingResult(False, None, str(exc))
