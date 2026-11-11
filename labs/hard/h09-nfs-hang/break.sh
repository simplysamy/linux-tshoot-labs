#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

command -v exportfs >/dev/null || { red "nfs-kernel-server missing - run: sudo bash setup/install-base.sh"; exit 1; }

# the "NAS" is a local NFS server on its own address
ip link add nas0 type dummy 2>/dev/null || true
ip addr replace 10.240.0.10/32 dev nas0
ip link set nas0 up
echo "10.240.0.10 nas01.lab.internal nas01   # tshoot-lab" >> /etc/hosts

mkdir -p /srv/nfs/reports
chmod 0777 /srv/nfs/reports
sed -i '/# tshoot-lab/d' /etc/exports 2>/dev/null || true
echo "/srv/nfs/reports 10.240.0.0/24(rw,sync,no_subtree_check) 127.0.0.1(rw,sync,no_subtree_check)   # tshoot-lab" >> /etc/exports
systemctl start nfs-server
exportfs -ra

mkdir -p /mnt/reports
sed -i '\# /mnt/reports #d' /etc/fstab
echo "nas01.lab.internal:/srv/nfs/reports /mnt/reports nfs4 hard,timeo=50,retrans=2 0 0" >> /etc/fstab
systemctl daemon-reload
mount /mnt/reports

cat > /usr/local/bin/report-export <<'EOF'
#!/bin/bash
# nightly export of shop reports to the NAS
set -euo pipefail
f=/mnt/reports/export-$(date +%Y%m%d-%H%M%S).csv
{ echo "sku,name,price"; tail -n +2 /srv/shopdata/catalog/products.db; } > "$f"
sync "$f"
EOF
chmod 0755 /usr/local/bin/report-export
/usr/local/bin/report-export
echo "* * * * * root /usr/local/bin/report-export" > /etc/cron.d/report-export

# SEC-410: egress lockdown cuts the path to the NAS
iptables -I OUTPUT -d 10.240.0.10 -p tcp --dport 2049 -m comment --comment "SEC-410 egress lockdown" -j DROP

# monitoring agents and the export start piling up
for _ in 1 2 3; do setsid nohup df -h >/dev/null 2>&1 < /dev/null & done
setsid nohup /usr/local/bin/report-export >/dev/null 2>&1 < /dev/null &
info "Waiting 20s for processes to get stuck ..."
sleep 20
