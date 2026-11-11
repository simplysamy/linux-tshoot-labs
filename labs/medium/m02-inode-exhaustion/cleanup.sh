#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
find /srv/shopdata/sessions -type f -delete 2>/dev/null || true
rm -f /etc/cron.d/shopapp-session-cleanup
restore_baseline
