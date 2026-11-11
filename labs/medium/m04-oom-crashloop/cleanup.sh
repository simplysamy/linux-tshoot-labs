#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
systemctl disable --now cache-warmer >/dev/null 2>&1 || true
rm -rf /etc/systemd/system/cache-warmer.service /etc/systemd/system/cache-warmer.service.d
rm -f /usr/local/bin/cache-warmer /etc/cache-warmer.conf
systemctl daemon-reload
systemctl reset-failed cache-warmer >/dev/null 2>&1 || true
restore_baseline
