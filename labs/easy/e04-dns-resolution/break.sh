#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

# Save what resolv.conf was (normally a symlink to systemd-resolved's stub file).
if [[ -L /etc/resolv.conf ]]; then
    readlink /etc/resolv.conf > "$LAB_STATE_DIR/e04-resolv-link"
else
    backup_file /etc/resolv.conf
fi

# Fault 1: someone "fixed DNS" by hand with an old, dead resolver.
rm -f /etc/resolv.conf
cat > /etc/resolv.conf <<'EOF'
# managed manually - do not touch (ops 2019)
nameserver 10.255.255.53
options timeout:2 attempts:1
EOF

# Fault 2: a stale hosts entry from an old migration test.
echo "203.0.113.77   example.com www.example.com   # tshoot-lab migration test" >> /etc/hosts
