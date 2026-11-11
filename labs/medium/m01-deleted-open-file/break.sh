#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

SPOOL=/var/log/shopapp/shipper-spool.log

cat > /usr/local/bin/log-shipper <<'EOF'
#!/usr/bin/env bash
# Pretend log shipper: keeps its spool file open forever and appends to it.
exec 3>>/var/log/shopapp/shipper-spool.log
while true; do
    echo "$(date '+%F %T') shipped batch ok" >&3
    sleep 5
done
EOF
chmod 0755 /usr/local/bin/log-shipper

cat > /etc/systemd/system/log-shipper.service <<'EOF'
[Unit]
Description=Log shipper (forwards shopapp logs to central logging)
RequiresMountsFor=/var/log/shopapp

[Service]
User=shopapp
ExecStart=/usr/local/bin/log-shipper
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now log-shipper >/dev/null 2>&1
sleep 1

# The shipper's upstream was down for a day, so the spool grew huge...
yes "$(date '+%F %T') QUEUED event=checkout user=4411 cart=88 status=pending_forward" \
    | head -c 200M >> "$SPOOL" || true   # yes gets SIGPIPE when head stops; that is expected
sync

# ...and someone "fixed" the disk alert with rm.
rm -f "$SPOOL"
