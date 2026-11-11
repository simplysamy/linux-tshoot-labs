#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

# An old "status page" service from a past migration, re-enabled by mistake.
mkdir -p /var/www/legacy-status
cat > /var/www/legacy-status/index.html <<'EOF'
<h1>Maintenance status: ALL GREEN (legacy page, 2021)</h1>
EOF

cat > /etc/systemd/system/legacy-status.service <<'EOF'
[Unit]
Description=Legacy maintenance status page
After=network.target

[Service]
ExecStart=/usr/bin/python3 -m http.server 80 --bind 0.0.0.0 --directory /var/www/legacy-status
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl stop nginx
systemctl enable --now legacy-status >/dev/null 2>&1
sleep 1
systemctl start nginx 2>/dev/null || true    # fails: port 80 already in use
