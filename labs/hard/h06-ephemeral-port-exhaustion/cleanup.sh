#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
S=$LAB_STATE_DIR
systemctl disable --now price-sync >/dev/null 2>&1 || true
rm -rf /etc/systemd/system/price-sync.service /etc/systemd/system/price-sync.service.d \
       /usr/local/bin/price-sync /etc/price-sync.conf /etc/sysctl.d/90-net-tuning.conf
systemctl daemon-reload
if [[ -f $S/h06-sysctl.orig ]]; then
    while IFS='=' read -r k v; do sysctl -qw "$k=$v" || true; done < "$S/h06-sysctl.orig"
    rm -f "$S/h06-sysctl.orig"
fi
info "Note: sysctl files you created yourself are left in place."
restore_baseline
