#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
rm -f /srv/shopdata/trace.log
restore_baseline     # removes shopapp.service.d and restores config.ini
