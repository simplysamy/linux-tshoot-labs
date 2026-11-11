#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
S=$LAB_STATE_DIR
systemctl disable --now metrics-scraper metrics-exporter >/dev/null 2>&1 || true
rm -rf /etc/systemd/system/metrics-scraper.service /etc/systemd/system/metrics-exporter.service \
       /etc/systemd/system/metrics-scraper.service.d /etc/systemd/system/metrics-exporter.service.d \
       /usr/local/bin/metrics-scraper /usr/local/bin/metrics-exporter /etc/metrics-scraper.conf \
       /etc/sysctl.d/70-memory-saving.conf
systemctl daemon-reload
while iptables -S INPUT | grep -q 'SEC-099'; do
    rule=$(iptables -S INPUT | grep 'SEC-099' | head -1)
    eval "iptables ${rule/-A /-D }"
done
if [[ -f $S/h08-max.orig ]]; then
    sysctl -qw net.netfilter.nf_conntrack_max="$(cat "$S/h08-max.orig")" || true
    rm -f "$S/h08-max.orig"
fi
restore_baseline
