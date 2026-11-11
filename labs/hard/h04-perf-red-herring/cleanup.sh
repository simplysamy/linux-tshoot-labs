#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
systemctl disable --now audit-sync.timer >/dev/null 2>&1 || true
systemctl stop audit-sync.service >/dev/null 2>&1 || true
systemctl disable --now batch-encoder >/dev/null 2>&1 || true
rm -rf /etc/systemd/system/audit-sync.service /etc/systemd/system/audit-sync.service.d \
       /etc/systemd/system/audit-sync.timer /etc/systemd/system/batch-encoder.service \
       /etc/systemd/system/batch-encoder.service.d
rm -f /usr/local/bin/audit-sync /usr/local/bin/batch-encoder /var/tmp/audit-sync.dat
systemctl daemon-reload
systemctl reset-failed audit-sync.service audit-sync.timer batch-encoder >/dev/null 2>&1 || true
restore_baseline
