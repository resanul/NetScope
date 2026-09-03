from __future__ import annotations
import concurrent.futures
import ipaddress
import platform
import socket
import subprocess
from dataclasses import dataclass
from typing import Callable, Iterable

COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 3389, 5900, 8080]

@dataclass
class HostResult:
    ip: str
    hostname: str = ""
    alive: bool = False
    open_ports: list[int] | None = None
    mac: str = ""

def tcp_check(host: str, port: int, timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout): return True
    except (OSError, ValueError): return False

def scan_ports(host: str, ports: Iterable[int], timeout: float = 0.35, workers: int = 64) -> list[int]:
    clean = sorted({int(p) for p in ports if 1 <= int(p) <= 65535})
    if not clean: return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(workers, len(clean))) as pool:
        checks = pool.map(lambda p: (p, tcp_check(host, p, timeout)), clean)
    return [p for p, ok in checks if ok]

def ping_host(host: str, timeout_ms: int = 500) -> bool:
    if platform.system() == "Windows": cmd = ["ping", "-n", "1", "-w", str(timeout_ms), host]
    else: cmd = ["ping", "-c", "1", "-W", str(max(1, timeout_ms // 1000)), host]
    try:
        return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1.5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).returncode == 0
    except (OSError, subprocess.SubprocessError): return False

def reverse_dns(ip: str) -> str:
    try: return socket.gethostbyaddr(ip)[0]
    except OSError: return ""

def arp_table() -> dict[str, str]:
    if platform.system() != "Windows": return {}
    result = {}
    try:
        output = subprocess.check_output(["arp", "-a"], text=True, errors="replace", timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                try:
                    ipaddress.ip_address(parts[0])
                    if "-" in parts[1] or ":" in parts[1]: result[parts[0]] = parts[1].replace("-", ":").upper()
                except ValueError: pass
    except (OSError, subprocess.SubprocessError): pass
    return result

def discover_hosts(network: str, ports: Iterable[int], timeout: float = 0.35, workers: int = 64,
                   on_result: Callable[[HostResult], None] | None = None, stop_event=None) -> list[HostResult]:
    net = ipaddress.ip_network(network.strip(), strict=False)
    if net.version != 4: raise ValueError("Network discovery currently supports IPv4.")
    if net.num_addresses > 4096: raise ValueError("Discovery is limited to 4096 addresses per run. Use a smaller subnet.")
    targets = list(net.hosts()); arp = arp_table(); results = []

    def one(addr):
        ip = str(addr); mac = arp.get(ip, ""); alive = ping_host(ip, int(timeout * 1000))
        opened = scan_ports(ip, ports, timeout=timeout) if (alive or mac) else []
        if opened: alive = True
        return HostResult(ip, reverse_dns(ip), alive, opened, mac)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(workers, 128))) as pool:
        futures = [pool.submit(one, a) for a in targets]
        for future in concurrent.futures.as_completed(futures):
            if stop_event is not None and stop_event.is_set():
                for f in futures: f.cancel()
                break
            try: result = future.result()
            except Exception: continue
            if result.alive:
                results.append(result)
                if on_result: on_result(result)
    return sorted(results, key=lambda x: ipaddress.ip_address(x.ip))
