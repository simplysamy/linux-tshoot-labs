#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

cat > /usr/local/bin/shopapp-reindex <<'EOF'
#!/usr/bin/env python3
# "Search reindex" job. BUG: a retry loop with no sleep and no exit -> burns every CPU.
import multiprocessing, os

def worker(n):
    x = 0
    while True:          # retry forever, no backoff
        x = (x * 31 + n) % 1000003

if __name__ == "__main__":
    procs = [multiprocessing.Process(target=worker, args=(i,)) for i in range(os.cpu_count() or 2)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
EOF
chmod 0755 /usr/local/bin/shopapp-reindex

# Every minute; flock stops duplicates, so if you kill it, it is back within 60s.
cat > /etc/cron.d/shopapp-reindex <<'EOF'
# search reindex - owner: search team
* * * * * root /usr/bin/flock -n /run/shopapp-reindex.lock /usr/local/bin/shopapp-reindex >/dev/null 2>&1
EOF
chmod 0644 /etc/cron.d/shopapp-reindex

# start one now so the student does not wait for cron
setsid /usr/bin/flock -n /run/shopapp-reindex.lock /usr/local/bin/shopapp-reindex >/dev/null 2>&1 < /dev/null &
disown || true
sleep 2
