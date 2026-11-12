# M08 - Solution

> Long commands below are built up short-first (`# 1.`, `# 2.` ...). Each rung adds one flag;
> the last rung is what the lab uses. The README **Warm-up** explains every flag from scratch.

## 1. Confirm

```bash
df -h /var/log/shopapp                    # ~80%
ls -lh /var/log/shopapp/                  # app.log ~190M, never rotated
cat /etc/logrotate.d/shopapp
```

## 2. Dry run

```bash
sudo logrotate -d /etc/logrotate.d/shopapp
# error: skipping "/var/log/shopapp/app.log" because parent directory has insecure
# permissions (It's world writable or writable by group which is not "root") Set "su"
# directive in config file to tell logrotate which user/group should be used for rotation.
ls -ld /var/log/shopapp
# drwxrwxr-x 3 shopapp shopapp ... /var/log/shopapp      <- group-writable (last week's change)
```

Logrotate runs as root. In a directory that non-root users can write, a user could
swap files for symlinks and make root overwrite anything. So logrotate refuses.

Fix (either):

```bash
sudo chmod 0755 /var/log/shopapp      # read access for a group needs r-x, not w
# and/or add to the rule:   su shopapp shopapp
```

## 3. First real rotation - and the second problem

```bash
sudo logrotate -v -f /etc/logrotate.d/shopapp
for i in 1 2 3; do curl -s localhost/ >/dev/null; done
ls -l /var/log/shopapp/
# -rw-r----- 1 shopapp shopapp     0 ... app.log          <- stays empty!
# -rw-r----- 1 shopapp shopapp  210K ... app.log.1.gz
sudo lsof +L1 /var/log/shopapp
# python3 7001 shopapp 3w REG 7,0 199M 0 12 /var/log/shopapp/app.log.1 (deleted)
df -h /var/log/shopapp                # still full
```

`create` renamed `app.log` -> `app.log.1` (same inode, the app keeps writing there),
`compress` then gzipped it and **deleted** `app.log.1`. The app writes to a deleted file:
space is not freed and new log lines are invisible.

## 4. Fix the rule

shopapp has no "reopen log" signal, so use `copytruncate` (copy the content, then
truncate the original in place - same inode, the app's fd stays valid):

```
/var/log/shopapp/*.log {
    su shopapp shopapp
    daily
    maxsize 20M
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

(Alternative: keep `create` and add `postrotate systemctl restart shopapp endscript`.
`copytruncate` can lose a few lines written between copy and truncate - acceptable here.)

Free the space held by the deleted file: `sudo systemctl restart shopapp`.

Trap: `copytruncate` needs free space for a **full copy** of the file. If you switch to
`copytruncate` while the 190 MB `app.log` is still there, rotation fails with
`No space left on device`. Get rid of the big file first (rotate once with `create` and
restart, or archive it elsewhere and truncate), then rely on `maxsize` to keep files small.

## 5. Verify

```bash
sudo logrotate -d /etc/logrotate.d/shopapp 2>&1 | grep -i error   # nothing
sudo logrotate -v -f /etc/logrotate.d/shopapp
curl -s localhost/ >/dev/null; ls -l /var/log/shopapp/app.log   # grows
sudo lsof +L1 /var/log/shopapp                                  # nothing
sudo ./labctl.sh check m08
```

`maxsize` + the daily `logrotate.timer` keeps the file small. For big log bursts run
logrotate more often (hourly timer).

## Root cause and prevention

| | |
|---|---|
| Root cause | (1) group-writable log dir -> logrotate skipped the file; (2) `create`+`compress` with an app that never reopens its log -> writes to a deleted file |
| Fix | Dir 0755 / `su`, `copytruncate` + `delaycompress` + `maxsize`, restart app |
| Prevent | Test new rules with `logrotate -d` and one forced run; check `lsof +L1` after rotation; alert on log volume at 80% |
