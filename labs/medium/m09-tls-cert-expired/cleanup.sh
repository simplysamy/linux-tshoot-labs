#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
rm -f /etc/nginx/sites-enabled/shopapp-tls /etc/nginx/sites-available/shopapp-tls
rm -rf /etc/ssl/shopapp "$LAB_STATE_DIR/m09-ca"
restore_baseline
