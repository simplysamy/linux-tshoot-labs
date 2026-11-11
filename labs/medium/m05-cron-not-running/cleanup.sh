#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
grep -lsr shopapp-backup /etc/cron.d | xargs -r rm -f || true
rm -f /usr/local/bin/shopapp-backup /srv/backups/shopapp-*.tar.gz
restore_baseline
