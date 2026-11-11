#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
IMG=$LAB_STATE_DIR/shopdata.img

systemctl stop shopapp || true
if findmnt -n /srv/shopdata >/dev/null; then
    umount /srv/shopdata || umount -l /srv/shopdata
fi
e2fsck -fy "$IMG" >/dev/null 2>&1 || true
mount /srv/shopdata
rm -rf /srv/shopdata/lost+found/#* /srv/backups/catalog "$LAB_STATE_DIR/h02-catalog.sha256"
rm -f /srv/shopdata/catalog/products.db
restore_baseline     # recreates a default products.db
