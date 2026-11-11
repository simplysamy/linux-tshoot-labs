#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

f=/etc/nginx/sites-available/shopapp
backup_file "$f"
# "Quick change" by a colleague: bump the timeout... and forget the semicolon.
sed -i 's/proxy_read_timeout 10s;/proxy_read_timeout 30s\n        proxy_send_timeout 30s;/' "$f"
systemctl restart nginx 2>/dev/null || true   # fails -> nginx is now down
