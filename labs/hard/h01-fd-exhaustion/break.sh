#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

# Change 1 (weeks ago, harmless alone): limits drop-in copied from an old container template.
mkdir -p /etc/systemd/system/shopapp.service.d
cat > /etc/systemd/system/shopapp.service.d/10-limits.conf <<'EOF'
# copied from legacy container template (tpl-v1)
[Service]
LimitNOFILE=64
EOF

# Change 2 (yesterday): request tracing turned on for debugging INC-1999.
# (comment on its own line: python configparser does not strip inline comments)
sed -i 's/^trace_requests = false/; enabled for INC-1999 debugging - turn off after!\ntrace_requests = true/' /etc/shopapp/config.ini

systemctl daemon-reload
systemctl restart shopapp
sleep 1

# Normal traffic.
for _ in $(seq 90); do curl -s -o /dev/null --max-time 1 http://127.0.0.1:8080/ || true; done
