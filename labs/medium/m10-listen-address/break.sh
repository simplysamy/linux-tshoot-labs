#!/usr/bin/env bash
# Topology: [mon-ns] mon0 10.210.0.2/24 ---- h-mon 10.210.0.1/24 [ VM ]
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

ip netns del mon-ns 2>/dev/null || true
ip link del h-mon 2>/dev/null || true
ip netns add mon-ns
ip link add h-mon type veth peer name mon0
ip link set mon0 netns mon-ns
ip addr add 10.210.0.1/24 dev h-mon
ip link set h-mon up
ip -n mon-ns addr add 10.210.0.2/24 dev mon0
ip -n mon-ns link set mon0 up
ip -n mon-ns link set lo up

# CHG-610 "hardening": nginx only on loopback
sed -i \
    -e 's|^\(\s*\)listen 80 default_server;|\1listen 127.0.0.1:80 default_server;   # CHG-610 hardening: loopback only|' \
    -e 's|^\(\s*\)listen \[::\]:80 default_server;|\1listen [::1]:80 default_server;|' \
    /etc/nginx/sites-available/shopapp
nginx -t >/dev/null 2>&1
systemctl restart nginx

# SEC-118: block a "scanner subnet" - which is the monitoring network
iptables -I INPUT -s 10.210.0.0/24 -p tcp --dport 80 -m comment --comment "SEC-118 block scanner subnet" -j DROP
