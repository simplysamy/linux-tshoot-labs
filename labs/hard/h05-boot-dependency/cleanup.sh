#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
rm -rf /etc/systemd/system/shopapp.service.d
systemctl daemon-reload
systemctl reset-failed shopapp srv-shopdata.mount >/dev/null 2>&1 || true
restore_baseline     # rewrites the fstab lines and mounts the volumes
