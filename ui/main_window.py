from __future__ import annotations
import datetime
import ipaddress
import platform
import socket
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QComboBox
from core.network import calculate_network, get_default_gateway, get_dns_servers, get_interfaces, get_primary_interface
from core.ping import ping_once

class PingWorker(QThread):
    result = Signal(object)
    def __init__(self, target):
        super().__init__(); self.target = target
    def run(self): self.result.emit(ping_once(self.target))

class Card(QFrame):
    def __init__(self, title, value="-", subtitle=""):
        super().__init__(); self.setObjectName("Card")
        layout=QVBoxLayout(self); layout.setContentsMargins(16,14,16,14)
        t=QLabel(title.upper()); t.setObjectName("Muted")
        self.value_label=QLabel(value); self.value_label.setObjectName("Metric")
        s=QLabel(subtitle); s.setObjectName("Muted")
        layout.addWidget(t); layout.addWidget(self.value_label); layout.addWidget(s)

class MainWindow(QMainWindow):
    def __init__(self, theme):
        super().__init__(); self.theme=theme; self.worker=None; self.pages={}; self.nav_buttons=[]
        self.setWindowTitle("NetScope — Network Diagnostics"); self.resize(1180,760); self.setMinimumSize(900,620); self.build()

    def build(self):
        root=QWidget(); outer=QHBoxLayout(root); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        sidebar=QFrame(); sidebar.setObjectName("Sidebar"); sidebar.setMinimumWidth(220); side=QVBoxLayout(sidebar); side.setContentsMargins(16,20,16,16)
        brand=QLabel("NETSCOPE"); brand.setObjectName("Brand"); side.addWidget(brand)
        tag=QLabel("Network Diagnostics"); tag.setObjectName("Muted"); side.addWidget(tag); side.addSpacing(20)
        search=QLineEdit(); search.setPlaceholderText("Search tools…"); search.textChanged.connect(self.filter_nav); side.addWidget(search); side.addSpacing(10)
        for icon,text,key in [("⌂","Dashboard","dashboard"),("◈","Device Info","device"),("⌁","Local Network","network"),("◉","Ping","ping"),("▦","IP Calculator","ipcalc")]:
            b=QPushButton(f"{icon}   {text}"); b.setObjectName("NavButton"); b.setProperty("key",key); b.clicked.connect(lambda checked=False,k=key:self.show_page(k)); side.addWidget(b); self.nav_buttons.append(b)
        side.addStretch(); a=QLabel("APPEARANCE"); a.setObjectName("Muted"); side.addWidget(a)
        combo=QComboBox(); combo.addItems(["Dark","Light","System"]); combo.currentTextChanged.connect(lambda x:self.theme.apply(x.lower())); side.addWidget(combo)
        footer=QLabel("v0.1.0 • Phase 1"); footer.setObjectName("Muted"); side.addSpacing(10); side.addWidget(footer)
        self.stack=QStackedWidget(); self.add_pages(); outer.addWidget(sidebar); outer.addWidget(self.stack,1); self.setCentralWidget(root); self.show_page("dashboard")

    def header(self,title,subtitle):
        l=QVBoxLayout(); t=QLabel(title); t.setObjectName("PageTitle"); s=QLabel(subtitle); s.setObjectName("Muted"); l.addWidget(t); l.addWidget(s); l.addSpacing(12); return l

    def add_pages(self):
        self.pages={"dashboard":self.dashboard(),"device":self.device(),"network":self.network(),"ping":self.ping(),"ipcalc":self.ipcalc()}
        for p in self.pages.values(): self.stack.addWidget(p)

    def dashboard(self):
        p=QWidget(); l=QVBoxLayout(p); l.setContentsMargins(28,24,28,24); l.addLayout(self.header("Network Overview","A quick view of this Windows machine and its active network path."))
        primary=get_primary_interface(); ip=primary.ipv4 if primary else "Not available"; gw=get_default_gateway() or "Not detected"; dns=(get_dns_servers() or ["Not detected"])[0]
        grid=QGridLayout(); cards=[Card("Connection","ONLINE" if primary and primary.is_up else "OFFLINE",primary.name if primary else ""),Card("Local IP",ip,primary.netmask if primary else ""),Card("Gateway",gw,"Default route"),Card("DNS",dns,"Primary resolver")]
        for i,c in enumerate(cards): grid.addWidget(c,0,i)
        l.addLayout(grid); panel=QFrame(); panel.setObjectName("Card"); pl=QVBoxLayout(panel); pl.addWidget(QLabel("Network Interfaces")); table=self.interface_table(); pl.addWidget(table); l.addWidget(panel,1); return p

    def interface_table(self):
        t=QTableWidget(0,6); t.setHorizontalHeaderLabels(["Interface","IPv4","Netmask","MAC","Speed","Status"]); t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for x in get_interfaces():
            r=t.rowCount(); t.insertRow(r); vals=[x.name,x.ipv4 or "—",x.netmask or "—",x.mac or "—",f"{x.speed_mbps} Mbps" if x.speed_mbps else "—","UP" if x.is_up else "DOWN"]
            for c,v in enumerate(vals): t.setItem(r,c,QTableWidgetItem(v))
        return t

    def device(self):
        p=QWidget(); l=QVBoxLayout(p); l.setContentsMargins(28,24,28,24); l.addLayout(self.header("Device Info","System and network information collected locally.")); primary=get_primary_interface()
        rows=[("Hostname",socket.gethostname()),("FQDN",socket.getfqdn()),("Platform",platform.platform()),("Primary IPv4",primary.ipv4 if primary else "Not available"),("Default Gateway",get_default_gateway() or "Not detected"),("DNS Servers",", ".join(get_dns_servers()) or "Not detected")]
        t=QTableWidget(len(rows),2); t.setHorizontalHeaderLabels(["Property","Value"]); t.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeToContents); t.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)
        for r,(k,v) in enumerate(rows): t.setItem(r,0,QTableWidgetItem(k)); t.setItem(r,1,QTableWidgetItem(v))
        l.addWidget(t,1); return p

    def network(self):
        p=QWidget(); l=QVBoxLayout(p); l.setContentsMargins(28,24,28,24); l.addLayout(self.header("Local Network","Inspect local interfaces and the active subnet.")); primary=get_primary_interface(); subnet="Not available"
        if primary and primary.ipv4 and primary.netmask:
            try: subnet=str(ipaddress.ip_network(f"{primary.ipv4}/{primary.netmask}",strict=False))
            except ValueError: subnet="Unable to calculate"
        g=QGridLayout(); g.addWidget(Card("Active Interface",primary.name if primary else "—"),0,0); g.addWidget(Card("Subnet",subnet),0,1); g.addWidget(Card("Gateway",get_default_gateway() or "—"),0,2); l.addLayout(g); l.addWidget(self.interface_table(),1); return p

    def ping(self):
        p=QWidget(); l=QVBoxLayout(p); l.setContentsMargins(28,24,28,24); l.addLayout(self.header("Ping","Run a one-shot latency check without freezing the interface.")); row=QHBoxLayout(); target=QLineEdit(get_default_gateway()); target.setPlaceholderText("Hostname or IP"); btn=QPushButton("Ping"); row.addWidget(target,1); row.addWidget(btn); l.addLayout(row); card=Card("Result","READY","Enter a target and start a test."); l.addWidget(card); table=QTableWidget(0,3); table.setHorizontalHeaderLabels(["Time","Status","Latency"]); table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); l.addWidget(table,1)
        def start():
            if not target.text().strip(): QMessageBox.warning(self,"Target required","Enter a hostname or IP address."); return
            btn.setEnabled(False); card.value_label.setText("TESTING…"); self.worker=PingWorker(target.text().strip()); self.worker.result.connect(lambda result:self.finish_ping(result,card,table,btn)); self.worker.start()
        btn.clicked.connect(start); return p

    def finish_ping(self,result,card,table,btn):
        card.value_label.setText("SUCCESS" if result.success else "FAILED"); r=table.rowCount(); table.insertRow(r); vals=[datetime.datetime.now().strftime("%H:%M:%S"),"Reachable" if result.success else "Unreachable",f"{result.latency_ms:.1f} ms" if result.latency_ms is not None else "—"]
        for c,v in enumerate(vals): table.setItem(r,c,QTableWidgetItem(v))
        btn.setEnabled(True); self.worker=None

    def ipcalc(self):
        p=QWidget(); l=QVBoxLayout(p); l.setContentsMargins(28,24,28,24); l.addLayout(self.header("IP Calculator","Calculate IPv4/IPv6 network details locally.")); row=QHBoxLayout(); inp=QLineEdit("192.168.1.10/24"); inp.setPlaceholderText("CIDR, e.g. 10.0.0.0/24"); btn=QPushButton("Calculate"); row.addWidget(inp,1); row.addWidget(btn); l.addLayout(row); t=QTableWidget(0,2); t.setHorizontalHeaderLabels(["Property","Value"]); t.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeToContents); t.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch); l.addWidget(t,1)
        def calc():
            try: vals=calculate_network(inp.text())
            except ValueError as e: QMessageBox.warning(self,"Invalid network",f"Enter a valid CIDR.\n\n{e}"); return
            t.setRowCount(0)
            for k,v in vals.items(): r=t.rowCount(); t.insertRow(r); t.setItem(r,0,QTableWidgetItem(k)); t.setItem(r,1,QTableWidgetItem(v))
        btn.clicked.connect(calc); calc(); return p

    def show_page(self,key):
        self.stack.setCurrentWidget(self.pages[key])
        for b in self.nav_buttons:
            b.setProperty("active",b.property("key")==key); b.style().unpolish(b); b.style().polish(b)

    def filter_nav(self,text):
        q=text.strip().lower()
        for b in self.nav_buttons: b.setVisible(not q or q in b.text().lower())
