#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

# "Security hardening" run by someone else: lock down /etc/shopapp.
chmod 0600 /etc/shopapp/config.ini
chown root:root /etc/shopapp/config.ini
chmod 0700 /etc/shopapp
systemctl restart shopapp || true
