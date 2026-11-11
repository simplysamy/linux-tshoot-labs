#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"

img=$(awk '$2 == "/srv/shopdata" && $1 !~ /^#/ {print $1}' /etc/fstab | head -1)
if [[ -n $img && -f $img ]]; then pass "fstab source for /srv/shopdata exists ($img)"; else fail "fstab source for /srv/shopdata is '${img:-missing}' - does not exist"; fi

for u in $(systemctl show -p User --value shopapp) $(systemctl show -p Group --value shopapp); do
    if getent passwd "$u" >/dev/null || getent group "$u" >/dev/null; then
        pass "unit user/group '$u' exists"
    else
        fail "unit references user/group '$u' that does not exist"
    fi
done

info "Simulating a reboot of the app stack (stop app, unmount, daemon-reload, start app)..."
systemctl stop shopapp
umount /srv/shopdata 2>/dev/null
systemctl daemon-reload
systemctl start shopapp 2>/dev/null
sleep 2

check "srv-shopdata.mount is active after 'reboot'" systemctl is-active --quiet srv-shopdata.mount
check "shopapp is active after 'reboot'" systemctl is-active --quiet shopapp
owner=$(ps -o user= -p "$(systemctl show -p MainPID --value shopapp)" 2>/dev/null | tr -d ' ')
[[ -n $owner && $owner != root ]] && pass "shopapp runs as '$owner' (not root)" || fail "shopapp runs as '${owner:-?}'"
check "data files are visible (catalog/products.db)" test -f /srv/shopdata/catalog/products.db
[[ $(http_code http://127.0.0.1/health) == 200 ]] && pass "/health returns 200" || fail "/health is not 200"
finish_verify
