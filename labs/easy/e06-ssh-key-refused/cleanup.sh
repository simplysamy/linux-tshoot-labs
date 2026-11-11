#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
B=$BACKUP_DIR/_etc_ssh_sshd_config
if [[ -f $B ]]; then
    cp -a "$B" /etc/ssh/sshd_config && rm -f "$B"
    systemctl restart ssh 2>/dev/null || systemctl restart sshd 2>/dev/null || true
fi
pkill -u deploy 2>/dev/null || true
userdel -r deploy 2>/dev/null || true
rm -rf "$LAB_STATE_DIR/e06"
restore_baseline
