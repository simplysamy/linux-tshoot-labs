#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

# shoptools "2.0" installs into /opt and only fixes PATH for login shells
install -d /opt/shoptools/bin
cat > /opt/shoptools/bin/shopctl <<'EOF'
#!/usr/bin/env bash
# shoptools 2.0 - shop admin CLI
case ${1:-} in
    stats)
        echo "products=$(($(wc -l < /srv/shopdata/catalog/products.db) - 1))"
        echo "sessions=$(find /srv/shopdata/sessions -type f | wc -l)"
        ;;
    *) echo "usage: shopctl stats" >&2; exit 1 ;;
esac
EOF
chmod 0755 /opt/shoptools/bin/shopctl
echo 'export PATH="$PATH:/opt/shoptools/bin"' > /etc/profile.d/shoptools.sh

cat > /usr/local/bin/shopapp-report <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
out=/srv/backups/shop-report.txt
{
    echo "report generated $(date -Is)"
    shopctl stats
} > "$out.tmp"
mv "$out.tmp" "$out"
EOF
chmod 0755 /usr/local/bin/shopapp-report

cat > /etc/systemd/system/shopapp-report.service <<'EOF'
[Unit]
Description=ShopApp stock report

[Service]
Type=oneshot
ExecStart=/usr/local/bin/shopapp-report
EOF
cat > /etc/systemd/system/shopapp-report.timer <<'EOF'
[Unit]
Description=ShopApp stock report every 5 minutes

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
EOF

# an old report from "before the upgrade"
echo "report generated $(date -Is -d '-3 days')" > /srv/backups/shop-report.txt
echo "products=0" >> /srv/backups/shop-report.txt
touch -d '-3 days' /srv/backups/shop-report.txt

systemctl daemon-reload
systemctl enable --now shopapp-report.timer >/dev/null 2>&1
systemctl start shopapp-report.service 2>/dev/null || true
