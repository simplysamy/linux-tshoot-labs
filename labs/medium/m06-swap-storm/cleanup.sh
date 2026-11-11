#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
S=$LAB_STATE_DIR
systemctl disable --now report-builder >/dev/null 2>&1 || true
rm -f /etc/systemd/system/report-builder.service /usr/local/bin/report-builder /etc/report-builder.conf \
      /etc/sysctl.d/60-batch-tuning.conf
systemctl daemon-reload
if [[ -f $S/m06-swappiness.orig ]]; then
    sysctl -qw vm.swappiness="$(cat "$S/m06-swappiness.orig")"
    rm -f "$S/m06-swappiness.orig"
fi
if [[ -f $S/m06-swapfile ]]; then
    swapoff "$S/m06-swapfile" 2>/dev/null || true
    rm -f "$S/m06-swapfile"
fi
restore_baseline
