#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

S=$LAB_STATE_DIR

# SEC-099: a sane stateful rule - it also makes the kernel track every connection
iptables -C INPUT -m conntrack --ctstate INVALID -m comment --comment "SEC-099 drop invalid packets" -j DROP 2>/dev/null \
    || iptables -I INPUT -m conntrack --ctstate INVALID -m comment --comment "SEC-099 drop invalid packets" -j DROP
sysctl -n net.netfilter.nf_conntrack_max > "$S/h08-max.orig"

cat > /etc/sysctl.d/70-memory-saving.conf <<'EOF'
# CHG-830 reduce kernel memory on small VMs
net.netfilter.nf_conntrack_max = 1024
EOF
sysctl -q -p /etc/sysctl.d/70-memory-saving.conf

# local metrics exporter on :9100 - accepts connections and keeps them open
cat > /usr/local/bin/metrics-exporter <<'EOF'
#!/usr/bin/env python3
import selectors, socket
sel = selectors.DefaultSelector()
srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
srv.bind(("127.0.0.1", 9100)); srv.listen(4096); srv.setblocking(False)
sel.register(srv, selectors.EVENT_READ)
while True:
    for key, _ in sel.select():
        s = key.fileobj
        if s is srv:
            c, _ = srv.accept(); c.setblocking(False); sel.register(c, selectors.EVENT_READ)
        else:
            try:
                data = s.recv(4096)
            except OSError:
                data = b""
            if not data:
                sel.unregister(s); s.close()
            else:
                s.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 12\r\n\r\nup_metric 1\n")
EOF

cat > /etc/metrics-scraper.conf <<'EOF'
[scraper]
target = 127.0.0.1:9100
interval_s = 5
; v2: keep connections warm
pool_size = 1500
connection_max_age_s = 300
EOF

cat > /usr/local/bin/metrics-scraper <<'EOF'
#!/usr/bin/env python3
"""metrics-scraper v2: keeps a warm pool of connections to the exporter."""
import configparser, socket, time
cfg = configparser.ConfigParser(inline_comment_prefixes=(";",))
cfg.read("/etc/metrics-scraper.conf")
c = cfg["scraper"]
host, port = c.get("target").split(":")
pool_size = c.getint("pool_size"); max_age = c.getint("connection_max_age_s", 300)
interval = c.getfloat("interval_s", 5)
print(f"metrics-scraper v2: pool_size={pool_size}", flush=True)
pool, failed, last = [], 0, 0
while True:
    now = time.time()
    pool = [(s, t) for s, t in pool if now - t < max_age or s.close()]
    opened = 0
    while len(pool) < pool_size and opened < 100:          # grow the pool, max 100 per tick
        s = socket.socket(); s.settimeout(1)
        try:
            s.connect((host, int(port))); pool.append((s, now))
        except OSError:
            s.close(); failed += 1
            break                                           # try again next tick
        opened += 1
    if now - last >= interval and pool:
        try:
            pool[0][0].sendall(b"GET /metrics HTTP/1.1\r\n\r\n"); pool[0][0].recv(4096)
        except OSError:
            pool[0][0].close(); pool.pop(0)
        print(f"scrape ok pool={len(pool)} connect_failures={failed}", flush=True)
        failed, last = 0, now
    time.sleep(0.2)
EOF
chmod 0755 /usr/local/bin/metrics-exporter /usr/local/bin/metrics-scraper

for svc in metrics-exporter metrics-scraper; do
cat > /etc/systemd/system/$svc.service <<EOF
[Unit]
Description=$svc
After=network.target

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/$svc
Restart=always
RestartSec=2
LimitNOFILE=8192

[Install]
WantedBy=multi-user.target
EOF
done
systemctl daemon-reload
systemctl enable --now metrics-exporter >/dev/null 2>&1
sleep 1
systemctl enable --now metrics-scraper >/dev/null 2>&1
info "Waiting 30s for the scraper pool to fill the table ..."
sleep 30
