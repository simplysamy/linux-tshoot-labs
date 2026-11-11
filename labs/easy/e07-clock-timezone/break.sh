#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

S=$LAB_STATE_DIR
timedatectl show -p Timezone --value > "$S/e07-tz.orig"

# "customised image": local timezone, NTP off, clock 7 minutes slow
timedatectl set-timezone America/Los_Angeles
timedatectl set-ntp false
systemctl stop systemd-timesyncd chrony chronyd 2>/dev/null || true
date -s "$(date -d '-7 minutes' '+%F %T')" >/dev/null

# the app picks up the new zone at its next start (as after a reboot)
systemctl restart shopapp
sleep 1
curl -s -o /dev/null --max-time 3 http://127.0.0.1/ || true
