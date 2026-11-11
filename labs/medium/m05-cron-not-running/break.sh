#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

mkdir -p /srv/backups
rm -f /srv/backups/shopapp-*.tar.gz

cat > /usr/local/bin/shopapp-backup <<'EOF'
#!/usr/bin/env bash
# Back up shopapp config + catalog. Runs from cron.
set -euo pipefail
ts=$(date +%F-%H%M)
tar -czf "/srv/backups/shopapp-$ts.tar.gz" /etc/shopapp /srv/shopdata/catalog 2>/dev/null
find /srv/backups -name 'shopapp-*.tar.gz' -mtime +7 -delete
logger -t shopapp-backup "backup ok: /srv/backups/shopapp-$ts.tar.gz"
EOF
chmod 0644 /usr/local/bin/shopapp-backup          # fault 3: not executable

# For the lab the "nightly" job runs every minute so you can see results quickly.
cat > /etc/cron.d/shopapp-backup.cron <<'EOF'
# shopapp backup - every minute in the lab (in prod: 30 2 * * *)
* * * * * root /usr/local/bin/shopapp-backup
EOF
chmod 0666 /etc/cron.d/shopapp-backup.cron        # fault 2: group/world writable
# fault 1: the file name contains a dot -> cron ignores it entirely
