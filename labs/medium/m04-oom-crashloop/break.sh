#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

cat > /usr/local/bin/cache-warmer <<'EOF'
#!/usr/bin/env python3
"""Keeps hot product pages in memory. Cache size limit comes from the config."""
import configparser, sys, time
cfg = configparser.ConfigParser()
cfg.read("/etc/cache-warmer.conf")
max_mb = cfg.getint("cache", "max_mb", fallback=64)     # 0 = unlimited
print(f"cache-warmer starting, max_mb={max_mb} ({'UNLIMITED' if max_mb == 0 else 'bounded'})", flush=True)
cache = []
while True:
    cache.append(b"p" * (1024 * 1024))     # warm 1 MB of "pages" (touched, so it counts in RSS)
    if max_mb and len(cache) > max_mb:
        cache.pop(0)                       # evict oldest
    if len(cache) % 25 == 0:
        print(f"cache size {len(cache)} MB", flush=True)
    time.sleep(0.05)
EOF
chmod 0755 /usr/local/bin/cache-warmer

cat > /etc/cache-warmer.conf <<'EOF'
[cache]
# Size of the in-memory page cache in MB. Must stay well below the unit's MemoryMax (160M).
# Changed for load test LT-88: 0 = unlimited.  (was: 64)
max_mb = 0
EOF

cat > /etc/systemd/system/cache-warmer.service <<'EOF'
[Unit]
Description=ShopApp cache warmer

[Service]
User=shopapp
ExecStart=/usr/bin/python3 -u /usr/local/bin/cache-warmer
MemoryMax=160M
MemorySwapMax=0
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now cache-warmer >/dev/null 2>&1
info "Waiting ~25s so a few OOM kills happen..."
sleep 25
