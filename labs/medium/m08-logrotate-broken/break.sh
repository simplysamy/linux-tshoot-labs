#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

L=/var/log/shopapp

# two weeks of logs that were never rotated (~190 MB)
yes "$(date '+%F %T'),123 INFO 127.0.0.1 \"GET /api/cart?id=48121 HTTP/1.0\" 200 -" \
    | head -c 190M >> "$L/app.log" || true
chown shopapp:shopapp "$L/app.log"

# "let the deploy group read the logs"
chmod 0775 "$L"

cat > /etc/logrotate.d/shopapp <<'EOF'
/var/log/shopapp/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 0640 shopapp shopapp
}
EOF
chmod 0644 /etc/logrotate.d/shopapp
sync
