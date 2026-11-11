#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

S=$LAB_STATE_DIR
for k in net.ipv4.ip_local_port_range net.ipv4.tcp_tw_reuse net.ipv4.tcp_fin_timeout; do
    echo "$k=$(sysctl -n $k | tr '\t' ' ')"
done > "$S/h06-sysctl.orig"

cat > /etc/sysctl.d/90-net-tuning.conf <<'EOF'
# CHG-701 network tuning (from "10 Linux TCP settings for high traffic")
# keep ephemeral ports away from our monitoring agent ports
net.ipv4.ip_local_port_range = 61000 61100
# safer
net.ipv4.tcp_tw_reuse = 0
# release closed sockets later to avoid resets
net.ipv4.tcp_fin_timeout = 120
EOF
sysctl -q -p /etc/sysctl.d/90-net-tuning.conf

cat > /etc/price-sync.conf <<'EOF'
[sync]
url_host = 127.0.0.1
url_port = 80
path = /
requests_per_second = 20
reuse_connections = false
EOF

cat > /usr/local/bin/price-sync <<'EOF'
#!/usr/bin/env python3
"""price-sync: polls the shop for prices."""
import configparser, http.client, time

cfg = configparser.ConfigParser()
cfg.read("/etc/price-sync.conf")
c = cfg["sync"]
host, port, path = c.get("url_host"), c.getint("url_port"), c.get("path")
rate = c.getfloat("requests_per_second", 20)
reuse = c.getboolean("reuse_connections", False)
print(f"price-sync: {rate:g} req/s, reuse_connections={reuse}", flush=True)

conn = None
errors, last_exc, last_report = 0, "", time.time()
while True:
    try:
        if conn is None:
            conn = http.client.HTTPConnection(host, port, timeout=5)
        conn.request("GET", path)          # HTTP/1.1, keep-alive by default
        resp = conn.getresponse()
        resp.read()
        if resp.status != 200:
            errors, last_exc = errors + 1, f"HTTP {resp.status}"
        if not reuse:
            conn.close()                   # we close first -> TIME_WAIT on our side
            conn = None
    except OSError as exc:
        errors, last_exc = errors + 1, exc
        if conn:
            conn.close()
        conn = None
    if time.time() - last_report >= 10:
        if errors:
            print(f"ERROR {errors} failed syncs in last 10s (last: {last_exc})", flush=True)
        errors, last_report = 0, time.time()
    time.sleep(1 / rate)
EOF
chmod 0755 /usr/local/bin/price-sync

cat > /etc/systemd/system/price-sync.service <<'EOF'
[Unit]
Description=Price sync client
After=nginx.service

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/price-sync
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now price-sync >/dev/null 2>&1
sleep 10
