# M01 - Solution

> Long commands below are built up short-first (`# 1.`, `# 2.` ...). Each rung adds one flag;
> the last rung is what the lab uses. The README **Warm-up** explains every flag from scratch.

## 1. See the mismatch

```bash
df -h /var/log/shopapp          # ~90% used
sudo du -sh /var/log/shopapp    # only a few MB
```

## 2. Find the hidden space

```bash
sudo lsof /var/log/shopapp               # 1. who has files open there
sudo lsof +L1 /var/log/shopapp           # 2. + only files with link count < 1 (deleted)
sudo lsof -nP +L1 /var/log/shopapp       # 3. + no DNS/port-name lookups (faster)
# COMMAND   PID    USER  FD  TYPE DEVICE  SIZE/OFF NLINK NODE NAME
# log-shipp 3120 shopapp  3w  REG    7,0 209715200     0   14 /var/log/shopapp/shipper-spool.log (deleted)
```

`NLINK 0` = no names left. `SIZE/OFF` = 200 MB still held by PID 3120 on fd 3.

```bash
ls -l /proc/3120/fd/
# 3 -> /var/log/shopapp/shipper-spool.log (deleted)
systemctl status 3120 --no-pager     # log-shipper.service
```

## 3a. Fix - restart the holder (preferred when allowed)

```bash
sudo systemctl restart log-shipper
df -h /var/log/shopapp       # space is back
```

The service opens a new, empty spool file.

## 3b. Fix - when you may NOT restart (e.g. a database)

Truncate the deleted file through the fd. The process keeps running:

```bash
sudo sh -c ': > /proc/3120/fd/3'
df -h /var/log/shopapp
```

The fd stays open with size 0. `lsof +L1` still lists it (size 0) until the
process restarts. Restart it in the next maintenance window.
The checker wants zero deleted spool files, so do 3a at some point.

## Root cause and prevention

| | |
|---|---|
| Root cause | Spool file deleted with `rm` while log-shipper still had it open; inode and blocks stay allocated |
| Prevent | Use `truncate -s 0` for live logs; logrotate with `copytruncate` or a `postrotate` signal; alert on spool size |
