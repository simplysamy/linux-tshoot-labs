#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
L=/var/log/shopapp
rm -f /etc/logrotate.d/shopapp "$LAB_STATE_DIR/m08-verify.state"
rm -f "$L"/*.log.[0-9]* "$L"/*.gz
[[ -f $L/app.log ]] && : > "$L/app.log"
systemctl restart shopapp 2>/dev/null || true    # drop any deleted-but-open log file
restore_baseline
