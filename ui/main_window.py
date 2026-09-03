from __future__ import annotations

import datetime, ipaddress, json, platform, re, socket, ssl, subprocess, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (QComboBox, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QScrollArea, QStackedWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QPlainTextEdit, QProgressBar, QSpinBox)
from core.network import calculate_network, get_default_gateway, get_dns_servers, get_interfaces, get_primary_interface
from core.ping import ping_once
from core.scanner import COMMON_PORTS, HostResult, discover_hosts, scan_ports

TOOLS = [
    ("Network", "◈", "Device Info", "device", "System and adapter information"),
    ("Network", "⌁", "Local Network", "network", "Interfaces, gateway and subnet"),
    ("Discovery", "◎", "Network Discovery", "discovery", "Auto-discover hosts and open ports"),
    ("Scanning", "◉", "Port Scanner", "port", "TCP port discovery"),
    ("Scanning", "◎", "Multi-IP Port Scanner", "multi", "Scan several hosts at once"),
    ("Wireless", "⌁", "WiFi Analyzer", "wifi", "SSID, channel and signal overview"),
    ("Diagnostics", "⇢", "Traceroute", "trace", "Trace the route to a host"),
    ("Diagnostics", "◉", "Ping", "ping", "Latency and reachability test"),
    ("Diagnostics", "⌁", "Ping Graph", "pinggraph", "Repeated latency measurements"),
    ("DNS & Domain", "◌", "DNS Lookup", "dns", "A, AAAA, MX, NS and TXT"),
    ("DNS & Domain", "↩", "Reverse IP Lookup", "reverse", "Resolve an IP to hostname"),
    ("DNS & Domain", "⌕", "WHOIS Lookup", "whois", "Registration information"),
    ("Remote", "✦", "Wake-On-LAN", "wol", "Send a magic packet"),
    ("Utilities", "▣", "IP Calculator", "ipcalc", "IPv4 and IPv6 subnet calculator"),
    ("Security", "◇", "Certificate Viewer", "cert", "Inspect TLS certificates"),
    ("Diagnostics", "◒", "Speed Test", "speed", "HTTP download measurement"),
    ("Discovery", "◎", "mDNS Browser", "mdns", "Bonjour / Zeroconf discovery"),
    ("Discovery", "⌗", "UPnP Browser", "upnp", "SSDP device discovery"),
    ("Discovery", "⌘", "Network Map", "map", "Host map from latest discovery"),
    ("Security", "✓", "HTTP Header Checker", "headers", "Inspect HTTP response headers"),
    ("Security", "◇", "TLS Security Check", "tls", "Inspect TLS protocol/certificate"),
    ("Monitoring", "▥", "Connection Monitor", "connections", "Active TCP connections"),
]

class Worker(QThread):
    result = Signal(object); error = Signal(str)
    def __init__(self, fn): super().__init__(); self.fn = fn
    def run(self):
        try: self.result.emit(self.fn())
        except Exception as e: self.error.emit(str(e))

class DiscoveryWorker(QThread):
    host = Signal(object); done = Signal(); error = Signal(str)
    def __init__(self, network, ports): super().__init__(); self.network=network; self.ports=ports; self.stop_requested=False
    def stop(self): self.stop_requested=True
    def run(self):
        class Stop:
            def __init__(self, owner): self.owner=owner
            def is_set(self): return self.owner.stop_requested
        try: discover_hosts(self.network,self.ports,on_result=self.host.emit,stop_event=Stop(self)); self.done.emit()
        except Exception as e: self.error.emit(str(e))

class Card(QFrame):
    def __init__(self,title,value="-",subtitle=""):
        super().__init__(); self.setObjectName("Card"); l=QVBoxLayout(self); l.setContentsMargins(16,14,16,14)
        a=QLabel(title.upper()); a.setObjectName("Muted"); self.value_label=QLabel(value); self.value_label.setObjectName("Metric"); s=QLabel(subtitle); s.setObjectName("Muted")
        l.addWidget(a); l.addWidget(self.value_label); l.addWidget(s)

class ToolPage(QWidget):
    def __init__(self,title,desc,icon="◈",body=None):
        super().__init__(); l=QVBoxLayout(self); l.setContentsMargins(30,26,30,26); l.setSpacing(14)
        hero=QFrame(); hero.setObjectName("ToolHero"); hl=QHBoxLayout(hero); hl.setContentsMargins(18,16,18,16)
        i=QLabel(icon); i.setObjectName("HeroIcon"); box=QVBoxLayout(); t=QLabel(title); t.setObjectName("PageTitle"); d=QLabel(desc); d.setObjectName("Muted"); box.addWidget(t); box.addWidget(d); hl.addWidget(i); hl.addLayout(box,1); l.addWidget(hero)
        if body: l.addWidget(body,1)

class MainWindow(QMainWindow):
    def __init__(self,theme):
        super().__init__(); self.theme=theme; self.worker=None; self.discovery_worker=None; self.pages={}; self.nav_buttons=[]; self.last_discovery=[]
        self.setWindowTitle("NetScope — Network & Security Toolkit"); self.resize(1320,820); self.setMinimumSize(1050,680); self.build()

    def build(self):
        root=QWidget(); outer=QHBoxLayout(root); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        side=QFrame(); side.setObjectName("Sidebar"); side.setFixedWidth(270); sl=QVBoxLayout(side); sl.setContentsMargins(18,18,18,14)
        br=QHBoxLayout(); b=QLabel("NETSCOPE"); b.setObjectName("Brand"); v=QLabel("PRO"); v.setObjectName("BrandBadge"); br.addWidget(b); br.addWidget(v); br.addStretch(); sl.addLayout(br)
        q=QLabel("NETWORK & SECURITY TOOLKIT"); q.setObjectName("Muted"); sl.addWidget(q); sl.addSpacing(12)
        search=QLineEdit(); search.setPlaceholderText("⌕  Search tools…"); search.textChanged.connect(self.filter_nav); sl.addWidget(search)
        dash=QPushButton("⌂   Dashboard"); dash.setObjectName("NavButton"); dash.setProperty("key","dashboard"); dash.clicked.connect(lambda:self.show_page("dashboard")); sl.addWidget(dash); self.nav_buttons.append(dash)
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setObjectName("NavScroll"); c=QWidget(); nl=QVBoxLayout(c); nl.setContentsMargins(0,8,4,8); nl.setSpacing(2); group=None
        for g,icon,text,key,desc in TOOLS:
            if g!=group: group=g; h=QLabel(g.upper()); h.setObjectName("NavGroup"); nl.addWidget(h)
            x=QPushButton(f"{icon}   {text}"); x.setObjectName("NavButton"); x.setProperty("key",key); x.setProperty("tool_name",text.lower()); x.clicked.connect(lambda checked=False,k=key:self.show_page(k)); nl.addWidget(x); self.nav_buttons.append(x)
        nl.addStretch(); scroll.setWidget(c); sl.addWidget(scroll,1)
        ap=QLabel("APPEARANCE"); ap.setObjectName("Muted"); sl.addWidget(ap); combo=QComboBox(); combo.addItems(["Dark","Light","System"]); combo.currentTextChanged.connect(lambda x:self.theme.apply(x.lower())); sl.addWidget(combo); f=QLabel("v0.3.0 • Local-first"); f.setObjectName("Muted"); sl.addWidget(f)
        self.stack=QStackedWidget(); self.add_pages(); [self.stack.addWidget(x) for x in self.pages.values()]; outer.addWidget(side); outer.addWidget(self.stack,1); self.setCentralWidget(root); self.show_page("dashboard")

    def shell(self,title,desc,icon,body): return ToolPage(title,desc,icon,body)

    def add_pages(self):
        self.pages={"dashboard":self.dashboard(),"device":self.device(),"network":self.network(),"discovery":self.discovery(),"port":self.port_scanner(),"multi":self.multi_scanner(),"ping":self.ping(False),"pinggraph":self.ping(True),"dns":self.dns(),"reverse":self.reverse(),"whois":self.command_page("WHOIS Lookup","Run the installed WHOIS client.","⌕","whois","Domain or IP"),"trace":self.command_page("Traceroute","Trace each network hop to a destination.","⇢","tracert","Hostname or IP"),"wifi":self.command_page("WiFi Analyzer","Read nearby SSIDs, BSSID, channels and signal with Windows netsh.","⌁","netsh wlan show networks mode=bssid","Press Run to scan nearby Wi-Fi"),"wol":self.wol(),"ipcalc":self.ipcalc(),"cert":self.cert(),"speed":self.speed(),"mdns":self.mdns(),"upnp":self.upnp(),"map":self.network_map(),"headers":self.headers(),"tls":self.cert(),"connections":self.connections()}
        for g,i,t,k,d in TOOLS:
            if k not in self.pages: self.pages[k]=self.shell(t,d,i,QPlainTextEdit())

    def dashboard(self):
        body=QWidget(); l=QVBoxLayout(body); head=QHBoxLayout(); t=QVBoxLayout(); a=QLabel("Network Overview");a.setObjectName("PageTitle");s=QLabel("Discover, inspect and troubleshoot your authorized network.");s.setObjectName("Muted");t.addWidget(a);t.addWidget(s);head.addLayout(t);head.addStretch();r=QPushButton("⟳ Refresh");r.setObjectName("PrimaryButton");r.clicked.connect(self.refresh_dashboard);head.addWidget(r);l.addLayout(head)
        p=get_primary_interface(); cards=[Card("Connection","ONLINE" if p and p.is_up else "OFFLINE",p.name if p else ""),Card("Local IP",p.ipv4 if p else "—",p.netmask if p else ""),Card("Gateway",get_default_gateway() or "—","Default route"),Card("DNS",(get_dns_servers() or ["—"])[0],"Primary resolver")]; g=QGridLayout();[g.addWidget(x,0,i) for i,x in enumerate(cards)];l.addLayout(g)
        box=QFrame();box.setObjectName("Card");bl=QVBoxLayout(box);h=QHBoxLayout();h.addWidget(QLabel("Automatic Discovery"));h.addStretch();go=QPushButton("Discover Hosts & Open Ports");go.setObjectName("PrimaryButton");go.clicked.connect(lambda:self.show_page("discovery"));h.addWidget(go);bl.addLayout(h);bl.addWidget(QLabel("Automatically detect the active subnet, discover hosts, resolve names, read MAC addresses and identify open TCP ports."));l.addWidget(box);l.addWidget(self.interface_table(),1);return body

    def refresh_dashboard(self):
        old=self.stack.currentIndex(); w=self.dashboard(); self.stack.removeWidget(self.pages["dashboard"]); self.pages["dashboard"]=w; self.stack.insertWidget(0,w); self.stack.setCurrentIndex(old)
    def interface_table(self):
        t=QTableWidget(0,6);t.setHorizontalHeaderLabels(["Interface","IPv4","Netmask","MAC","Speed","Status"]);t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for x in get_interfaces():
            r=t.rowCount();t.insertRow(r);vals=[x.name,x.ipv4 or "—",x.netmask or "—",x.mac or "—",f"{x.speed_mbps} Mbps" if x.speed_mbps else "—","UP" if x.is_up else "DOWN"]
            for c,v in enumerate(vals):t.setItem(r,c,QTableWidgetItem(v))
        return t

    def device(self):
        p=get_primary_interface(); rows=[("Hostname",socket.gethostname()),("FQDN",socket.getfqdn()),("Platform",platform.platform()),("Primary IPv4",p.ipv4 if p else "—"),("Gateway",get_default_gateway() or "—"),("DNS",", ".join(get_dns_servers()) or "—")];t=QTableWidget(len(rows),2);t.setHorizontalHeaderLabels(["Property","Value"]);t.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeToContents);t.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)
        for r,(k,v) in enumerate(rows):t.setItem(r,0,QTableWidgetItem(k));t.setItem(r,1,QTableWidgetItem(v))
        return self.shell("Device Info","System and network information collected locally.","◈",t)
    def network(self):
        p=get_primary_interface();sub="—"
        if p and p.ipv4 and p.netmask:
            try:sub=str(ipaddress.ip_network(f"{p.ipv4}/{p.netmask}",strict=False))
            except ValueError:pass
        body=QWidget();l=QVBoxLayout(body);g=QGridLayout();g.addWidget(Card("Active Interface",p.name if p else "—"),0,0);g.addWidget(Card("Subnet",sub),0,1);g.addWidget(Card("Gateway",get_default_gateway() or "—"),0,2);l.addLayout(g);l.addWidget(self.interface_table(),1);return self.shell("Local Network","Inspect adapters, subnet and the active route.","⌁",body)

    @staticmethod
    def parse_ports(text):
        out=set()
        for tok in re.split(r"[,;\s]+",text.strip()):
            if not tok:continue
            if "-" in tok:
                a,b=tok.split("-",1);out.update(range(int(a),int(b)+1))
            else:out.add(int(tok))
        return sorted(x for x in out if 1<=x<=65535)

    def discovery(self):
        body=QWidget();l=QVBoxLayout(body); row=QHBoxLayout();p=get_primary_interface();sub=""
        if p and p.ipv4 and p.netmask:
            try:sub=str(ipaddress.ip_network(f"{p.ipv4}/{p.netmask}",strict=False))
            except ValueError:pass
        self.dis_sub=QLineEdit(sub);self.dis_ports=QLineEdit(",".join(map(str,COMMON_PORTS)));self.dis_start=QPushButton("▶ Start Discovery");self.dis_start.setObjectName("PrimaryButton");self.dis_stop=QPushButton("■ Stop");self.dis_stop.setEnabled(False);self.dis_start.clicked.connect(self.start_discovery);self.dis_stop.clicked.connect(self.stop_discovery);row.addWidget(QLabel("Subnet"));row.addWidget(self.dis_sub,2);row.addWidget(QLabel("TCP Ports"));row.addWidget(self.dis_ports,3);row.addWidget(self.dis_start);row.addWidget(self.dis_stop);l.addLayout(row)
        self.dis_status=QLabel("READY — subnet auto-detected");self.dis_status.setObjectName("StatusPill");l.addWidget(self.dis_status);self.dis_progress=QProgressBar();self.dis_progress.setRange(0,0);self.dis_progress.hide();l.addWidget(self.dis_progress)
        self.dis_table=QTableWidget(0,6);self.dis_table.setHorizontalHeaderLabels(["IP","Hostname","MAC","State","Open TCP Ports","Port Count"]);self.dis_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);l.addWidget(self.dis_table,1);return self.shell("Network Discovery","One-click local discovery: find hosts and identify their open TCP ports.","◎",body)

    def start_discovery(self):
        try:net=str(ipaddress.ip_network(self.dis_sub.text().strip(),strict=False));ports=self.parse_ports(self.dis_ports.text());
        except ValueError as e:QMessageBox.warning(self,"Invalid settings",str(e));return
        if not ports:QMessageBox.warning(self,"Ports required","Enter ports such as 22,80,443 or 1-1024.");return
        self.dis_table.setRowCount(0);self.dis_start.setEnabled(False);self.dis_stop.setEnabled(True);self.dis_progress.show();self.dis_status.setText(f"SCANNING {net} — {len(ports)} ports/host")
        self.discovery_worker=DiscoveryWorker(net,ports);self.discovery_worker.host.connect(self.add_host);self.discovery_worker.done.connect(self.discovery_done);self.discovery_worker.error.connect(self.discovery_error);self.discovery_worker.start()
    def add_host(self,x:HostResult):
        self.last_discovery.append(x);r=self.dis_table.rowCount();self.dis_table.insertRow(r);vals=[x.ip,x.hostname or "—",x.mac or "—","UP",", ".join(map(str,x.open_ports or [])) or "None",str(len(x.open_ports or []))]
        for c,v in enumerate(vals):self.dis_table.setItem(r,c,QTableWidgetItem(v))
        self.dis_status.setText(f"FOUND {r+1} HOST(S) — scanning…")
    def discovery_done(self):self.dis_start.setEnabled(True);self.dis_stop.setEnabled(False);self.dis_progress.hide();self.dis_status.setText(f"COMPLETE — {self.dis_table.rowCount()} host(s) discovered")
    def discovery_error(self,e):self.discovery_done();QMessageBox.warning(self,"Discovery error",e)
    def stop_discovery(self):
        if self.discovery_worker:self.discovery_worker.stop();self.dis_status.setText("STOPPING…")

    def port_scanner(self):
        body=QWidget();l=QVBoxLayout(body);row=QHBoxLayout();h=QLineEdit("127.0.0.1");ports=QLineEdit(",".join(map(str,COMMON_PORTS)));go=QPushButton("▶ Scan");go.setObjectName("PrimaryButton");row.addWidget(h,2);row.addWidget(ports,3);row.addWidget(go);l.addLayout(row);st=QLabel("READY");st.setObjectName("StatusPill");l.addWidget(st);t=QTableWidget(0,3);t.setHorizontalHeaderLabels(["Port","State","Service"]);t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);l.addWidget(t,1)
        def run():
            try:ps=self.parse_ports(ports.text())
            except ValueError as e:QMessageBox.warning(self,"Invalid ports",str(e));return
            if not h.text().strip() or not ps:return
            go.setEnabled(False);st.setText(f"SCANNING {h.text().strip()}…");t.setRowCount(0);self.worker=Worker(lambda:scan_ports(h.text().strip(),ps));self.worker.result.connect(done);self.worker.error.connect(lambda e:(st.setText("ERROR"),go.setEnabled(True),QMessageBox.warning(self,"Scan",e)));self.worker.start()
        def done(opened):
            for p in opened:r=t.rowCount();t.insertRow(r);t.setItem(r,0,QTableWidgetItem(str(p)));t.setItem(r,1,QTableWidgetItem("OPEN"));
            st.setText(f"COMPLETE — {len(opened)} open port(s)");go.setEnabled(True)
        go.clicked.connect(run);return self.shell("Port Scanner","Scan one authorized host for open TCP ports.","◉",body)

    def multi_scanner(self):
        body=QWidget();l=QVBoxLayout(body);targets=QPlainTextEdit();targets.setPlaceholderText("One host per line\n192.168.1.1\n192.168.1.20");targets.setFixedHeight(100);ports=QLineEdit(",".join(map(str,COMMON_PORTS)));go=QPushButton("▶ Start Multi Scan");go.setObjectName("PrimaryButton");row=QHBoxLayout();row.addWidget(targets,3);x=QVBoxLayout();x.addWidget(QLabel("TCP Ports"));x.addWidget(ports);x.addWidget(go);x.addStretch();row.addLayout(x,2);l.addLayout(row);st=QLabel("READY");st.setObjectName("StatusPill");l.addWidget(st);t=QTableWidget(0,3);t.setHorizontalHeaderLabels(["Host","Result","Open Ports"]);t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);l.addWidget(t,1)
        def run():
            try:ps=self.parse_ports(ports.text())
            except ValueError as e:QMessageBox.warning(self,"Invalid ports",str(e));return
            hs=[x.strip() for x in targets.toPlainText().splitlines() if x.strip()];
            if not hs or not ps:return
            go.setEnabled(False);st.setText(f"SCANNING {len(hs)} HOST(S)…")
            def work():
                out=[]
                with ThreadPoolExecutor(max_workers=min(16,len(hs))) as ex:
                    fs={ex.submit(scan_ports,h,ps):h for h in hs}
                    for f in as_completed(fs):out.append((fs[f],f.result()))
                return out
            self.worker=Worker(work);self.worker.result.connect(done);self.worker.error.connect(lambda e:(go.setEnabled(True),QMessageBox.warning(self,"Scan",e)));self.worker.start()
        def done(rows):
            t.setRowCount(0)
            for h,op in sorted(rows):r=t.rowCount();t.insertRow(r);t.setItem(r,0,QTableWidgetItem(h));t.setItem(r,1,QTableWidgetItem("OPEN PORTS" if op else "NO OPEN PORTS"));t.setItem(r,2,QTableWidgetItem(", ".join(map(str,op)) or "—"))
            st.setText("COMPLETE");go.setEnabled(True)
        go.clicked.connect(run);return self.shell("Multi-IP Port Scanner","Scan several authorized hosts at once and compare open TCP ports.","◎",body)

    def ping(self,repeated=False):
        body=QWidget();l=QVBoxLayout(body);row=QHBoxLayout();h=QLineEdit(get_default_gateway());n=QSpinBox();n.setRange(1,60);n.setValue(10 if repeated else 1);go=QPushButton("▶ Start Ping");go.setObjectName("PrimaryButton");row.addWidget(h,1);row.addWidget(QLabel("Count"));row.addWidget(n);row.addWidget(go);l.addLayout(row);st=QLabel("READY");st.setObjectName("StatusPill");l.addWidget(st);t=QTableWidget(0,3);t.setHorizontalHeaderLabels(["Time","Status","Latency"]);t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);l.addWidget(t,1)
        def run():
            host=h.text().strip();go.setEnabled(False);t.setRowCount(0)
            def work():
                rows=[]
                for _ in range(n.value()):rows.append(ping_once(host));time.sleep(.35 if repeated else .05)
                return rows
            self.worker=Worker(work);self.worker.result.connect(done);self.worker.error.connect(lambda e:(go.setEnabled(True),QMessageBox.warning(self,"Ping",e)));self.worker.start()
        def done(rows):
            for z in rows:r=t.rowCount();t.insertRow(r);t.setItem(r,0,QTableWidgetItem(datetime.datetime.now().strftime("%H:%M:%S")));t.setItem(r,1,QTableWidgetItem("Reachable" if z.success else "Unreachable"));t.setItem(r,2,QTableWidgetItem(f"{z.latency_ms:.1f} ms" if z.latency_ms is not None else "—"))
            ok=[z.latency_ms for z in rows if z.success and z.latency_ms is not None];st.setText(f"COMPLETE — {len(ok)}/{len(rows)} replies" + (f" • avg {sum(ok)/len(ok):.1f} ms" if ok else ""));go.setEnabled(True)
        go.clicked.connect(run);return self.shell("Ping Graph" if repeated else "Ping","Measure reachability and latency.","⌁" if repeated else "◉",body)

    def dns(self):
        body=QWidget();l=QVBoxLayout(body);row=QHBoxLayout();h=QLineEdit();h.setPlaceholderText("example.com");typ=QComboBox();typ.addItems(["A","AAAA","MX","NS","CNAME","TXT"]);go=QPushButton("Lookup");go.setObjectName("PrimaryButton");row.addWidget(h,1);row.addWidget(typ);row.addWidget(go);l.addLayout(row);out=QPlainTextEdit();out.setReadOnly(True);l.addWidget(out,1)
        def run():
            def work():
                if typ.currentText() in ("A","AAAA"):
                    fam=socket.AF_INET if typ.currentText()=="A" else socket.AF_INET6;return "\n".join(sorted({x[4][0] for x in socket.getaddrinfo(h.text().strip(),None,fam)}))
                return subprocess.check_output(["nslookup",f"-type={typ.currentText()}",h.text().strip()],text=True,errors="replace",timeout=8,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            self.worker=Worker(work);self.worker.result.connect(lambda x:out.setPlainText(str(x)));self.worker.error.connect(lambda e:out.setPlainText(e));self.worker.start()
        go.clicked.connect(run);return self.shell("DNS Lookup","Query common DNS record types.","◌",body)

    def reverse(self):
        body=QWidget();l=QVBoxLayout(body);row=QHBoxLayout();h=QLineEdit();h.setPlaceholderText("8.8.8.8");go=QPushButton("Resolve");go.setObjectName("PrimaryButton");row.addWidget(h,1);row.addWidget(go);l.addLayout(row);out=QPlainTextEdit();out.setReadOnly(True);l.addWidget(out,1)
        go.clicked.connect(lambda:out.setPlainText(json.dumps({"IP":h.text().strip(),"Hostname":socket.gethostbyaddr(h.text().strip())[0],"Aliases":socket.gethostbyaddr(h.text().strip())[1]},indent=2)) if h.text().strip() else None);return self.shell("Reverse IP Lookup","Resolve an IP address to its hostname.","↩",body)

    def command_page(self,title,desc,icon,command,placeholder):
        body=QWidget();l=QVBoxLayout(body);row=QHBoxLayout();h=QLineEdit();h.setPlaceholderText(placeholder);go=QPushButton("▶ Run");go.setObjectName("PrimaryButton");row.addWidget(h,1);row.addWidget(go);l.addLayout(row);out=QPlainTextEdit();out.setReadOnly(True);l.addWidget(out,1)
        def run():
            cmd=command.split() if " " in command else [command];
            if command in ("whois","tracert"):cmd.append(h.text().strip())
            self.worker=Worker(lambda:subprocess.check_output(cmd,text=True,errors="replace",timeout=45,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)));self.worker.result.connect(lambda x:out.setPlainText(x));self.worker.error.connect(lambda e:out.setPlainText(e));self.worker.start()
        go.clicked.connect(run);return self.shell(title,desc,icon,body)

    def wol(self):
        body=QWidget();l=QVBoxLayout(body);row=QHBoxLayout();m=QLineEdit();m.setPlaceholderText("AA:BB:CC:DD:EE:FF");b=QLineEdit("255.255.255.255");go=QPushButton("Send Magic Packet");go.setObjectName("PrimaryButton");row.addWidget(m,2);row.addWidget(b,1);row.addWidget(go);l.addLayout(row);st=QLabel("READY");st.setObjectName("StatusPill");l.addWidget(st);l.addStretch()
        def run():
            mac=re.sub(r"[^0-9A-Fa-f]","",m.text());
            if len(mac)!=12:QMessageBox.warning(self,"Invalid MAC","Enter a valid MAC address.");return
            try:s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1);s.sendto(bytes.fromhex("FF"*6+mac*16),(b.text().strip(),9));s.close();st.setText("SENT — magic packet transmitted")
            except OSError as e:st.setText("ERROR");QMessageBox.warning(self,"Wake-On-LAN",str(e))
        go.clicked.connect(run);return self.shell("Wake-On-LAN","Send a magic packet to a device you manage.","✦",body)

    def ipcalc(self):
        body=QWidget();l=QVBoxLayout(body);row=QHBoxLayout();h=QLineEdit("192.168.1.10/24");go=QPushButton("Calculate");go.setObjectName("PrimaryButton");row.addWidget(h,1);row.addWidget(go);l.addLayout(row);t=QTableWidget(0,2);t.setHorizontalHeaderLabels(["Property","Value"]);t.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeToContents);t.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch);l.addWidget(t,1)
        def run():
            try:v=calculate_network(h.text())
            except ValueError as e:QMessageBox.warning(self,"Invalid CIDR",str(e));return
            t.setRowCount(0)
            for k,x in v.items():r=t.rowCount();t.insertRow(r);t.setItem(r,0,QTableWidgetItem(k));t.setItem(r,1,QTableWidgetItem(x))
        go.clicked.connect(run);run();return self.shell("IP Calculator","Calculate IPv4 and IPv6 subnet details.","▣",body)

    def cert(self):
        body=QWidget();l=QVBoxLayout(body);row=QHBoxLayout();h=QLineEdit();h.setPlaceholderText("example.com:443");go=QPushButton("Inspect TLS");go.setObjectName("PrimaryButton");row.addWidget(h,1);row.addWidget(go);l.addLayout(row);out=QPlainTextEdit();out.setReadOnly(True);l.addWidget(out,1)
        def run():
            host,_,ps=h.text().strip().partition(":");port=int(ps or 443)
            def work():
                ctx=ssl.create_default_context();
                with socket.create_connection((host,port),timeout=7) as s:
                    with ctx.wrap_socket(s,server_hostname=host) as ss:return json.dumps({"TLS version":ss.version(),"Cipher":ss.cipher(),"Certificate":ss.getpeercert()},indent=2,default=str)
            self.worker=Worker(work);self.worker.result.connect(out.setPlainText);self.worker.error.connect(out.setPlainText);self.worker.start()
        go.clicked.connect(run);return self.shell("Certificate Viewer","Inspect the certificate and negotiated TLS session.","◇",body)

    def speed(self):
        body=QWidget();l=QVBoxLayout(body);row=QHBoxLayout();u=QLineEdit("https://speed.cloudflare.com/__down?bytes=1000000");go=QPushButton("Test Download");go.setObjectName("PrimaryButton");row.addWidget(u,1);row.addWidget(go);l.addLayout(row);out=QPlainTextEdit();out.setReadOnly(True);l.addWidget(out,1)
        def run():
            def work():start=time.perf_counter();data=urllib.request.urlopen(u.text().strip(),timeout=20).read();sec=time.perf_counter()-start;return f"Bytes: {len(data):,}\nTime: {sec:.2f}s\nApprox download: {(len(data)*8/sec)/1_000_000:.2f} Mbps"
            self.worker=Worker(work);self.worker.result.connect(out.setPlainText);self.worker.error.connect(out.setPlainText);self.worker.start()
        go.clicked.connect(run);return self.shell("Speed Test","Measure HTTP download throughput from a selected endpoint.","◒",body)

    def mdns(self): return self.command_page("mDNS Browser","Use an installed mDNS scanner if available.","◎","dns-sd","Service type, e.g. _http._tcp")
    def upnp(self):
        body=QWidget();l=QVBoxLayout(body);go=QPushButton("▶ Discover UPnP / SSDP Devices");go.setObjectName("PrimaryButton");l.addWidget(go);out=QPlainTextEdit();out.setReadOnly(True);l.addWidget(out,1)
        def run():
            def work():
                s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM,socket.IPPROTO_UDP);s.settimeout(1.8);s.sendto(b"M-SEARCH * HTTP/1.1\r\nHOST:239.255.255.250:1900\r\nMAN: \"ssdp:discover\"\r\nMX: 1\r\nST: ssdp:all\r\n\r\n",("239.255.255.250",1900));rows=[]
                try:
                    while True:rows.append(s.recvfrom(65535)[0].decode("utf-8","replace"))
                except socket.timeout:pass
                s.close();return "\n\n--- DEVICE ---\n".join(rows) if rows else "No SSDP responses received."
            self.worker=Worker(work);self.worker.result.connect(out.setPlainText);self.worker.error.connect(out.setPlainText);self.worker.start()
        go.clicked.connect(run);return self.shell("UPnP Browser","Discover UPnP devices using SSDP multicast.","⌗",body)

    def network_map(self):
        body=QWidget();l=QVBoxLayout(body);go=QPushButton("↻ Load Latest Discovery");go.setObjectName("PrimaryButton");l.addWidget(go);t=QTableWidget(0,4);t.setHorizontalHeaderLabels(["Host","Hostname","MAC","Open Ports"]);t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);l.addWidget(t,1)
        def run():
            t.setRowCount(0)
            for x in self.last_discovery:r=t.rowCount();t.insertRow(r);[t.setItem(r,c,QTableWidgetItem(v)) for c,v in enumerate([x.ip,x.hostname or "—",x.mac or "—",", ".join(map(str,x.open_ports or [])) or "—"])]
        go.clicked.connect(run);return self.shell("Network Map","A clean table view of hosts found by Network Discovery.","⌘",body)

    def headers(self):
        body=QWidget();l=QVBoxLayout(body);row=QHBoxLayout();u=QLineEdit();u.setPlaceholderText("https://example.com");go=QPushButton("Inspect Headers");go.setObjectName("PrimaryButton");row.addWidget(u,1);row.addWidget(go);l.addLayout(row);out=QPlainTextEdit();out.setReadOnly(True);l.addWidget(out,1);go.clicked.connect(lambda: self._http_headers(u,out));return self.shell("HTTP Header Checker","Inspect response headers for an HTTP/HTTPS endpoint.","✓",body)
    def _http_headers(self,u,out):
        def work():r=urllib.request.urlopen(urllib.request.Request(u.text().strip(),method="HEAD"),timeout=10);return "\n".join(f"{k}: {v}" for k,v in r.headers.items())
        self.worker=Worker(work);self.worker.result.connect(out.setPlainText);self.worker.error.connect(out.setPlainText);self.worker.start()
    def connections(self): return self.command_page("Connection Monitor","Show active TCP connections using Windows netstat.","▥","netstat -ano","Press Run to refresh")

    def show_page(self,key):
        self.stack.setCurrentWidget(self.pages[key])
        for b in self.nav_buttons:b.setProperty("active",b.property("key")==key);b.style().unpolish(b);b.style().polish(b)
    def filter_nav(self,text):
        q=text.strip().lower()
        for b in self.nav_buttons:b.setVisible(not q or q in b.text().lower())
