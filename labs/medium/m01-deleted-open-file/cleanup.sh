#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
systemctl disable --now log-shipper >/dev/null 2>&1 || true
rm -f /etc/systemd/system/log-shipper.service /usr/local/bin/log-shipper /var/log/shopapp/shipper-spool.log
systemctl daemon-reload
restore_baseline
