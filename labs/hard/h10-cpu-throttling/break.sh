#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

# FINOPS-77, layer 1: a slice for "the shop", capped at 10%
cat > /etc/systemd/system/shop.slice <<'EOF'
[Unit]
Description=Shop services

[Slice]
# FINOPS-77 cap the whole shop at 10%
CPUQuota=10%
EOF

# FINOPS-77, layer 2: shopapp itself capped at 5% and moved into the slice
mkdir -p /etc/systemd/system/shopapp.service.d
cat > /etc/systemd/system/shopapp.service.d/50-finops.conf <<'EOF'
[Service]
# FINOPS-77 right-size noisy services
CPUQuota=5%
Slice=shop.slice
EOF

# expected production-like load
cat > /usr/local/bin/traffic-replay <<'EOF'
#!/usr/bin/env python3
"""traffic-replay: replays a share of production traffic against the local shop."""
import threading, time, urllib.request

def worker():
    while True:
        try:
            urllib.request.urlopen("http://127.0.0.1/", timeout=15).read()
        except OSError:
            time.sleep(0.5)
        time.sleep(0.1)          # ~60 req/s in total when the app is healthy

for _ in range(6):
    threading.Thread(target=worker, daemon=True).start()
print("traffic-replay: 6 workers", flush=True)
while True:
    time.sleep(3600)
EOF
chmod 0755 /usr/local/bin/traffic-replay
cat > /etc/systemd/system/traffic-replay.service <<'EOF'
[Unit]
Description=Production traffic replay (canary testing)
After=nginx.service

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/traffic-replay
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl restart shopapp
systemctl enable --now traffic-replay >/dev/null 2>&1
sleep 10
