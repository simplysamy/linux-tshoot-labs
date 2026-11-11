#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
systemctl disable --now shopapp-report.timer >/dev/null 2>&1 || true
rm -rf /etc/systemd/system/shopapp-report.service /etc/systemd/system/shopapp-report.timer \
       /etc/systemd/system/shopapp-report.service.d
systemctl reset-failed shopapp-report.service 2>/dev/null || true
rm -rf /opt/shoptools /etc/profile.d/shoptools.sh /usr/local/bin/shopapp-report /srv/backups/shop-report.txt*
[[ -L /usr/local/bin/shopctl ]] && rm -f /usr/local/bin/shopctl
systemctl daemon-reload
restore_baseline
