# Per-command explanations for the medium labs' solution walkthroughs.
# Pipes (|) are only allowed inside `code` spans (the table parser splits on bare pipes).

CMDS = {
"m01": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `df -h /var/log/shopapp` | Filesystem-level usage (from the superblock counters). | ~90% used. |
| `du -sh /var/log/shopapp` | Adds up sizes of **visible names** (`-s` summary, `-h` human). | Only a few MB. `df` >> `du` = space is held by something with **no name**: a deleted-but-open file. |
| `lsof -nP +L1 /var/log/shopapp` | `lsof` lists open files. `+L1` = only files with link count < 1 (deleted). `-n` no DNS, `-P` no port-name lookup. | Finds `shipper-spool.log (deleted)`, `NLINK 0`, 200 MB held by PID 3120 on fd 3. |
| `ls -l /proc/3120/fd/` | Every process exposes its open fds as symlinks under `/proc/PID/fd`. | Second proof, and it gives the **fd number** needed for the in-place truncate. |
| `systemctl status 3120` | Resolves the PID to its unit. | Tells you *who* owns it (`log-shipper.service`) so you know what restart means. |
| `systemctl restart log-shipper` | Stops the holder (fd closes, blocks freed) and starts a new one. | Preferred fix: space returns and the service opens a fresh empty spool. |
| `sh -c ': > /proc/3120/fd/3'` | `:` is a no-op, `>` redirect truncates the target to 0 bytes. Goes through the fd symlink to the deleted inode. `sh -c` is needed so **root** performs the redirect (plain `sudo : > file` redirects as you). | Fix when you may **not** restart (e.g. a database): frees the space while the process runs. |
| `df -h` again | Re-reads usage. | Space is back. |
""",

"m02": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `curl -s localhost/health` | Calls the health endpoint. | `Errno 28 No space left on device` - yet it is not about space in bytes. |
| `df -h /srv/shopdata` | Block usage. | ~15% - blocks are fine. |
| `df -i /srv/shopdata` | **Inode** usage (`-i`). | 100% IUse: filesystem has 4096 inodes and all are used. Every file needs one, regardless of size. |
| `du --inodes -x /srv/shopdata | sort -n | tail -3` | `--inodes` counts files instead of bytes; `sort -n` numeric; `tail -3` biggest three. | Finds the directory eating inodes: `sessions` with ~4070. |
| `ls -lt /srv/shopdata/sessions | head` | Lists newest first (`-t`). | See that `sess_live_*` are recent and must be kept. |
| `find ... -type f -name 'sess_*' -mmin +1440 | wc -l` | `-mmin +1440` = modified more than 1440 min (24 h) ago; `wc -l` counts lines. | **Dry run**: count what would be deleted (~4000) before deleting. |
| `find ... -mmin -1440 | wc -l` | `-1440` = newer than 24 h. | Count what is protected (40 live). Both numbers must add up and match expectations. |
| `find ... -mmin +1440 -delete` | Same filter, then deletes each match. | The fix - narrow filter (type, name, age) instead of `rm -rf`. Keep `-delete` **last** in the expression. |
| `cat /etc/cron.d/shopapp-session-cleanup` | Shows the cron job file. | Root cause: cleanup line is commented out ("DISABLED during migration"). |
| `sed -i 's/^#\(17 \* \* \* \* shopapp find\)/\1/' FILE` | Removes the leading `#` using a captured group `\(...\)` and `\1`. | Re-enables the job so inodes do not fill up again. cron rereads `/etc/cron.d` by itself. |
""",

"m03": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `uptime` | Load averages for 1/5/15 min. | Load 2.1 on 2 CPUs = fully busy. |
| `nproc` | Number of CPUs. | Load only makes sense relative to CPU count. |
| `top -o %CPU` | Live process view sorted by CPU. | Two python3 processes at ~100% each. |
| `ps -eo pid,ppid,user,ni,%cpu,etime,cmd --sort=-%cpu | head -5` | `-e` all processes, `-o` choose columns, `--sort=-%cpu` highest first. | Static snapshot with PPID (who started it), NI (priority) and ELAPSED (how long). |
| `pstree -ps 4102` | Shows the process ancestry (`-p` PIDs, `-s` parents of that PID). | Answers *who keeps starting it*: `cron -> sh -> flock -> python3`. |
| `grep -r reindex /etc/cron* /var/spool/cron 2>/dev/null` | Search all cron locations; hide permission errors. | Finds `/etc/cron.d/shopapp-reindex`, the scheduler. |
| `journalctl -u cron --since "5 min ago" | grep reindex` | cron's own log. | Proves cron launches it every minute. |
| `sed -i 's/^\* \* \* \* \* root/# DISABLED INC-2003 .../' FILE` | Comments out the job and leaves a reason. | **Disable the scheduler first**, otherwise killing the process just makes cron respawn it. |
| `pgrep -af shopapp-reindex` | Lists matching PIDs (`-a` with command line, `-f` match full command line). | **Always look before you kill** - see exactly what the pattern hits. |
| `pkill -f '^/usr/bin/python3 /usr/local/bin/shopapp-reindex'` | Signals every process whose command line matches the regex. `^` anchors to the start. | Without `^` it also matches your own `sudo pkill ...` command line (which contains the same text). |
| `sleep 2; pgrep -af ... || echo "gone"` | Wait, re-check. | Confirms the kill worked; wait 2 minutes to confirm it does not respawn. |
""",

"m04": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `systemctl status cache-warmer` | State and result. | `Result: oom-kill` - killed by the OOM killer, not a normal crash. |
| `systemctl show -p NRestarts cache-warmer` | Counter of auto-restarts. | Proof of a crash loop and how fast it climbs. |
| `journalctl -u cache-warmer -n 20` | Unit log. | Shows `max_mb=0 (UNLIMITED)` and the oom-kill message. |
| `journalctl -k --since "5 min ago" | grep -iE 'oom|killed process'` | `-k` = kernel messages only. | The kernel's view: `constraint=CONSTRAINT_MEMCG` means a **cgroup** limit was hit, not host memory. |
| `free -m` | Memory in MB. | Host still has plenty of free RAM - confirms it is a per-service limit. |
| `systemctl show -p MemoryMax cache-warmer` | Reads the cgroup limit. | `160M` - the unit's own ceiling. |
| `watch -n1 'systemctl show -p MemoryCurrent cache-warmer'` | Re-runs a command every second. | A straight line up ~20 MB/s = unbounded growth, not a one-time spike. |
| `cat /etc/cache-warmer.conf` | Config file. | `max_mb = 0` (0 = unlimited) left over from load test LT-88. |
| `sed -i 's/^max_mb = 0/max_mb = 64/' ...` | Restores the original value. | Fixes the **cause**. Raising MemoryMax only delays the kill. |
| `systemctl restart cache-warmer; sleep 15; systemctl show -p NRestarts -p MemoryCurrent ...` | Restart, wait, re-measure. | Memory flat at ~70-80 MB and restart counter stops = fixed. |
""",

"m05": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `ls -l /srv/backups` | Output folder of the job. | Empty - the backup is not being produced. |
| `journalctl -u cron --since "10 min ago"` | cron daemon log. | No lines for this job at all = cron is not even *seeing* it. |
| `ls -l /etc/cron.d/` | Names and modes of cron files. | Name `shopapp-backup.cron` contains a dot; mode is `rw-rw-rw-`. Two clues for two faults. |
| `mv /etc/cron.d/shopapp-backup.cron /etc/cron.d/shopapp-backup` | Renames the file. | Debian/Ubuntu cron ignores names with a `.` in `/etc/cron.d` (silently). |
| `chown root:root` + `chmod 0644` | Fix owner and mode. | cron logs `INSECURE MODE (group/other writable)` and refuses files that anyone can edit - otherwise any user could run code as root. |
| `journalctl -u cron --since "2 min ago"` (after each fix) | Re-read the log a minute later. | Each fix reveals the **next** fault. `CMD (...)` = cron now runs it. |
| `/usr/local/bin/shopapp-backup` (run by hand as root) | Executes the job like cron would. | The output is discarded by cron (`No MTA installed`), so run it yourself to see the error. |
| `ls -l /usr/local/bin/shopapp-backup` | Mode of the script. | `-rw-r--r--`: no execute bit. |
| `chmod 0755 /usr/local/bin/shopapp-backup` | Adds execute. | Fault 3 fixed. |
| `journalctl -t shopapp-backup -n 3` | Filter by syslog **identifier** (`-t`). | See what the script itself logged. |
| `tar -tzvf /srv/backups/shopapp-*.tar.gz | head` | `-t` list, `-z` gzip, `-v` verbose, `-f` file. | A backup you never read back is not a backup - verify the archive is valid and has content. |
""",

"m06": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `uptime` | Load average. | 6.8 on 2 CPUs - but is the CPU really busy? |
| `vmstat 1 5` | Virtual memory stats, 1 s interval, 5 samples. | Key columns: `si/so` (swap in/out, KB/s) in the thousands = swap storm; `b` blocked tasks; `wa` CPU waiting on IO; tiny `cache`. CPU is not busy, it is **waiting for disk**. |
| `free -m` | RAM and swap usage in MB. | `available` ~18 MB: nothing left without swapping. |
| `ps -eo pid,user,rss,cmd --sort=-rss | head` | `rss` = resident memory. Sorted by biggest. | Ten `report-builder` workers, ~200 MB each. |
| `grep VmSwap /proc/[0-9]*/status | sort -k2 -n | tail -3` | Reads swap use of every process; sorts by the number in column 2. | Who has been pushed to swap. |
| `systemctl status report-builder` | Shows a cgroup memory summary. | `Memory: 1.9G (swap: 790M)` for one service. |
| `ls -lt /etc/sysctl.d/ /etc/*.conf | head` | Newest changed config files first. | Finds what CHG-552 touched. |
| `cat /etc/sysctl.d/60-batch-tuning.conf` | Kernel tunables applied at boot. | `vm.swappiness = 100` - swap application memory eagerly. |
| `cat /etc/report-builder.conf` | App config. | `workers = 10` (was 2): 10 x 200 MB > RAM. |
| `sed -i 's/^workers *=.*/workers = 2/' FILE` | Restore the old value. | Fixes the memory demand. |
| `rm /etc/sysctl.d/60-batch-tuning.conf` | Removes persistent tuning. | So it does not come back at reboot. |
| `sysctl -w vm.swappiness=60` | Changes the kernel parameter **now** (runtime only). | Immediate effect; `rm` above makes it permanent. |
| `sysctl --system` | Re-applies all sysctl files in order. | Confirms nothing else sets swappiness. |
| `swapoff -a && swapon -a` | Disable and re-enable all swap (forces pages back into RAM). | Optional cleanup - **only** if there is enough free RAM, or it can OOM. |
""",

"m07": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `journalctl -u queue-dispatcher -n 5` | Unit log. | `fork failed: Errno 11 (EAGAIN)`: cannot create processes. |
| `ps -eo stat | grep -c '^Z'` | Prints process state; `grep -c` counts lines starting with `Z` (zombie). | ~149 zombies. |
| `ps -eo pid,ppid,stat,cmd | awk '$3 ~ /Z/' | head -3` | `awk` keeps lines where column 3 (STAT) contains Z. | All zombies share the same PPID 6100 - one parent is the culprit. |
| `kill -9 ZOMBIE` (useless) | Sends SIGKILL. | A zombie is already dead; only its process-table entry remains until the parent calls `wait()`. |
| `systemctl status queue-dispatcher | grep Tasks` | Shows cgroup task count and limit. | `Tasks: 150 (limit: 150)` - zombies still occupy PIDs in the cgroup. |
| `systemctl show -p TasksMax queue-dispatcher` | Reads the limit. | Explains why `fork()` returns EAGAIN. |
| `pstree -p 6100` | Process tree of the parent. | See its children. |
| `systemctl cat queue-dispatcher | grep ExecStart` | What the service runs. | Find the program and its config. |
| `cat /etc/queue-dispatcher.conf` | App config. | `reap_children = false`, set while debugging INC-2190 and never reverted. |
| `sed -i 's/^reap_children *=.*/reap_children = true/' FILE` | Flip it back. | Real fix. |
| `systemctl restart queue-dispatcher` | Restart parent. | Clears existing zombies (orphans are re-parented to init and reaped). |
""",

"m08": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `df -h /var/log/shopapp` and `ls -lh /var/log/shopapp/` | Usage and file sizes. | ~80% used, `app.log` ~190 MB and never rotated. |
| `cat /etc/logrotate.d/shopapp` | The rotation rule. | Read what it is supposed to do. |
| `logrotate -d /etc/logrotate.d/shopapp` | `-d` = debug / **dry run**: shows what it would do and errors, changes nothing. | Reveals why it silently skips: `parent directory has insecure permissions`. |
| `ls -ld /var/log/shopapp` | `-d` shows the directory itself, not its contents. | Group-writable (`drwxrwxr-x`). logrotate runs as root and will not work in a directory others can write (symlink attacks). |
| `chmod 0755 /var/log/shopapp` and/or `su shopapp shopapp` in the rule | Remove group write, or tell logrotate which user/group to use. | Fix 1. |
| `logrotate -v -f /etc/logrotate.d/shopapp` | `-f` force rotation now, `-v` verbose. | Tests it for real instead of waiting for the timer. |
| `lsof +L1 /var/log/shopapp` | Open deleted files. | Fault 2: `app.log.1 (deleted)` still held by python - `compress` deleted the renamed file while the app kept writing to it. |
| `copytruncate` (in the rule) | Copies the file, then truncates the original in place. | App keeps the same inode and fd, so no signal or restart is needed. Cost: a few lines can be lost; needs free space for a full copy. |
| `systemctl restart shopapp` | Closes the old fd. | Frees the deleted file's space. |
| `logrotate -d ... 2>&1 | grep -i error` | Dry run, filter errors. | Verify nothing is reported. |
| `curl -s localhost/ >/dev/null; ls -l app.log` | Generate traffic, check size. | The file grows again = app writes to the right file. |
""",

"m09": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `curl -v --resolve shop.lab.internal:443:127.0.0.1 --cacert CA https://shop.lab.internal/` | `--resolve` forces name -> IP without DNS; `--cacert` trusts our private CA. | Reproduces exactly what a client sees: `certificate has expired`. |
| `openssl s_client -connect 127.0.0.1:443 -servername NAME </dev/null 2>/dev/null | openssl x509 -noout -subject -dates` | Connects with TLS, grabs the served cert, prints subject and validity. `</dev/null` ends the session; `-servername` sets SNI. | Shows what is **actually served**: expired 3 days ago. |
| `ls -l /etc/ssl/shopapp/` | Files and modes. | Old and new cert/key pairs exist. Also `shop-2026-renewal.key` is world-readable. |
| `for c in /etc/ssl/shopapp/shop-*.crt; do openssl x509 -in "$c" -noout -enddate; done` | Loop: print expiry of each cert. | Find which cert is still valid: `shop-2026.crt`. |
| `nginx -T 2>/dev/null | grep ssl_certificate` | `-T` = test and **dump the full effective config**. | Which cert/key nginx really uses (still the 2025 files) - renewal never got deployed. |
| `openssl x509 -in CERT -noout -pubkey | sha256sum` | Hash of the cert's public key. | Compare with the key's public key. |
| `openssl pkey -in KEY -pubout | sha256sum` | Hash of the public key derived from a private key. | Equal hashes = this key belongs to this cert. Only `shop-2026-renewal.key` matches. |
| `chmod 600 shop-2026-renewal.key` | Owner read/write only. | Private keys must not be readable by others. |
| `sed -i 's#shop-2025.crt#shop-2026.crt#; s#shop-2025.key#shop-2026-renewal.key#' FILE` | Two substitutions in one run. | Point nginx at the new pair. |
| `nginx -t && systemctl reload nginx` | Validate, then reload without dropping connections. | A mismatched key would fail here with `key values mismatch` instead of causing an outage. |
| `openssl x509 -noout -checkend 2592000` | Exits 0 if the cert is still valid in 2592000 s (30 days). | Monitoring-style check for the future. |
""",

"m10": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `curl -s localhost/health` | Local test. | Works - **misleading**: loopback does not use the network path the monitor uses. |
| `ip netns exec mon-ns curl -sv --max-time 5 http://10.210.0.1/health` | Runs curl inside the monitoring network namespace (simulated remote host). `--max-time 5` limits the wait. | Test **as the user**, from their side. `Connection timed out` = packets dropped. |
| `tcpdump -ni h-mon port 80` | Packet capture on interface `h-mon`; `-n` no name lookup. | SYNs arrive, nothing is answered: traffic reaches the host but something drops it. |
| `iptables -L INPUT -n -v --line-numbers` | Lists firewall rules with hit counters (`-v`) and numbers. | `DROP ... 10.210.0.0/24 dpt:80` with a counter that increases on every probe = this rule is the one. |
| `iptables -I INPUT 1 -s 10.210.0.2/32 -p tcp --dport 80 -j ACCEPT` | Inserts an ACCEPT at position 1, for just the probe host. | Narrow exception: keep the security block, allow monitoring. |
| `iptables -D INPUT NUM` | Deletes rule number NUM. | Alternative if the block was a mistake. |
| `curl` again from `mon-ns` | Re-test. | Error changed to `Connection refused` = progress: packets arrive, nobody listens on that address. |
| `ss -ltnp | grep ':80 '` | Listening sockets on port 80. | nginx listens only on `127.0.0.1:80` and `[::1]:80`. |
| `nginx -T | grep -n listen` | Effective config with line numbers. | Shows `listen 127.0.0.1:80` from CHG-610. |
| `sudoedit ...` + `listen 80;` + `listen [::]:80;` | Binds to all addresses. | The fix. |
| `nginx -t && systemctl reload nginx` | Validate then apply. | Safe change. |
| `ss -ltn | grep ':80 '` | Verify. | `0.0.0.0:80` and `[::]:80`. |
""",
}
