#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
rm -f /etc/cron.d/report-export

# 1. reopen the path so stuck tasks can finish
while rule=$(iptables -S OUTPUT | grep -E 'SEC-410|10\.240\.0\.10' | head -1) && [[ -n $rule ]]; do
    eval "iptables ${rule/-A /-D }"
done
sleep 3
pkill -f /usr/local/bin/report-export 2>/dev/null || true
pkill -x df 2>/dev/null || true

# 2. unmount and remove the NAS
umount -f -l /mnt/reports 2>/dev/null || true
sed -i '\# /mnt/reports #d' /etc/fstab
systemctl daemon-reload
sed -i '/# tshoot-lab/d' /etc/exports 2>/dev/null || true
exportfs -ra 2>/dev/null || true
systemctl stop nfs-server 2>/dev/null || true
ip link del nas0 2>/dev/null || true
rm -rf /srv/nfs /usr/local/bin/report-export
rmdir /mnt/reports 2>/dev/null || true
restore_baseline      # also removes the /etc/hosts entry
