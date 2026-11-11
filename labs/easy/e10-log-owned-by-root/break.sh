#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

L=/var/log/shopapp
systemctl stop shopapp
mv "$L/app.log" "$L/app.log.old"

# "ran app.py by hand as root" - it creates a fresh app.log owned by root
timeout 3 python3 /opt/shopapp/app.py >/dev/null 2>&1 || true
[[ -f $L/app.log ]] || touch "$L/app.log"
chown root:root "$L/app.log"; chmod 0644 "$L/app.log"

systemctl start shopapp || true
