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


def tcp_check(host: str, port: int, timeout: float = 0.45) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except (OSError, ValueError):
        return False


def scan_ports(host: str, ports: Iterable[int], timeout: float = 0.45, workers: int = 32) -> list[int]:
    clean = sorted({int(p) for p in ports if 1 <= int(p) <= 65535})
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(workers, len(clean) or 1))) as pool:
        results = pool.map(lambda p: (p, tcp_check(host, p, timeout)), clean)
    return [p for p, ok in results if ok]


def ping_host(host: str, timeout_ms: int = 700) -> bool:
    if platform.system() == "Windows":
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), host]
    else:
        cmd = ["ping", "-c", "1", "-W", str(max(1, timeout_ms // 1000)), host]
    try:
        completed = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   timeout=max(1.5, timeout_ms / 1000 + 0.8),
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return completed.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def reverse_dns(ip: str) -> str:
    try:
        return socket.gethostbyaddr(ip)[0]
    except OSError:
        return ""


def arp_table() -> dict[str, str]:
    if platform.system() != "Windows":
        return {}
    result: dict[str, str] = {}
    try:
        output = subprocess.check_output(["arp", "-a"], text=True, errors="replace", timeout=5,
                                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                try:
                    ipaddress.ip_address(parts[0])
                    if "-" in parts[1] or ":" in parts[1]:
                        result[parts[0]] = parts[1].replace("-", ":").upper()
                except ValueError:
                    continue
    except (OSError, subprocess.SubprocessError):
        pass
    return result


def discover_hosts(network: str, ports: Iterable[int],
                   timeout: float = 0.45, workers: int = 64,
                   on_result: Callable[[HostResult], None] | None = None,
                   stop_event=None) -> list[HostResult]:
    """Discover hosts in a local IPv4 subnet and optionally identify open TCP ports.

    Intended for networks the operator is authorized to assess. Results are streamed
    through on_result when supplied.
    """
    net = ipaddress.ip_network(network.strip(), strict=False)
    if net.version != 4:
        raise ValueError("Network discovery currently supports IPv4 subnets.")
    targets = list(net.hosts())
    arp = arp_table()
    results: list[HostResult] = []

    def one(addr: ipaddress.IPv4Address) -> HostResult:
        ip = str(addr)
        alive = ping_host(ip, int(timeout * 1000))
        # Some Windows hosts block ICMP, so an open TCP port also counts as discovered.
        open_ports = scan_ports(ip, ports, timeout=timeout) if (alive or ports) else []
        if open_ports:
            alive = True
        result = HostResult(ip=ip, hostname=reverse_dns(ip), alive=alive,
                            open_ports=open_ports, mac=arp.get(ip, ""))
        if on_result:
            on_result(result)
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(workers, 128))) as pool:
        futures = [pool.submit(one, addr) for addr in targets]
        for future in concurrent.futures.as_completed(futures):
            if stop_event is not None and stop_event.is_set():
                for f in futures:
                    f.cancel()
                break
            try:
                result = future.result()
            except Exception:
                continue
            if result.alive:
                results.append(result)
    return sorted(results, key=lambda x: ipaddress.ip_address(x.ip))
