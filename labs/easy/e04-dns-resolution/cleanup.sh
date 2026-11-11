#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"

sed -i '/tshoot-lab migration test/d' /etc/hosts
if [[ -f $LAB_STATE_DIR/e04-resolv-link ]]; then
    ln -sfn "$(cat "$LAB_STATE_DIR/e04-resolv-link")" /etc/resolv.conf
    rm -f "$LAB_STATE_DIR/e04-resolv-link"
elif [[ -f $BACKUP_DIR/_etc_resolv.conf ]]; then
    cp -a "$BACKUP_DIR/_etc_resolv.conf" /etc/resolv.conf
fi
restore_baseline
