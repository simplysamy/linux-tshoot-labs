#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

backup_file /etc/fstab

# Change 1 (storage migration, "cleanup" of names): fstab now points at a file that does not exist.
sed -i 's#^/var/lib/tshoot/shopdata.img /srv/shopdata #/var/lib/tshoot/shop-data.img /srv/shopdata #' /etc/fstab

# Change 2 (security ticket SEC-117): service account "renamed". The rename itself never happened.
mkdir -p /etc/systemd/system/shopapp.service.d
cat > /etc/systemd/system/shopapp.service.d/20-service-account.conf <<'EOF'
# SEC-117: run services under the new naming standard
[Service]
User=shop-app
Group=shop-app
EOF

# Simulate the maintenance reboot of the app stack.
systemctl stop shopapp
sync
umount /srv/shopdata
systemctl daemon-reload            # fstab generator rebuilds srv-shopdata.mount
systemctl start shopapp 2>/dev/null || true
