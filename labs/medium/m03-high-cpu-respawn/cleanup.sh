#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
rm -f /etc/cron.d/shopapp-reindex
pkill -f /usr/local/bin/shopapp-reindex || true
sleep 1
pkill -9 -f /usr/local/bin/shopapp-reindex || true
rm -f /usr/local/bin/shopapp-reindex /run/shopapp-reindex.lock
restore_baseline
