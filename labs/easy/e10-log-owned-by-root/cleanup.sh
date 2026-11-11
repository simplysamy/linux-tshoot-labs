#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
rm -f /var/log/shopapp/app.log.old
# install-base re-owns *.log files, resets dir mode and reinstalls the unit
restore_baseline
