#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

U=/etc/systemd/system/shopapp.service
systemctl disable shopapp >/dev/null 2>&1
# "template cleanup" dropped everything from [Install] on
sed -i '/^\[Install\]/,$d' "$U"
sed -i -e :a -e '/^\n*$/{$d;N;ba' -e '}' "$U"   # trim trailing blank lines
systemctl daemon-reload
# on-call started it by hand after the reboot
systemctl start shopapp
