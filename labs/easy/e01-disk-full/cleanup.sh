#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
rm -rf /var/log/shopapp/debug-trace.log /var/log/shopapp/archive
restore_baseline
