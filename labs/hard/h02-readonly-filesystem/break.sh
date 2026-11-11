#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

IMG=$LAB_STATE_DIR/shopdata.img
CAT=/srv/shopdata/catalog/products.db

# A real catalog, plus last night's backup of it.
python3 - <<'EOF'
import random
random.seed(7)
with open("/srv/shopdata/catalog/products.db", "w") as fh:
    fh.write("sku,name,price\n")
    for i in range(1, 501):
        fh.write(f"A-{1000+i},Product {i},{random.randint(199, 9999)/100:.2f}\n")
EOF
chown shopapp:shopapp "$CAT"
mkdir -p /srv/backups/catalog
cp -a "$CAT" "/srv/backups/catalog/products.db.$(date -d yesterday +%F)"
sha256sum "$CAT" | awk '{print $1}' > "$LAB_STATE_DIR/h02-catalog.sha256"

# Simulate on-disk corruption: wipe the catalog file's inode (storage glitch).
systemctl stop shopapp
sync
umount /srv/shopdata
debugfs -w -R "clri /catalog/products.db" "$IMG" >/dev/null 2>&1
mount /srv/shopdata
systemctl start shopapp

# The nightly price job reads the catalog -> ext4 detects the corruption,
# logs EXT4-fs error and (errors=remount-ro) flips the filesystem to read-only.
cat "$CAT" >/dev/null 2>&1 || true
ls -l /srv/shopdata/catalog >/dev/null 2>&1 || true
sleep 1
if ! findmnt -no OPTIONS /srv/shopdata | grep -qE '(^|,)ro(,|$)'; then
    # fallback in case this kernel did not remount by itself
    mount -o remount,ro /srv/shopdata
fi
curl -s -o /dev/null http://127.0.0.1/health || true
