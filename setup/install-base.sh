#!/usr/bin/env bash
# Builds (or restores) the "golden" lab baseline. Safe to re-run any time.
#
#   client --> nginx :80 --> shopapp :8080 (python, systemd unit, user shopapp)
#                                 |-- config : /etc/shopapp/config.ini
#                                 |-- logs   : /var/log/shopapp  (256M loop volume)
#                                 `-- data   : /srv/shopdata     (128M loop volume, 4096 inodes)
#
# Usage: sudo bash setup/install-base.sh          (full install)
#        SKIP_PACKAGES=1 sudo bash ...            (restore only, used by lab resets)
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE=/var/lib/tshoot

[[ $EUID -eq 0 ]] || { echo "Run as root"; exit 1; }

if ! grep -qiE 'ubuntu|debian' /etc/os-release; then
    echo "WARNING: labs are written for Ubuntu 22.04/24.04. Continuing anyway."
fi

# ---------------------------------------------------------------- packages
if [[ "${SKIP_PACKAGES:-0}" != 1 ]]; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq \
        nginx curl dnsutils lsof strace sysstat psmisc procps htop \
        tcpdump traceroute iproute2 iptables cron e2fsprogs util-linux \
        python3 net-tools bash-completion less vim-tiny \
        openssh-server openssl logrotate conntrack iputils-ping iputils-tracepath \
        nfs-kernel-server nfs-common >/dev/null
    # NFS server is only used by lab H09; keep it off in the baseline
    systemctl disable --now nfs-server >/dev/null 2>&1 || true
    apt-get install -y -qq iotop-c >/dev/null 2>&1 || apt-get install -y -qq iotop >/dev/null 2>&1 || true
    # enable sysstat collection so `sar` has history
    sed -i 's/^ENABLED="false"/ENABLED="true"/' /etc/default/sysstat 2>/dev/null || true
    systemctl enable --now sysstat >/dev/null 2>&1 || true
fi

mkdir -p "$STATE/backup"
touch /etc/tshoot-lab          # marker: "this host may be broken on purpose"

# ---------------------------------------------------------------- user
id shopapp >/dev/null 2>&1 || useradd --system --home /opt/shopapp --shell /usr/sbin/nologin shopapp

# ---------------------------------------------------------------- loop volumes
make_volume() {   # image size mountpoint extra-mkfs-args
    local img=$1 size=$2 mnt=$3; shift 3
    if [[ ! -f $img ]]; then
        truncate -s "$size" "$img"
        mkfs.ext4 -q -F "$@" "$img"
    fi
    mkdir -p "$mnt"
    # fstab entry (rewritten every time so H5 "typo" is repaired by reset)
    sed -i "\# $mnt #d" /etc/fstab
    echo "$img $mnt ext4 loop,defaults,nofail,errors=remount-ro 0 2" >> /etc/fstab
}
make_volume "$STATE/applogs.img"   256M /var/log/shopapp
make_volume "$STATE/shopdata.img"  128M /srv/shopdata -N 4096
systemctl daemon-reload

ensure_mounted() {
    local img=$1 mnt=$2
    if findmnt -n "$mnt" >/dev/null; then
        # repair a read-only remount left over from a lab
        if findmnt -no OPTIONS "$mnt" | grep -qE '(^|,)ro(,|$)'; then
            umount "$mnt" || umount -l "$mnt"
        else
            return 0
        fi
    fi
    e2fsck -fy "$img" >/dev/null 2>&1 || true
    mount "$mnt"
}
ensure_mounted "$STATE/applogs.img"  /var/log/shopapp
ensure_mounted "$STATE/shopdata.img" /srv/shopdata

chown shopapp:shopapp /var/log/shopapp /srv/shopdata
chmod 0755 /var/log/shopapp /srv/shopdata
# log files must belong to the app (lab E10 breaks this)
find /var/log/shopapp -maxdepth 1 -type f -name '*.log' -exec chown shopapp:shopapp {} + -exec chmod 0644 {} +
mkdir -p /srv/shopdata/sessions /srv/shopdata/catalog /srv/backups
chown shopapp:shopapp /srv/shopdata/sessions /srv/shopdata/catalog
[[ -f /srv/shopdata/catalog/products.db ]] || echo "sku,name,price" > /srv/shopdata/catalog/products.db
chown shopapp:shopapp /srv/shopdata/catalog/products.db

# ---------------------------------------------------------------- app
install -d -m 0755 /opt/shopapp
install -m 0755 "$SRC/files/app.py" /opt/shopapp/app.py
install -d -m 0755 -o root -g root /etc/shopapp
install -m 0640 -o root -g shopapp "$SRC/files/config.ini" /etc/shopapp/config.ini

rm -rf /etc/systemd/system/shopapp.service.d
install -m 0644 "$SRC/files/shopapp.service" /etc/systemd/system/shopapp.service

# ---------------------------------------------------------------- nginx
install -m 0644 "$SRC/files/nginx-shopapp.conf" /etc/nginx/sites-available/shopapp
ln -sf /etc/nginx/sites-available/shopapp /etc/nginx/sites-enabled/shopapp
rm -f /etc/nginx/sites-enabled/default

# ---------------------------------------------------------------- DNS baseline
if [[ -e /run/systemd/resolve/stub-resolv.conf ]] && [[ ! -L /etc/resolv.conf ]]; then
    ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf
fi
sed -i '/# tshoot-lab/d' /etc/hosts

# ---------------------------------------------------------------- start
systemctl daemon-reload
systemctl enable --now cron >/dev/null 2>&1 || true
systemctl enable shopapp >/dev/null 2>&1
systemctl reset-failed shopapp nginx >/dev/null 2>&1 || true
systemctl restart shopapp
systemctl enable nginx >/dev/null 2>&1
systemctl restart nginx

sleep 1
if curl -fs --max-time 5 http://127.0.0.1/health >/dev/null; then
    echo "[baseline] OK - http://localhost/health is healthy"
else
    echo "[baseline] WARNING - health check failed; inspect: systemctl status shopapp nginx"
fi
