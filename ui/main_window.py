from __future__ import annotations

import datetime
import ipaddress
import platform
import socket

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QStackedWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget
)

from core.network import (
    calculate_network, get_default_gateway, get_dns_servers,
    get_interfaces, get_primary_interface,
)
from core.ping import ping_once


TOOLS = [
    ("Network", "◈", "Device Info", "device", "System and adapter information"),
    ("Network", "⌁", "Local Network", "network", "Interfaces, gateway and subnet"),
    ("Scanning", "◉", "Port Scanner", "portscan", "TCP port discovery"),
    ("Scanning", "◎", "Multi-IP Port Scanner", "multiport", "Scan several hosts at once"),
    ("Wireless", "⌁", "WiFi Analyzer", "wifi", "SSID, channel and signal overview"),
    ("Diagnostics", "⇢", "Traceroute", "traceroute", "Trace the route to a host"),
    ("Diagnostics", "◉", "Ping", "ping", "Latency and reachability test"),
    ("Diagnostics", "⌁", "Ping Graph", "pinggraph", "Continuous latency visualization"),
    ("DNS & Domain", "◌", "DNS Lookup", "dns", "A, AAAA, MX, NS, TXT and more"),
    ("DNS & Domain", "↩", "Reverse IP Lookup", "reverse", "Resolve an IP to hostnames"),
    ("DNS & Domain", "⌕", "WHOIS Lookup", "whois", "Domain and IP registration data"),
    ("Remote", "✦", "Wake-On-LAN", "wol", "Send a magic packet"),
    ("Utilities", "▣", "IP Calculator", "ipcalc", "IPv4 and IPv6 subnet calculator"),
    ("Security", "▤", "Certificate Viewer", "cert", "Inspect TLS certificates"),
    ("Diagnostics", "◒", "Speed Test", "speed", "Download, upload and latency"),
    ("Discovery", "◎", "mDNS Browser", "mdns", "Bonjour / Zeroconf services"),
    ("Discovery", "⌗", "UPnP Browser", "upnp", "Discover UPnP devices"),
    ("Discovery", "⌘", "Network Map", "map", "Visualize discovered hosts"),
    ("Security", "✓", "HTTP Header Checker", "headers", "Inspect web response headers"),
    ("Security", "◇", "TLS Security Check", "tls", "Review TLS configuration"),
    ("Monitoring", "▥", "Connection Monitor", "connections", "Active local connections"),
    ("Monitoring", "▤", "Bandwidth Monitor", "bandwidth", "Interface traffic overview"),
]


class PingWorker(QThread):
    result = Signal(object)

    def __init__(self, target):
        super().__init__()
        self.target = target

    def run(self):
        self.result.emit(ping_once(self.target))


class Card(QFrame):
    def __init__(self, title, value="-", subtitle=""):
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        title_label = QLabel(title.upper())
        title_label.setObjectName("Muted")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("Metric")
        sub = QLabel(subtitle)
        sub.setObjectName("Muted")
        layout.addWidget(title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(sub)


class ToolPage(QWidget):
    def __init__(self, title, description, icon="◈", body=None):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 26, 30, 26)
        hero = QFrame()
        hero.setObjectName("ToolHero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(20, 18, 20, 18)
        badge = QLabel(icon)
        badge.setObjectName("HeroIcon")
        text = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")
        desc = QLabel(description)
        desc.setObjectName("Muted")
        text.addWidget(title_label)
        text.addWidget(desc)
        hero_layout.addWidget(badge)
        hero_layout.addLayout(text, 1)
        layout.addWidget(hero)
        layout.addSpacing(14)
        if body:
            layout.addWidget(body, 1)
        else:
            card = QFrame()
            card.setObjectName("Card")
            card_layout = QVBoxLayout(card)
            status = QLabel("READY")
            status.setObjectName("StatusPill")
            card_layout.addWidget(status, 0, Qt.AlignLeft)
            note = QLabel("This tool is included in the NetScope toolkit. The UI is ready for the scanner/collector engine.")
            note.setObjectName("Muted")
            note.setWordWrap(True)
            card_layout.addWidget(note)
            card_layout.addStretch()
            layout.addWidget(card, 1)


class MainWindow(QMainWindow):
    def __init__(self, theme):
        super().__init__()
        self.theme = theme
        self.worker = None
        self.pages = {}
        self.nav_buttons = []
        self.setWindowTitle("NetScope — Network & Security Toolkit")
        self.resize(1320, 820)
        self.setMinimumSize(1050, 680)
        self.build()

    def build(self):
        root = QWidget()
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(270)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 20, 18, 18)
        side.setSpacing(6)

        brand_row = QHBoxLayout()
        brand = QLabel("NETSCOPE")
        brand.setObjectName("Brand")
        version = QLabel("PRO")
        version.setObjectName("BrandBadge")
        brand_row.addWidget(brand)
        brand_row.addWidget(version)
        brand_row.addStretch()
        side.addLayout(brand_row)
        tag = QLabel("NETWORK & SECURITY TOOLKIT")
        tag.setObjectName("Muted")
        side.addWidget(tag)
        side.addSpacing(14)

        search = QLineEdit()
        search.setObjectName("ToolSearch")
        search.setPlaceholderText("⌕  Search tools…")
        search.textChanged.connect(self.filter_nav)
        side.addWidget(search)
        side.addSpacing(8)

        self.dashboard_button = QPushButton("⌂   Dashboard")
        self.dashboard_button.setObjectName("NavButton")
        self.dashboard_button.setProperty("key", "dashboard")
        self.dashboard_button.clicked.connect(lambda: self.show_page("dashboard"))
        side.addWidget(self.dashboard_button)
        self.nav_buttons.append(self.dashboard_button)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("NavScroll")
        nav_content = QWidget()
        nav_layout = QVBoxLayout(nav_content)
        nav_layout.setContentsMargins(0, 8, 4, 8)
        nav_layout.setSpacing(2)

        current_group = None
        for group, icon, text, key, _ in TOOLS:
            if group != current_group:
                current_group = group
                header = QLabel(group.upper())
                header.setObjectName("NavGroup")
                nav_layout.addWidget(header)
            button = QPushButton(f"{icon}   {text}")
            button.setObjectName("NavButton")
            button.setProperty("key", key)
            button.setProperty("tool_name", text.lower())
            button.clicked.connect(lambda checked=False, k=key: self.show_page(k))
            nav_layout.addWidget(button)
            self.nav_buttons.append(button)
        nav_layout.addStretch()
        scroll.setWidget(nav_content)
        side.addWidget(scroll, 1)

        bottom = QFrame()
        bottom.setObjectName("SidebarBottom")
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 10, 0, 0)
        appearance = QLabel("APPEARANCE")
        appearance.setObjectName("Muted")
        combo = QComboBox()
        combo.addItems(["Dark", "Light", "System"])
        combo.currentTextChanged.connect(lambda x: self.theme.apply(x.lower()))
        bottom_layout.addWidget(appearance)
        bottom_layout.addWidget(combo)
        footer = QLabel("v0.2.0  •  Windows")
        footer.setObjectName("Muted")
        bottom_layout.addWidget(footer)
        side.addWidget(bottom)

        self.stack = QStackedWidget()
        self.add_pages()
        for page in self.pages.values():
            self.stack.addWidget(page)

        outer.addWidget(sidebar)
        outer.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.show_page("dashboard")

    def add_pages(self):
        self.pages["dashboard"] = self.dashboard()
        self.pages["device"] = self.device()
        self.pages["network"] = self.network()
        self.pages["ping"] = self.ping()
        self.pages["ipcalc"] = self.ipcalc()
        for group, icon, title, key, desc in TOOLS:
            if key not in self.pages:
                self.pages[key] = ToolPage(title, desc, icon)

    def dashboard(self):
        p = QWidget()
        l = QVBoxLayout(p)
        l.setContentsMargins(30, 26, 30, 26)
        heading = QHBoxLayout()
        text = QVBoxLayout()
        title = QLabel("Network Overview")
        title.setObjectName("PageTitle")
        sub = QLabel("Your complete network diagnostics workspace.")
        sub.setObjectName("Muted")
        text.addWidget(title)
        text.addWidget(sub)
        heading.addLayout(text)
        heading.addStretch()
        scan = QPushButton("⟳  Refresh")
        scan.setObjectName("PrimaryButton")
        scan.clicked.connect(self.refresh_dashboard)
        heading.addWidget(scan, 0, Qt.AlignBottom)
        l.addLayout(heading)
        l.addSpacing(18)

        primary = get_primary_interface()
        ip = primary.ipv4 if primary else "Not available"
        gw = get_default_gateway() or "Not detected"
        dns = (get_dns_servers() or ["Not detected"])[0]
        cards = [
            Card("Connection", "ONLINE" if primary and primary.is_up else "OFFLINE", primary.name if primary else "No active adapter"),
            Card("Local IP", ip, primary.netmask if primary else ""),
            Card("Gateway", gw, "Default route"),
            Card("DNS", dns, "Primary resolver"),
        ]
        grid = QGridLayout()
        grid.setSpacing(12)
        for i, card in enumerate(cards):
            grid.addWidget(card, 0, i)
        l.addLayout(grid)
        l.addSpacing(14)

        row = QHBoxLayout()
        left = QFrame()
        left.setObjectName("Card")
        ll = QVBoxLayout(left)
        ll.addWidget(QLabel("Network Interfaces"))
        ll.addWidget(self.interface_table())
        row.addWidget(left, 2)

        right = QFrame()
        right.setObjectName("Card")
        rl = QVBoxLayout(right)
        rl.addWidget(QLabel("Toolkit"))
        rl.addWidget(QLabel("22 tools available across 9 categories."))
        for label, value in [("Scanning", "4 tools"), ("DNS & Domain", "3 tools"), ("Diagnostics", "4 tools"), ("Security", "3 tools")]:
            c = QHBoxLayout()
            a = QLabel(label)
            b = QLabel(value)
            b.setObjectName("AccentText")
            c.addWidget(a)
            c.addStretch()
            c.addWidget(b)
            rl.addLayout(c)
        rl.addStretch()
        row.addWidget(right, 1)
        l.addLayout(row, 1)
        return p

    def refresh_dashboard(self):
        old = self.stack.currentIndex()
        self.pages["dashboard"] = self.dashboard()
        self.stack.insertWidget(0, self.pages["dashboard"])
        self.stack.removeWidget(self.stack.widget(1))
        self.stack.setCurrentIndex(old if old == 0 else old)

    def interface_table(self):
        t = QTableWidget(0, 6)
        t.setHorizontalHeaderLabels(["Interface", "IPv4", "Netmask", "MAC", "Speed", "Status"])
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for x in get_interfaces():
            r = t.rowCount()
            t.insertRow(r)
            vals = [x.name, x.ipv4 or "—", x.netmask or "—", x.mac or "—", f"{x.speed_mbps} Mbps" if x.speed_mbps else "—", "UP" if x.is_up else "DOWN"]
            for c, v in enumerate(vals):
                t.setItem(r, c, QTableWidgetItem(v))
        return t

    def device(self):
        rows = [
            ("Hostname", socket.gethostname()),
            ("FQDN", socket.getfqdn()),
            ("Platform", platform.platform()),
            ("Primary IPv4", (get_primary_interface().ipv4 if get_primary_interface() else "Not available")),
            ("Default Gateway", get_default_gateway() or "Not detected"),
            ("DNS Servers", ", ".join(get_dns_servers()) or "Not detected"),
        ]
        table = QTableWidget(len(rows), 2)
        table.setHorizontalHeaderLabels(["Property", "Value"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for r, (k, v) in enumerate(rows):
            table.setItem(r, 0, QTableWidgetItem(k))
            table.setItem(r, 1, QTableWidgetItem(v))
        return ToolPage("Device Info", "System and network information collected locally.", "◈", table)

    def network(self):
        primary = get_primary_interface()
        subnet = "Not available"
        if primary and primary.ipv4 and primary.netmask:
            try:
                subnet = str(ipaddress.ip_network(f"{primary.ipv4}/{primary.netmask}", strict=False))
            except ValueError:
                subnet = "Unable to calculate"
        body = QWidget()
        l = QVBoxLayout(body)
        g = QGridLayout()
        g.addWidget(Card("Active Interface", primary.name if primary else "—"), 0, 0)
        g.addWidget(Card("Subnet", subnet), 0, 1)
        g.addWidget(Card("Gateway", get_default_gateway() or "—"), 0, 2)
        l.addLayout(g)
        l.addWidget(self.interface_table(), 1)
        return ToolPage("Local Network", "Inspect local interfaces and the active subnet.", "⌁", body)

    def ping(self):
        body = QWidget()
        l = QVBoxLayout(body)
        row = QHBoxLayout()
        target = QLineEdit(get_default_gateway())
        target.setPlaceholderText("Hostname or IP")
        btn = QPushButton("Ping")
        btn.setObjectName("PrimaryButton")
        row.addWidget(target, 1)
        row.addWidget(btn)
        l.addLayout(row)
        card = Card("Result", "READY", "Enter a target and start a test.")
        l.addWidget(card)
        table = QTableWidget(0, 3)
        table.setHorizontalHeaderLabels(["Time", "Status", "Latency"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        l.addWidget(table, 1)

        def start():
            if not target.text().strip():
                QMessageBox.warning(self, "Target required", "Enter a hostname or IP address.")
                return
            btn.setEnabled(False)
            card.value_label.setText("TESTING…")
            self.worker = PingWorker(target.text().strip())
            self.worker.result.connect(lambda result: self.finish_ping(result, card, table, btn))
            self.worker.start()

        btn.clicked.connect(start)
        return ToolPage("Ping", "Run a latency and reachability check without freezing the interface.", "◉", body)

    def finish_ping(self, result, card, table, btn):
        card.value_label.setText("SUCCESS" if result.success else "FAILED")
        r = table.rowCount()
        table.insertRow(r)
        vals = [datetime.datetime.now().strftime("%H:%M:%S"), "Reachable" if result.success else "Unreachable", f"{result.latency_ms:.1f} ms" if result.latency_ms is not None else "—"]
        for c, v in enumerate(vals):
            table.setItem(r, c, QTableWidgetItem(v))
        btn.setEnabled(True)
        self.worker = None

    def ipcalc(self):
        body = QWidget()
        l = QVBoxLayout(body)
        row = QHBoxLayout()
        inp = QLineEdit("192.168.1.10/24")
        inp.setPlaceholderText("CIDR, e.g. 10.0.0.0/24")
        btn = QPushButton("Calculate")
        btn.setObjectName("PrimaryButton")
        row.addWidget(inp, 1)
        row.addWidget(btn)
        l.addLayout(row)
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["Property", "Value"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        l.addWidget(table, 1)

        def calc():
            try:
                vals = calculate_network(inp.text())
            except ValueError as e:
                QMessageBox.warning(self, "Invalid network", f"Enter a valid CIDR.\n\n{e}")
                return
            table.setRowCount(0)
            for k, v in vals.items():
                r = table.rowCount()
                table.insertRow(r)
                table.setItem(r, 0, QTableWidgetItem(k))
                table.setItem(r, 1, QTableWidgetItem(v))

        btn.clicked.connect(calc)
        calc()
        return ToolPage("IP Calculator", "Calculate IPv4 and IPv6 network details locally.", "▣", body)

    def show_page(self, key):
        if key not in self.pages:
            return
        self.stack.setCurrentWidget(self.pages[key])
        for b in self.nav_buttons:
            active = b.property("key") == key
            b.setProperty("active", active)
            b.style().unpolish(b)
            b.style().polish(b)

    def filter_nav(self, text):
        q = text.strip().lower()
        for b in self.nav_buttons:
            if b is self.dashboard_button:
                b.setVisible(not q or "dashboard" in q)
                continue
            name = str(b.property("tool_name") or b.text()).lower()
            b.setVisible(not q or q in name)
