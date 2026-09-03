# NetScope

**Professional Network Diagnostics for Windows**

NetScope is a modern Python/PySide6 network diagnostics toolkit for Windows.

## Phase 1

- Interactive dashboard
- Device information
- Local network interface/subnet information
- Non-blocking Ping
- IPv4/IPv6 calculator
- Tool search
- Dark / Light / System appearance
- PyInstaller Windows EXE build
- GitHub Actions CI/CD

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

## Build Windows EXE

```powershell
pip install pyinstaller
pyinstaller --noconfirm --clean --windowed --name NetScope app.py
```

The executable will be created under `dist\NetScope\NetScope.exe`.

## Roadmap

Phase 2: Port Scanner, Multi-IP Scanner, DNS Lookup, Traceroute, ARP/neighbor table and routing table.

Phase 3: Wi-Fi Analyzer, certificate viewer, mDNS/UPnP discovery, speed test and richer visualizations.

Use network discovery/scanning features only on systems and networks you are authorized to test.
