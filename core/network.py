from __future__ import annotations
import ipaddress
import platform
import socket
import subprocess
from dataclasses import dataclass
import psutil

@dataclass
class InterfaceInfo:
    name: str
    ipv4: str = ""
    netmask: str = ""
    broadcast: str = ""
    mac: str = ""
    is_up: bool = False
    speed_mbps: int = 0

def get_interfaces() -> list[InterfaceInfo]:
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    result = []
    link_family = getattr(psutil, "AF_LINK", None)
    for name, addr_list in addrs.items():
        info = InterfaceInfo(name=name)
        stat = stats.get(name)
        info.is_up = bool(stat and stat.isup)
        info.speed_mbps = int(stat.speed or 0) if stat else 0
        for addr in addr_list:
            if addr.family == socket.AF_INET:
                info.ipv4 = addr.address or ""
                info.netmask = addr.netmask or ""
                info.broadcast = addr.broadcast or ""
            elif link_family is not None and addr.family == link_family:
                info.mac = addr.address or ""
        result.append(info)
    return result

def get_primary_interface() -> InterfaceInfo | None:
    interfaces = get_interfaces()
    return next((x for x in interfaces if x.is_up and x.ipv4 and not x.ipv4.startswith("127.")), None)

def get_default_gateway() -> str:
    if platform.system() != "Windows":
        return ""
    try:
        output = subprocess.check_output(["route", "print", "0.0.0.0"], text=True, errors="replace", timeout=3, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 4 and parts[0] == "0.0.0.0" and parts[1] != "0.0.0.0":
                return parts[2]
    except (OSError, subprocess.SubprocessError):
        pass
    return ""

def get_dns_servers() -> list[str]:
    if platform.system() != "Windows":
        return []
    servers = []
    try:
        output = subprocess.check_output(["ipconfig", "/all"], text=True, errors="replace", timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        capture = False
        for raw in output.splitlines():
            line = raw.strip()
            if "DNS Servers" in line:
                capture = True
                value = line.split(":", 1)[-1].strip()
                if value and value not in servers:
                    servers.append(value)
            elif capture and line and line[0].isdigit():
                value = line.split()[0]
                if value not in servers:
                    servers.append(value)
            elif capture:
                capture = False
    except (OSError, subprocess.SubprocessError):
        pass
    return servers

def calculate_network(cidr: str) -> dict[str, str]:
    network = ipaddress.ip_network(cidr.strip(), strict=False)
    result = {"Version": f"IPv{network.version}", "Network": str(network.network_address), "Prefix": f"/{network.prefixlen}", "Netmask": str(network.netmask), "Broadcast": str(network.broadcast_address) if network.version == 4 else "N/A", "Total addresses": str(network.num_addresses)}
    if network.version == 4 and network.num_addresses > 2:
        result.update({"First host": str(network.network_address + 1), "Last host": str(network.broadcast_address - 1), "Usable hosts": str(network.num_addresses - 2)})
    else:
        result.update({"First host": str(network.network_address), "Last host": str(network.broadcast_address), "Usable hosts": "N/A"})
    return result
