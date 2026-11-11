#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
S=$LAB_STATE_DIR
tz=Etc/UTC
[[ -s $S/e07-tz.orig ]] && tz=$(cat "$S/e07-tz.orig")
timedatectl set-timezone "$tz"
timedatectl set-ntp true || true
# undo the 7-minute drift unless NTP has already corrected it
if [[ $(timedatectl show -p NTPSynchronized --value) != yes ]]; then
    date -s "$(date -d '+7 minutes' '+%F %T')" >/dev/null 2>&1 || true
fi
rm -f "$S/e07-tz.orig"
restore_baseline
