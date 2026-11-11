# M02 - Solution

## 1. Confirm and look at both kinds of space

```bash
curl -s localhost/health            # ERROR: [Errno 28] No space left on device
df -h /srv/shopdata                 # Use% ~15%  -> blocks are fine
df -i /srv/shopdata
# Filesystem  Inodes IUsed IFree IUse% Mounted on
# /dev/loop1    4096  4096     0  100% /srv/shopdata    <-- out of inodes
```

## 2. Where are the files?

```bash
sudo du --inodes -x /srv/shopdata | sort -n | tail -3
# 4070  /srv/shopdata/sessions
ls /srv/shopdata/sessions | head
ls -lt /srv/shopdata/sessions | head      # newest first: sess_live_* are recent
```

## 3. Dry run, then delete only old sessions

```bash
# older than 24h (1440 minutes), only regular files named sess_*
sudo find /srv/shopdata/sessions -type f -name 'sess_*' -mmin +1440 | wc -l     # ~4000
sudo find /srv/shopdata/sessions -type f -name 'sess_*' -mmin -1440 | wc -l     # 40 live
sudo find /srv/shopdata/sessions -type f -name 'sess_*' -mmin +1440 -delete
df -i /srv/shopdata
curl -s localhost/health            # OK
```

## 4. Why did it happen? Fix the cause

```bash
ls /etc/cron.d/
cat /etc/cron.d/shopapp-session-cleanup
# #17 * * * * shopapp find ...     <-- commented out ("DISABLED during migration")
sudo sed -i 's/^#\(17 \* \* \* \* shopapp find\)/\1/' /etc/cron.d/shopapp-session-cleanup
cat /etc/cron.d/shopapp-session-cleanup
```

cron reads `/etc/cron.d` automatically; no restart needed.

## Root cause and prevention

| | |
|---|---|
| Root cause | Session cleanup cron disabled during a migration and never re-enabled; session files used all 4096 inodes |
| Prevent | Alert on inode usage (`node_filesystem_files_free`); track "temporary" changes in tickets with an end date; size inode count for small-file workloads (`mkfs.ext4 -i` / `-N`) or use XFS (dynamic inodes) |
