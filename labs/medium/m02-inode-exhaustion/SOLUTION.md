# M02 - Solution

> Long commands below are built up short-first (`# 1.`, `# 2.` ...). Each rung adds one flag;
> the last rung is what the lab uses. The README **Warm-up** explains every flag from scratch.

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
sudo du --inodes /srv/shopdata                          # 1. file count per directory
sudo du --inodes -x /srv/shopdata | sort -n             # 2. -x one filesystem, sort by count
sudo du --inodes -x /srv/shopdata | sort -n | tail -3   # 3. only the 3 biggest
# 4070  /srv/shopdata/sessions
ls /srv/shopdata/sessions | head
ls -lt /srv/shopdata/sessions | head      # newest first: sess_live_* are recent
```

## 3. Dry run, then delete only old sessions

```bash
# older than 24h (1440 minutes), only regular files named sess_*
sudo find /srv/shopdata/sessions -type f                                    # 1. all files
sudo find /srv/shopdata/sessions -type f -name 'sess_*'                     # 2. + name pattern
sudo find /srv/shopdata/sessions -type f -name 'sess_*' -mmin +1440         # 3. + older than 1440 min (24 h)
sudo find /srv/shopdata/sessions -type f -name 'sess_*' -mmin +1440 | wc -l     # 4. count them (dry run): ~4000
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
