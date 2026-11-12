# Hand-written study content for the medium labs. Same format as content_easy.py.

CONTENT = {
"m01": dict(
explain="""
**A file is an inode; a name is just a pointer to it.** `rm` (unlink) deletes a **directory entry** and decrements the inode's *link count*. The inode and its data blocks are freed only when the link count is 0 **and** no process still has the file open.

`log-shipper` had `shipper-spool.log` open (fd 3, write). After `rm`: link count 0, but an open file description exists -> 200 MB stays allocated, invisible to any directory listing.

**Why `df` and `du` disagree:**

- `du` adds up files it can reach **by name**
- `df` asks the filesystem how many blocks are in use

A big gap = space used by something without a name (deleted-but-open files, or data hidden under a mount point).

**Find it:** `sudo lsof -nP +L1` (open files with link count < 1) or `find /proc/*/fd -lname '*(deleted)'`.

**Free it:**

- restart the holder (closes the fd), or
- if you may not restart: `: > /proc/<PID>/fd/<FD>` truncates the deleted file through the fd.

**Better habit:** on a live log use `truncate -s 0 file` instead of `rm`.
""",
mcq=[
("What does `rm file` actually remove?",
 ["A directory entry (name) pointing at the inode", "The inode and its blocks immediately", "Only the file's metadata", "The data blocks only, keeping the name"],
 "Blocks are freed only after the last name AND the last open handle are gone."),
("`df` says 90% used, but `du -sh` on the same volume shows a few MB. What should you suspect first?",
 ["A deleted file still held open by a process (lsof +L1)", "Corrupt superblock", "Swap is full", "The kernel needs a reboot"],
 "du counts names, df counts blocks; deleted-but-open files are the classic gap."),
("The holder is a database you must not restart. How do you free the space now?",
 ["Truncate through its fd: `: > /proc/<PID>/fd/<FD>`", "rm the file again", "Run fsck", "chmod the fd"],
 "Writing through /proc/PID/fd/N truncates the underlying inode; the process keeps running."),
],
qa=[
("Explain to a junior what an inode and a link count are, and why deleting a file may not free space.",
 "An inode holds the file's metadata and block pointers; directory entries are names that link to it. rm removes one name and lowers the link count. When the count hits 0 AND the last open file descriptor closes, the kernel frees the blocks. A process with the file open keeps the space allocated."),
("After you truncate through /proc, `lsof +L1` still lists the file and the checker still fails. Why, and what do you do?",
 "The fd is still open (size now 0); the deleted inode still exists until the process closes it. The checker requires no process to hold a deleted spool file, so restart `log-shipper` in a maintenance window - it then opens a fresh, named file."),
]),

"m02": dict(
explain="""
**Two resources hide behind "No space left on device" (ENOSPC):**

- **blocks** (bytes of data) - `df -h`
- **inodes** (one per file or directory) - `df -i`

ext4 fixes the inode count at `mkfs` time (by a bytes-per-inode ratio). The 128 MB volume had only 4096 inodes; ~4000 tiny session files used them all while data usage stayed at 15%. The engineer's `df -h` was right and irrelevant.

**Find where:** `du --inodes -x /srv/shopdata | sort -n | tail` or count files per directory.

**Delete safely - dry-run first:**

```
find ... -type f -name 'sess_*' -mmin +1440 | wc -l    # how many old?
find ... -type f -name 'sess_*' -mmin -1440 | wc -l    # how many live (must keep)?
find ... -type f -name 'sess_*' -mmin +1440 -delete    # only now delete
```

`-mmin +1440` = modified more than 1440 minutes (24 h) ago.

**Why it happened:** the cleanup cron in `/etc/cron.d/shopapp-session-cleanup` was commented out "during migration" and never restored. Deleting files without re-enabling it just resets the clock. Prevention: alert on inode usage, size inodes for small-file workloads (`mkfs.ext4 -i`/`-N`) or use XFS (dynamic inodes).
""",
mcq=[
("`/health` returns `No space left on device`, but `df -h` shows 15% used. What next?",
 ["df -i - the filesystem may be out of inodes", "Reboot", "Increase swap", "Run fsck on /"],
 "ENOSPC = no blocks OR no inodes. Always check both."),
("What is the safe way to delete only sessions older than 24 hours?",
 ["Run find with the exact criteria and wc -l first, then repeat with -delete", "rm -rf /srv/shopdata/sessions/*", "find ... -mmin -1440 -delete", "Delete files by size"],
 "List and count before destroying; `-mmin +1440` selects old files, `-1440` would select the live ones."),
("Which action fixes the ROOT cause so the problem does not return?",
 ["Re-enable the disabled session-cleanup cron job", "Delete all sessions again next week", "Mount the volume read-only", "Increase `df -h` free space"],
 "A migration disabled the cleanup job; without it the files pile up again."),
],
qa=[
("Why must you not simply delete all session files?",
 "Sessions newer than 24 hours belong to active customers (carts); deleting them is a business-visible outage. The ticket demands keeping them, so filter by age, verify counts first, and delete only the old ones."),
("What would you do to prevent inode exhaustion for a small-file workload?",
 "Alert on inode usage (e.g. > 80%), keep scheduled cleanup jobs and track 'temporary' changes with an end date, create the filesystem with more inodes (mkfs.ext4 -i or -N) or choose XFS/btrfs with dynamic inodes, and avoid millions of tiny files where possible."),
]),

"m03": dict(
explain="""
**Load average** = average number of tasks that are runnable **or** in uninterruptible sleep. Compare it with the CPU count: load 2.1 on `nproc` = 2 means the machine is fully busy.

**Find the hog:** `top` (press `P`), or `ps -eo pid,ppid,user,ni,%cpu,etime,cmd --sort=-%cpu | head`.

**Who started it:** `pstree -ps <PID>` and `systemctl status <PID>`. Here the chain is `cron -> sh -> flock -> python3`. `grep -r reindex /etc/cron* /var/spool/cron` finds the schedule: `* * * * * root flock -n ... shopapp-reindex`.

**Why killing fails:** `flock -n` only prevents *duplicates*. Kill the running copy -> lock is free -> next minute cron starts a new one.

**Correct order:**

1. **Disable the scheduler first** (comment the cron line, add a note with the ticket number)
2. then kill the process (`pgrep -af` first, then an anchored `pkill -f '^...'`)
3. wait 2+ minutes and confirm it does not return

**Why anchor `pkill -f`?** `-f` matches the whole command line of every process - including your own `sudo pkill -f ...`, which contains the same text.

Hand off to the owning team (retry loop with no backoff); do not delete their script.
""",
mcq=[
("Load average is 2.10 on a host with 2 CPUs. What does that mean?",
 ["The CPUs are roughly fully utilised", "The host is idle", "The disk is saturated", "There is a memory leak"],
 "Compare load to nproc: load ~= nproc is full utilisation."),
("Why did the CPU hog return a minute after it was killed?",
 ["cron starts it every minute; flock -n only blocks duplicate runs", "The kernel restarts killed processes", "systemd's OOM killer", "The disk was full"],
 "A scheduler (cron, timer, supervisor) respawns it. Remove the trigger, not just the process."),
("What is the correct order to stop the job for good?",
 ["Disable the cron entry, then kill the process, then verify it stays gone", "Kill the process, then disable cron", "Reboot the host", "Delete the script"],
 "If you kill first, cron may immediately start another copy."),
],
qa=[
("What is the danger of `pkill -f reindex` and how do you make it safer?",
 "-f matches the full command line of ALL processes, so the pattern can also match your own sudo/pkill command or other tools (an editor with the script open). Run `pgrep -af` first, anchor the pattern (`^/usr/bin/python3 /usr/local/bin/shopapp-reindex`), and prefer stopping the owning unit/scheduler."),
("List the commands that answer 'who started this process?'",
 "`pstree -ps <PID>` (parent chain), `ps -o pid,ppid,user,etime,cmd -p <PID>`, `systemctl status <PID>` (unit/cgroup), `journalctl -u cron` (cron runs), `grep -r <name> /etc/cron* /var/spool/cron`, `systemctl list-timers`."),
]),

"m04": dict(
explain="""
**What happened:** `cache-warmer.service` has `MemoryMax=160M`. A load test had set `max_mb = 0` (= unlimited) in `/etc/cache-warmer.conf` and nobody reverted it. The cache grows ~20 MB/s until the unit's **cgroup** hits 160M and the kernel **OOM-kills a process inside that cgroup**. systemd reports `Result: oom-kill` and restarts it (`Restart=`) -> crash loop.

**How to tell a cgroup OOM from a host OOM:**

- `free -m` shows plenty of free RAM
- kernel log: `Memory cgroup out of memory: Killed process ...` and `oom-kill:constraint=CONSTRAINT_MEMCG ... task_memcg=/system.slice/cache-warmer.service`
- `systemctl show -p MemoryMax,MemoryCurrent,NRestarts cache-warmer`

**Leak or normal use?** Watch `MemoryCurrent`. A straight rising line = unbounded growth; a flat line = steady state.

**Fix the cause:** restore `max_mb = 64` and restart. Keep the limit: raising or removing it only delays the kill, and without it the *global* OOM killer might kill something important like the database.

"Nobody changed the code" - but a **config** change is a change.
""",
mcq=[
("`systemctl status` shows `Result: oom-kill` but `free -m` shows lots of free RAM. Why?",
 ["The unit hit its own cgroup limit (MemoryMax), not the host's RAM", "free is wrong inside containers", "Swap is exhausted", "The kernel is out of file descriptors"],
 "A memcg OOM triggers at the cgroup limit even if the host has free memory."),
("In the kernel log, which text tells you it was a cgroup OOM?",
 ["oom-kill:constraint=CONSTRAINT_MEMCG", "Out of memory: global", "EXT4-fs error", "nf_conntrack: table full"],
 "CONSTRAINT_MEMCG = the limit of that memory cgroup."),
("What is the right fix?",
 ["Set the cache bound back (max_mb = 64) and keep MemoryMax", "Remove MemoryMax", "Double MemoryMax to 320M", "Add swap"],
 "The cause is the unbounded cache config. A bigger limit just delays the same kill."),
],
qa=[
("Why is raising MemoryMax the wrong fix here?",
 "The cache has no upper bound (max_mb = 0) and grows ~20 MB/s, so any limit is eventually reached - you only delay the crash. Removing the limit lets the process threaten the whole host (global OOM may kill something critical). Fix the unbounded growth at its source."),
("How do you decide between a memory leak and legitimate memory use?",
 "Sample MemoryCurrent/RSS over time (`watch systemctl show -p MemoryCurrent`, `ps -o rss`). Legitimate use plateaus; a leak or unbounded cache rises steadily. Also read the service's start-up log/config for its configured bounds."),
]),

"m05": dict(
explain="""
**cron fails quietly.** Three independent mistakes meant the job never produced a backup, and nobody saw an error:

1. **File name** `shopapp-backup.cron` - on Debian/Ubuntu `/etc/cron.d` files follow `run-parts` naming: only `[A-Za-z0-9_-]`. A name with a `.` is **silently ignored** (so editor leftovers like `foo.bak` don't run).
2. **Mode 0666** - cron refuses files that are group/other-writable or not owned by root: `INSECURE MODE`. Fix: `root:root 0644`.
3. **Script without `x` bit** - cron executes the path directly (not `bash script`), so it needs the execute permission.

Even when cron runs the job, with no MTA the output is discarded - `No MTA installed, discarding output`.

**Method:**

- read the cron log: `journalctl -u cron` - do you see the job at all?
- run the **exact command as the exact user cron uses**: `sudo /usr/local/bin/shopapp-backup`
- check the result: `tar -tzvf /srv/backups/*.tar.gz` - a backup you never restored is not a backup

**Prevention:** deploy via config management/packages, log output (`>> file 2>&1` or `logger`), alert when the newest backup is older than ~26 h, consider systemd timers (logs in the journal).
""",
mcq=[
("Why was `/etc/cron.d/shopapp-backup.cron` never executed?",
 ["File names containing a '.' are ignored by cron's run-parts naming rules", "cron.d only accepts .cron suffix", "It needs a shebang", "cron only runs at midnight"],
 "No error is logged: such files are skipped silently."),
("The cron log shows `INSECURE MODE (group/other writable)`. What do you change?",
 ["chown root:root and chmod 0644 on the cron file", "chmod 777 the file", "Restart the kernel", "Add a MAILTO line"],
 "cron requires root ownership and no group/other write permission."),
("Cron now runs the job, but no archive appears. What is a likely remaining cause?",
 ["The script lacks the execute bit (cron runs it directly)", "Backups are only made on weekends", "cron can't write to /tmp", "The tar binary is missing from the kernel"],
 "Run it by hand exactly as cron does: it fails with Permission denied until chmod +x."),
],
qa=[
("'cron reported no errors' - why does that not prove the job works, and how do you make failures visible?",
 "Because several failures are silent: ignored file names, rejected insecure files, and discarded output when no MTA exists. Check `journalctl -u cron` for actual runs, run the command by hand as the cron user, redirect output to a log (`>> /var/log/x.log 2>&1` or logger), and alert when the newest backup is older than expected."),
("What does 'a backup you never restored is not a backup' mean in practice?",
 "You must verify the archive is usable: list/extract it (`tar -tzvf`), occasionally do a full test restore, and monitor backup age and size. An empty or corrupt archive gives false confidence."),
]),

"m06": dict(
explain="""
**Swap storm = slow system with idle CPU.** The sum of the batch workers' memory (10 workers x ~200 MB = ~2 GB) exceeds the RAM of a 2 GB VM. The kernel keeps moving pages between RAM and swap. Tasks wait for page-ins in uninterruptible sleep (D), which counts toward load average but not CPU use. Result: high load, high `wa`, low CPU, SSH echo lag.

**Signals in `vmstat 1`:** `si`/`so` in the thousands **every second**, `b > 0`, `wa` high, `cache` tiny, `free -m` -> `available` near zero. Swap *used* alone is not the signal; swap *activity* is.

**Two changes in CHG-552:**

- workers 2 -> 10 (capacity: workers x MB per worker must fit RAM with headroom)
- `vm.swappiness = 100` (swap application memory more eagerly)

`vm.swappiness` changes *when* the kernel swaps vs dropping page cache; it does not create memory.

**Persistence:** `sysctl -w` is runtime only. `/etc/sysctl.d/60-batch-tuning.conf` re-applies at boot, so remove or fix the file **and** set the runtime value. Verify with `sysctl --system | grep swappiness`.

Prevention: capacity check on changes, `MemoryMax=/MemoryHigh=` on batch units, alert on swap-in rate.
""",
mcq=[
("The host is very slow, `top` shows idle CPUs. Which `vmstat` pattern proves a swap storm?",
 ["si and so are high every second, with high wa", "r is high and us is 100", "cs is zero", "free is above 90%"],
 "Constant swap-in/swap-out plus I/O wait means tasks are waiting on swap."),
("What does `vm.swappiness` do?",
 ["Tunes how aggressively the kernel swaps application memory versus reclaiming page cache", "Sets the total swap size", "Enables the OOM killer", "Limits per-process memory"],
 "It is a preference, not a limit - it cannot create RAM."),
("How do you undo the swappiness tuning both now and after reboot?",
 ["sysctl -w vm.swappiness=60 AND remove the /etc/sysctl.d file", "Only run sysctl -w", "Only reboot", "Edit /proc/meminfo"],
 "Runtime change is lost on reboot; the file in sysctl.d would reapply the bad value."),
],
qa=[
("Why can load average be high while the CPUs are idle?",
 "Load counts runnable tasks plus tasks in uninterruptible sleep (D). During a swap storm many tasks wait for pages to be read from disk; they use no CPU but still add to load and iowait."),
("Give a quick capacity check that would have prevented CHG-552.",
 "workers x memory per worker (+ OS and other services) must be comfortably below RAM: 10 x ~200 MB = ~2 GB on a 2 GB host fails; 2 workers = ~400 MB fits. Also cap the batch unit with MemoryMax/MemoryHigh."),
]),

"m07": dict(
explain="""
**What a zombie is:** a process that has already exited but whose parent has not yet called `wait()` to read its exit status. Its memory is gone; only a **process-table entry** (PID + status) remains. State `Z`, shown as `<defunct>`.

**Why `kill -9` does nothing:** you cannot kill something that is already dead.

**Why it breaks the service:** every zombie still holds a **PID/task slot inside the unit's cgroup**. `TasksMax=150` + 150 zombies = the next `fork()` fails with `EAGAIN` (errno 11 `Resource temporarily unavailable`). EAGAIN on fork = task/PID limit, not memory.

**Who cleans up:** only the **parent** (calling `wait`) - or the parent's death (children are re-parented to PID 1, which reaps them). The dispatcher had `reap_children = false` in `/etc/queue-dispatcher.conf` (a debug flag from INC-2190 never reverted).

**Fix:** set `reap_children = true` and restart. Restarting alone clears the zombies but they return within ~30 s without the config fix. Don't raise `TasksMax` - it protects the host from runaway forks.

Prevent: expiring debug flags, alert on zombie count and on `Tasks` near `TasksMax`.
""",
mcq=[
("Why does `kill -9` have no effect on a `<defunct>` process?",
 ["It is already dead; only its process-table entry remains until the parent reaps it", "Zombies ignore SIGKILL by design of the kernel's scheduler", "kill -9 needs root", "The process is stuck in D state"],
 "Zombies are dead; the parent must call wait()."),
("`fork failed: [Errno 11] Resource temporarily unavailable` while memory is free. What limit was likely hit?",
 ["A task/PID limit such as TasksMax or pid_max", "The file descriptor limit", "The disk quota", "The swap size"],
 "EAGAIN from fork/clone = no more tasks allowed."),
("Which action removes zombies for good?",
 ["Fix the parent so it reaps children (or restart the parent)", "Reboot only", "Raise TasksMax", "Run kill -9 on each zombie"],
 "When the parent exits, orphans go to PID 1 and are reaped; fix the cause so they don't pile up."),
],
qa=[
("Why shouldn't you solve this by raising TasksMax?",
 "TasksMax is a safety net against fork bombs and leaks. Zombies would still accumulate until the new limit, merely delaying the failure and weakening host protection. The root cause is the parent not reaping (reap_children=false)."),
("What does a zombie cost, and what does it not cost?",
 "It costs almost nothing in CPU or memory, but it occupies a PID/task slot (counting against TasksMax and pid_max) until the parent reaps it."),
]),

"m08": dict(
explain="""
**Problem 1 - logrotate skips the file.** logrotate runs as root. If the log directory is **writable by a non-root user/group** (last week's change: `drwxrwxr-x shopapp:shopapp`), a user could swap files for symlinks and make root overwrite arbitrary files. So it prints `error: skipping ... because parent directory has insecure permissions`. Fix: `chmod 0755` (read access needs `r-x`, not `w`) and/or `su shopapp shopapp`.

**Problem 2 - the app keeps writing to the wrong file.** The app opens `app.log` once and keeps the fd. With `create`:

1. logrotate **renames** `app.log` -> `app.log.1` (same inode)
2. the app's fd still points at the renamed inode -> new lines go to `app.log.1`
3. `compress` gzips it and **deletes** it -> app writes to a deleted file (M01 again)
4. new `app.log` stays empty, space is not freed

**Options:** app reopens the log on a signal (`postrotate`), `copytruncate`, or restart in `postrotate`. `copytruncate` copies the content then truncates **in place** (same inode, fd stays valid) - but a few lines written between copy and truncate can be lost, and it needs free space for a **full copy** (a 190 MB file on an almost full volume fails with ENOSPC).

Also use `delaycompress` and `maxsize`, then **test**: `logrotate -d`, one forced `-f` run, `curl`, `lsof +L1`.
""",
mcq=[
("Which command does a safe dry-run of a logrotate rule?",
 ["logrotate -d /etc/logrotate.d/shopapp", "logrotate -f /etc/logrotate.d/shopapp", "logrotate --purge", "cron -t"],
 "-d = debug/dry run: shows what it would do and prints errors, changes nothing."),
("Why does the app keep writing to the old file after a `create`-style rotation?",
 ["It holds an open fd to the renamed file (same inode)", "logrotate deletes the app's PID", "The new app.log is read-only", "The app reads its config again"],
 "A rename keeps the inode; processes keep writing through their open file descriptors."),
("What is a trade-off of `copytruncate`?",
 ["Lines written between copy and truncate can be lost, and it needs free space for a full copy", "It requires restarting the app", "It deletes the old log", "It only works for compressed logs"],
 "It avoids reopening the log but is not atomic and uses disk space."),
],
qa=[
("Why does logrotate refuse a log directory that is group-writable?",
 "logrotate runs as root. A user able to write the directory could replace the log with a symlink to a sensitive file and trick root's rotation into overwriting or chowning it (privilege escalation). It skips such directories unless you fix modes or specify `su user group`."),
("Describe step by step how the log became invisible after the first forced rotation.",
 "`create` renamed app.log to app.log.1 (same inode); the app kept writing to that inode; `compress` gzipped and deleted app.log.1, so the app wrote into a deleted-but-open file. The new app.log stayed empty (size 0) and the 190 MB was not freed - confirmed by `lsof +L1`. Fix with copytruncate (or reopen signal) and restart the app to release the deleted file."),
]),

"m09": dict(
explain="""
**Check what the server *serves*, not only what is on disk.** `openssl s_client -connect 127.0.0.1:443 -servername shop.lab.internal </dev/null | openssl x509 -noout -subject -dates` showed an **expired** cert (`notAfter` 3 days ago).

**What went wrong in the "renewal":**

1. New files were copied to `/etc/ssl/shopapp/` but nginx still referenced `shop-2025.crt` / `.key` -> never switched
2. Two candidate new keys existed; only `shop-2026-renewal.key` matches the new certificate (`shop-2026.key` is a leftover from another CSR). A mismatch makes `nginx -t` fail with `key values mismatch`
3. The matching key was **world-readable** (`0644`)

**Prove a cert/key pair:** compare public-key hashes

```
openssl x509 -in CERT -noout -pubkey | sha256sum
openssl pkey -in KEY  -pubout       | sha256sum     # same hash = pair
```

**Fix:** `chmod 600` the key, point nginx at the 2026 cert + matching key, `nginx -t && systemctl reload nginx`, verify with `curl --cacert` and `openssl x509 -checkend 2592000` (still valid for 30 days?).

A private key that was world-readable must be treated as **possibly compromised** - in production report it, reissue key+cert, revoke the old one.
""",
mcq=[
("Which command shows the certificate that the server is actually presenting?",
 ["openssl s_client -connect host:443 -servername name | openssl x509 -noout -dates", "ls -l /etc/ssl", "nginx -v", "systemctl status nginx"],
 "Always verify the served cert; disk files may not be what nginx loaded."),
("How do you prove a certificate and a private key belong together?",
 ["Compare the sha256 of the public key from the cert and from the key", "Compare file names", "Compare file modification times", "Check both are mode 0600"],
 "`openssl x509 -pubkey` vs `openssl pkey -pubout` must give the same hash."),
("What mode should the nginx private key have?",
 ["0600 (root only) - or 0640 with a dedicated group", "0644", "0666", "0777"],
 "World-readable private keys must be treated as leaked."),
],
qa=[
("What three things make a certificate renewal complete?",
 "1) New cert and matching key files on disk. 2) The server configuration points at them (ssl_certificate / ssl_certificate_key). 3) The service reloads (after `nginx -t`) and you verify the served expiry date from outside. Missing step 2 or 3 leaves the old expired cert in use."),
("The new key was world-readable for a week. What do you do in production?",
 "Fix the mode immediately, then report to security: treat the key as potentially compromised, generate a new key and certificate, deploy them, and revoke the old certificate. Also audit who could have read it."),
]),

"m10": dict(
explain="""
**Read the client error exactly:**

| Error | Meaning |
|---|---|
| `Connection refused` | packet reached a host, nothing listens on that address:port (or a REJECT with RST) |
| `Connection timed out` | packets are **dropped** somewhere: firewall DROP, routing, host down |

**`curl localhost` is a misleading test.** It never touches the network interface, the INPUT rules for the external subnet, or the listening address used by remote clients.

**Two stacked faults:**

1. **SEC-118** `DROP` of the whole `10.210.0.0/24` on tcp/80 - which includes the monitoring probe (timeout). Found with `tcpdump -ni h-mon port 80` (SYNs arrive, nothing answers) and `iptables -L INPUT -n -v --line-numbers` (packet counter rises).
2. **CHG-610** bound nginx to `127.0.0.1:80`. After the firewall fix the error becomes **refused** - progress! `ss -ltnp | grep ':80 '` shows loopback only. Fix: `listen 80;` / `listen [::]:80;`, `nginx -t && reload`.

**Firewall habit:** read rules in order, with counters; insert an ACCEPT for the probe **before** the DROP (or narrow the DROP) instead of deleting the whole rule; persist the change.

Side finding: shopapp's `0.0.0.0:8080` lets the probe bypass nginx - that is what real hardening should address.
""",
mcq=[
("A remote client gets 'Connection timed out'. What is the most likely class of cause?",
 ["Packets are being dropped (firewall DROP or routing)", "Nothing listens on the port", "The service crashed", "The DNS name does not exist"],
 "Timeout = silence; refused = an active RST."),
("After fixing the firewall, the probe now gets 'Connection refused'. What does that tell you?",
 ["Traffic now reaches the host, but nothing listens on that address/port - check the listen address", "The firewall is still dropping", "DNS failed", "The cert expired"],
 "A changed error is progress: the next layer is the listener (nginx bound to 127.0.0.1)."),
("Why is `curl localhost/health` a poor check for 'is the shop reachable for customers'?",
 ["It bypasses the network path, remote firewall rules and the externally bound listen address", "localhost uses UDP", "It always returns 200", "It tests DNS only"],
 "Always test from where the user is."),
],
qa=[
("Describe your process for a layered outage where fixing one fault reveals another.",
 "Re-test from the client after every single change and compare the error text: timeout -> (fix firewall) -> refused -> (fix listen address) -> 200. Check counters (iptables -v), packet captures (tcpdump) and listeners (ss) at each layer; change one thing at a time; note each step in the incident notes."),
("What was the 'side finding' about shopapp on 0.0.0.0:8080 and why does it matter?",
 "The backend app listens on all addresses, so external clients can bypass nginx (and its controls) by hitting :8080 directly. Real hardening would bind it to 127.0.0.1 or restrict it by firewall, rather than binding nginx to loopback and breaking the service."),
]),
}
