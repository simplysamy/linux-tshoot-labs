# Hand-written study content for the hard labs and the method quiz. Same format as content_easy.py.

CONTENT = {
"h01": dict(
explain="""
**Two faults combined:**

1. **A leak** - `trace_requests = true` (debug flag from INC-1999) makes every request open `trace.log` and never close it: +1 fd per request.
2. **A tiny limit** - a legacy drop-in `shopapp.service.d/10-limits.conf` sets `LimitNOFILE=64`. It existed for weeks; the leak made it bite within minutes.

**EMFILE (`Errno 24 Too many open files`)** = per-process fd limit reached. Your shell's `ulimit -n` does **not** apply to a systemd service - limits come from the unit (`LimitNOFILE=`) and are visible in `/proc/<PID>/limits`.

**Why 504 and high CPU:** the listening socket stays "readable" but `accept()` fails with EMFILE, so the event loop spins.

**Evidence before restart:**

```
ls /proc/$PID/fd | wc -l              # 64
grep 'open files' /proc/$PID/limits   # 64
ls -l /proc/$PID/fd | awk '{print $NF}' | sort | uniq -c | sort -rn   # same file x56 = leak
strace -f -p $PID -e trace=openat,close   # openat without close
```

**Fix both:** turn tracing off, remove the bad drop-in (or set a sensible `LimitNOFILE=65536` via `systemctl edit`), `daemon-reload`, restart, then prove it with 300 requests and a stable fd count. Raising the limit alone only delays a leak. `systemctl cat` shows drop-ins; never edit `/lib/systemd/system`.
""",
mcq=[
("The log says `OSError: [Errno 24] Too many open files`. What limit is reached?",
 ["The per-process file descriptor limit (RLIMIT_NOFILE)", "The system-wide disk quota", "The number of inodes", "The TCP port range"],
 "EMFILE is per process; ENFILE would be system-wide."),
("Where do you see a RUNNING process's real fd count and limit?",
 ["/proc/<PID>/fd and /proc/<PID>/limits", "ulimit -n in your own shell", "/etc/security/limits.conf only", "df -i"],
 "Your shell's ulimit does not apply to systemd services; /proc shows the live state."),
("Why is raising LimitNOFILE alone not a fix here?",
 ["The code leaks one fd per request, so it would only take longer to fail again", "Systemd ignores LimitNOFILE", "fds are free", "The limit is read-only"],
 "A leak needs the code/config fixed; raising a limit just hides it for a while."),
],
qa=[
("Why capture evidence before restarting the service?",
 "A restart destroys the live state you need: open fds, which files they point to, thread/CPU behaviour, memory. Capturing `ls -l /proc/PID/fd`, `/proc/PID/limits`, strace output and logs first proves the cause (same file open 56 times, no close) and stops the team from repeating 'restart as a fix'."),
("Which two changes were combined into this outage, and which is the 'root cause'?",
 "The leak (debug trace on, file never closed) is the root cause; the legacy `LimitNOFILE=64` drop-in is the contributing condition that made it fail in minutes instead of days. Fix both and report the bug to developers (use `with open` / one shared handle)."),
]),

"h02": dict(
explain="""
**What happened:** a storage glitch corrupted metadata (a directory entry in `/catalog` pointed at a wiped inode). ext4 mounted with `errors=remount-ro` detected it and **remounted read-only** to protect the data - the "Read-only file system" error is a **symptom**, not the problem.

**Evidence:** `findmnt /srv/shopdata` (options `ro`), `journalctl -k | grep -i ext4` (`EXT4-fs error ... Remounting filesystem read-only`), `dumpe2fs -h <dev> | grep -i state` -> `clean with errors`.

**Correct recovery order:**

1. stop writers (`systemctl stop shopapp`, `cd /` yourself, `fuser -vm`)
2. `umount /srv/shopdata`
3. `e2fsck -f <device-or-image>` (run again; second run must be clean)
4. mount, check what is missing (`lost+found`)
5. restore the lost file from backup (`products.db`), fix ownership
6. start the app, test `/health`

**Never** `fsck` a mounted filesystem (it can destroy it). **Never** "fix" it with `mount -o remount,rw` - the error flag and broken entry remain, and the next access can flip it back or spread the damage. After fsck, files may vanish or end up in `lost+found` - backups are part of recovery.
""",
mcq=[
("Why did /srv/shopdata become read-only without anyone changing mounts?",
 ["ext4 detected corruption and remounted read-only (errors=remount-ro) to protect data", "The disk is full", "A cron job ran mount -o ro", "SELinux changed it"],
 "The kernel decided; its log names the device and function."),
("What is the correct sequence?",
 ["Stop writers -> umount -> e2fsck -f -> mount -> verify/restore -> start app", "remount rw -> start app -> fsck", "fsck on the mounted volume -> reboot", "Delete the volume and recreate it"],
 "fsck needs the filesystem unmounted; restore data before restarting writers."),
("Why is `mount -o remount,rw` the wrong fix?",
 ["It hides the symptom but leaves the corruption; it can fail again or spread damage", "It needs a reboot", "It deletes lost+found", "It always fails"],
 "The filesystem still has errors; run e2fsck."),
],
qa=[
("A colleague wants to run e2fsck right away on the mounted volume 'to save time'. What do you say?",
 "No. fsck must run on an unmounted (or read-only, with caution) filesystem; running it on a mounted rw filesystem can corrupt it further. Stop the writers, unmount (find holders with `fuser -vm`), then run `e2fsck -f`."),
("After fsck, `products.db` is gone. What now?",
 "Check `lost+found`, then restore from the latest good backup in /srv/backups/catalog, set ownership to shopapp, start the service and verify /health. Then investigate the storage layer (hypervisor logs, SMART) and test restores regularly."),
]),

"h03": dict(
explain="""
**Three stacked faults on the path client-ns -> router (this VM) -> app-ns.** Each fix only moves the failure forward - keep testing.

| # | Layer | Fault | How found |
|---|---|---|---|
| 1 | router | `net.ipv4.ip_forward = 0` | tcpdump on `h-cl` sees requests, nothing leaves `h-ap`; `sysctl` |
| 2 | server | no route back (no default route in app-ns) | tcpdump on `h-ap`: request arrives, no reply; `ip route get` |
| 3 | firewall | `FORWARD DROP tcp dport 9000` (SEC-204 wrong port) | ping works but curl times out; `iptables -L FORWARD -nv` counters |

**Principles:**

- Two-way thinking: a reply needs a route back.
- Bisect with `tcpdump` on each hop: find where the packet is last seen.
- Routed traffic hits **FORWARD**, not INPUT.
- Counters (`-v`) show which rule matches your traffic.
- ICMP working but TCP not -> a port-specific filter.

**Persistence matters:** `sysctl -w` and `iptables -D/-I` vanish on reboot. Use `/etc/sysctl.d/90-router.conf` and `iptables-save > /etc/iptables/rules.v4` (or nftables/ufw/config management).
""",
mcq=[
("A Linux box forwards packets between two interfaces only if:",
 ["net.ipv4.ip_forward = 1", "net.ipv4.tcp_syncookies = 1", "rp_filter = 0", "swap is enabled"],
 "Without ip_forward the kernel drops packets not addressed to itself."),
("Ping between the namespaces works but `curl :9000` times out. What does that suggest?",
 ["A port-specific filter such as an iptables FORWARD DROP rule", "ip_forward is off", "The cable is unplugged", "DNS is broken"],
 "ICMP passing proves routing; the TCP port is filtered."),
("tcpdump on h-ap shows ICMP echo requests arriving but no replies leaving. What is most likely?",
 ["The server has no route back to the client network", "The client has no default route", "The router has no firewall", "The server is powered off"],
 "The reply cannot be routed; check `ip route` / `ip route get <client>` in app-ns."),
],
qa=[
("Describe the bisect method you used to find where packets die.",
 "Start at the destination (service listening, answers locally), then the client (address, gateway, ping gateway), then run tcpdump on both router legs while pinging/curling. See on which interface the packet is last seen and whether replies exist; fix that fault, retest, repeat."),
("For each of the three fixes, how do you make it survive a reboot of the router?",
 "ip_forward: `/etc/sysctl.d/90-router.conf` (`net.ipv4.ip_forward = 1`). Route in app-ns: persist in that machine's network config (netplan/systemd-networkd or the namespace setup). Firewall: remove the bad rule from the persistent rule set (`iptables-save > /etc/iptables/rules.v4`, nftables config, ufw or config management)."),
]),

"h04": dict(
explain="""
**The red herring:** `batch-encoder` burns 100% of one CPU - but it runs at **nice 19**, so any normal task preempts it. In `top` it shows up as **`ni`**, not `us`. It cannot make the shell feel slow.

**The real bottleneck is disk I/O:**

```
%Cpu(s): 0.3 us, 6.0 sy, 49.0 ni, 0.0 id, 44.0 wa
vmstat: b = 1 (blocked)    iostat: w/s 950, w_await 1.0, %util 98
```

`wa` high + `b > 0` + processes in `D` state + disk `%util` ~ 100 = IO saturation. `pidstat -d` / `iotop` point to `dd if=/dev/zero of=/var/tmp/audit-sync.dat bs=4k oflag=dsync` - tiny synchronous writes. Only ~4 MB/s, but **every 4 KB write waits for the disk**, so the disk is full of IOPS and everything else queues behind it.

**Why it returns:** `systemctl status <PID>` shows `TriggeredBy: audit-sync.timer` (`OnUnitInactiveSec=20s`). Like cron, a timer restarts it.

**Fix options:** disable the timer (until the owner fixes the job) or keep it with low priority: `IOWeight=10`, `IOSchedulingClass=idle`, `IOWriteBandwidthMax=`.

**USE method:** for each resource (CPU, memory, disk, network) check Utilisation, Saturation, Errors - don't stop at the first busy thing.
""",
mcq=[
("`top` shows `49 ni` and `44 wa`. What is the bottleneck?",
 ["Disk I/O (iowait) - ni is only low-priority niced work using spare CPU", "CPU saturation by normal tasks", "Memory", "Network"],
 "ni = CPU used by niced processes (harmless when contended); wa = CPUs idle waiting for I/O."),
("Which tool shows I/O per process?",
 ["pidstat -d (or iotop)", "free -m", "ip -s link", "uptime"],
 "`pidstat -d 1` lists kB read/written per process."),
("Why is `systemctl stop audit-sync.service` alone not enough?",
 ["A systemd timer (TriggeredBy) starts it again", "stop is not allowed on services", "Services always restart on stop", "dd restarts itself"],
 "Disable the timer or constrain the job with IO limits."),
],
qa=[
("How do you prove with numbers that batch-encoder is not the cause?",
 "It runs at nice 19 (`ps -o ni`) and top attributes its CPU to `ni`; a normal-priority CPU loop still runs fast (`time`), us is tiny, nothing is starved. Meanwhile `wa` is 44%, `b` > 0, iostat shows %util ~98 and pidstat -d shows dd writing. The disk, not the CPU, is saturated."),
("Why can only ~4 MB/s of writes saturate a disk?",
 "The writes are 4 KB each with `oflag=dsync`: every one must reach stable storage before the next is issued, so the disk is limited by IOPS and latency, not bandwidth. ~950 sync writes/s keep it 98% busy and every other writer queues behind them."),
]),

"h05": dict(
explain="""
**systemd failures chain.** Fix the **first** failure.

1. `systemctl --failed` -> `srv-shopdata.mount failed`. `shopapp` says `Dependency failed`.
2. **Mount fault:** the "naming cleanup" changed `/etc/fstab` to `shop-data.img` but the real file is `shopdata.img` -> `failed to setup loop device`. Fix fstab (not the file), `systemctl daemon-reload` (fstab is turned into `.mount` units by a generator), `mount -a`.
3. **Service fault:** `status=217/USER` - systemd could not switch to the user. A drop-in from SEC-117 sets `User=shop-app` but that account was never created (`getent passwd shop-app` is empty). App logs are empty because the app never ran.

**Exit codes 200-243 are systemd setup failures:** 217/USER (user), 203/EXEC (exec), 200/CHDIR (working dir).

**Decision:** create `shop-app` (then fix ownership of config, logs and data - big change at 3 am) **or roll back** the half-applied change. Rolling back is the safe option; **never** "fix" with `User=root`.

**Survive the next reboot:** prove it by stopping the app, unmounting and starting again; validate with `findmnt --verify`, `mount -a`, `systemd-analyze verify`. Without `nofail`, a bad fstab line can send a server to emergency mode.
""",
mcq=[
("shopapp shows `Dependency failed`. What do you do first?",
 ["Find and fix the first failed unit in the chain (systemctl --failed)", "Restart shopapp repeatedly", "Reinstall nginx", "Reboot again"],
 "A failed mount causes the dependent service to fail; start at the root of the chain."),
("`status=217/USER` in systemctl status means:",
 ["systemd could not set the configured User= (account missing)", "The app ran out of memory", "The binary was not found", "A port is in use"],
 "217 = USER step failed, before the app code ran."),
("After editing /etc/fstab you must run:",
 ["systemctl daemon-reload", "ldconfig", "sysctl -p", "swapon -a"],
 "systemd generates .mount units from fstab; reload to regenerate."),
],
qa=[
("For the missing `shop-app` account, compare 'create it' versus 'roll back the drop-in'. Which would you choose at 3 am?",
 "Rollback: creating the account also requires changing owner/permissions on config, logs and data and testing them - a risky broad change when the owners are asleep. Roll back the half-applied SEC-117 drop-in, restore service, and let the change owners redo it completely in a planned window. Never use User=root."),
("Which commands would you run BEFORE a maintenance reboot to catch these two faults?",
 "`findmnt --verify` and `mount -a` (fstab), `systemd-analyze verify <units>`, test-starting services (`systemctl start`), `getent passwd <User=...>` for each configured service user, and ideally a reboot test in staging."),
]),

"h06": dict(
explain="""
**Every outgoing TCP connection needs a free local (ephemeral) port.** The connection is identified by the 4-tuple (src IP, src port, dst IP, dst port). The side that **closes first** keeps the tuple in **TIME_WAIT for 60 s** (fixed in Linux, `TCP_TIMEWAIT_LEN` - *not* `tcp_fin_timeout`).

**Capacity:** new connections per second to one destination ~ ports in range / 60.

- Default range `32768-60999` = 28 232 ports -> ~470 conn/s
- CHG-701 cut it to `61000-61100` = 101 ports -> **~1.7 conn/s**
- `price-sync` makes 20 req/s with `reuse_connections=false` -> needs ~1 200 ports

**Symptoms:** `errno 99 EADDRNOTAVAIL` on `connect()`, `curl` returns `000`, `ss -s` shows many `timewait`. Outside customers are fine because *they* use their own ports - the exhaustion is on this host's **client side** (here: loopback connections to nginx).

**Myths:** `tcp_fin_timeout` affects FIN_WAIT_2, not TIME_WAIT (red herring). `tcp_tw_recycle` was **removed in Linux 4.12** (it broke NAT clients). `tcp_tw_reuse` helps outgoing connections only.

**Real fix:** restore defaults (remove `/etc/sysctl.d/90-net-tuning.conf` + set runtime values) **and** make the client reuse connections (keep-alive / pooling).
""",
mcq=[
("`connect()` fails with errno 99 `Cannot assign requested address` for outgoing connections. What is the likely cause?",
 ["No free local (ephemeral) ports for new connections", "The remote server is down", "DNS failure", "Firewall REJECT"],
 "EADDRNOTAVAIL on connect = out of local ports (or no suitable source address)."),
("How long does a closed TCP connection stay in TIME_WAIT on Linux?",
 ["60 seconds (fixed)", "Whatever tcp_fin_timeout is set to", "2 seconds", "Until the process exits"],
 "tcp_fin_timeout is a red herring: it governs FIN_WAIT_2."),
("Which is the proper, lasting fix besides restoring the port range?",
 ["Connection reuse (HTTP keep-alive / pooling) in the client", "Enable tcp_tw_recycle", "Lower tcp_fin_timeout to 1", "Disable the firewall"],
 "tcp_tw_recycle no longer exists (removed in 4.12); fewer connections is the real fix."),
],
qa=[
("Calculate the sustainable new-connection rate for the default port range versus the CHG-701 range.",
 "Rate ~ ports / 60 s. Default 32768-60999 = 28 232 ports -> ~470 connections/s. CHG-701: 61000-61100 = 101 ports -> ~1.7 connections/s. price-sync needs 20/s, so it fails."),
("Why are outside customers unaffected while `curl localhost` flaps?",
 "Customers' connections use the customers' own ephemeral ports. The exhausted resource is this host's local port space for *outgoing* connections; the health check and price-sync both originate on this host (to 127.0.0.1:80), so they collide in the same tiny range."),
]),

"h07": dict(
explain="""
**The classic MTU black hole:** handshake and tiny requests work, bulk data hangs.

- Tunnel interface `r0` on the VPN gateway has **MTU 1400**; the server and partner both use 1500, so TCP negotiates MSS 1460 (1500-byte packets).
- Linux sets **DF (don't fragment)** on TCP packets. When the gateway can't forward a too-big packet it should send **ICMP type 3 code 4 "fragmentation needed"** (with the next-hop MTU) so the sender shrinks its packets: **Path MTU Discovery (PMTUD)**.
- **SEC-311 "no ICMP"** dropped those ICMP messages, so the server never learns the limit and retransmits the same big segment forever.

**Test:** `ping -M do -s 1372 <ip>` (1372 + 28 header bytes = 1400, replies) vs `-s 1472` (1500, silent loss). Test in the direction the bulk data flows. `tracepath` finds the path MTU. `tcpdump` shows identical large retransmissions and no ICMP.

**Fixes (both is best):**

- allow ICMP frag-needed before the drop: `iptables -I OUTPUT 1 -p icmp --icmp-type fragmentation-needed -j ACCEPT`
- **MSS clamping** on the gateway: MSS = 1400 - 20 (IP) - 20 (TCP) = **1360** via `-j TCPMSS --set-mss 1360`

Wrong fixes: raising `r0` to 1500 (the provider's tunnel can't carry it), changing the partner's machines. Also: a health check should download a **big** file, not a tiny URL.
""",
mcq=[
("Small requests work but large downloads hang. What should you suspect?",
 ["An MTU / Path MTU Discovery black hole", "DNS failure", "Expired certificate", "Wrong timezone"],
 "Large full-size packets are dropped; small ones fit in the tunnel."),
("Which ICMP message is essential for Path MTU Discovery?",
 ["Type 3 code 4: destination unreachable - fragmentation needed", "Type 8: echo request", "Type 11: time exceeded", "Type 5: redirect"],
 "SEC-311 blocked all ICMP and thereby this message."),
("What MSS should you clamp to for a tunnel MTU of 1400 (IPv4, no options)?",
 ["1360", "1400", "1460", "1500"],
 "1400 - 20 bytes IP header - 20 bytes TCP header = 1360."),
],
qa=[
("Why does 'block all ICMP' break TCP connections in this scenario?",
 "TCP relies on ICMP 'fragmentation needed' messages to learn the path MTU. With DF set, packets bigger than the tunnel are dropped by the gateway; if the ICMP error is also dropped, the sender never reduces its packet size and retransmits the same oversized segment forever - handshake and small requests (which fit) still work."),
("Why can't you simply set r0 to MTU 1500, and what two fixes are available instead?",
 "The tunnel MTU 1400 is fixed by the provider; the tunnel cannot carry 1500-byte packets, so setting 1500 would just break it. Instead allow ICMP type 3 code 4 (let PMTUD work) and/or clamp TCP MSS to 1360 on the gateway so neither side sends oversized packets."),
]),

"h08": dict(
explain="""
**conntrack tracks every connection** that passes through a stateful firewall - including loopback - as soon as a rule uses connection state (here `SEC-099 -m conntrack --ctstate INVALID -j DROP`). Each entry costs ~300 bytes.

**When the table is full the kernel drops new packets.** Established connections keep working (they already have an entry). New SYNs are dropped, the client retransmits after **1 s, then 3 s** ... -> `time_connect` of ~1 s or ~3 s, or a timeout. That "random" pattern plus **nothing in app logs** (the packets never reach nginx) points below the application. First stop: `dmesg` -> `nf_conntrack: table full, dropping packet`.

**Two causes:**

1. CHG-830 `/etc/sysctl.d/70-memory-saving.conf`: `nf_conntrack_max = 1024` (saves ~20 MB at best)
2. metrics-scraper v2 `pool_size = 1500` (typo for 15): 1500 idle established connections to :9100. Established entries are "assured" and live for days, so `early_drop` can't evict them.

**Find them:** `conntrack -C` vs `sysctl net.netfilter.nf_conntrack_max`, `conntrack -S`, `conntrack -L | grep -o 'dport=[0-9]*' | sort | uniq -c | sort -rn`, `ss -tn state established '( dport = :9100 )'`.

**Fix both:** pool 15 and restart the scraper; remove the sysctl file and set `nf_conntrack_max=65536`. Raising the limit alone would treat the symptom. Keep the SEC-099 rule.
""",
mcq=[
("New connections take ~1 s or ~3 s to establish at random; established ones are fine. What does the timing indicate?",
 ["SYN packets are being dropped and retransmitted (1 s, 3 s backoff)", "Slow DNS", "Disk latency", "Bad TLS ciphers"],
 "Exact ~1 s/~3 s delays are the TCP SYN retransmission timer."),
("Where do you look first when packets vanish below the application?",
 ["The kernel log (dmesg / journalctl -k)", "The nginx access log", "/var/log/apt/history.log", "crontab -l"],
 "App logs show nothing because the packets never reach the app."),
("Why is raising nf_conntrack_max by itself only half the fix?",
 ["Something is holding ~1500 idle connections; the table will fill again", "The limit cannot be raised", "conntrack uses no memory", "sysctl is read-only"],
 "Find who fills the table (metrics-scraper pool of 1500)."),
],
qa=[
("Why were there no errors in the application logs?",
 "The kernel dropped the new SYN packets in the netfilter conntrack path before they reached nginx or shopapp, so the applications never saw the connection attempts. Only the kernel log (`nf_conntrack: table full, dropping packet`) and client-side timing show it."),
("Why can't you just delete the SEC-099 rule to avoid conntrack, and how else is the issue solved?",
 "The ticket forbids removing the security rule; it uses connection state, so tracking stays enabled. The solution is to size the table sensibly (>= 16384, here 65536; ~20 MB) persistently and stop the leak - set the scraper pool to 15 and restart."),
]),

"h09": dict(
explain="""
**High load + idle CPU = look for D-state tasks.** Linux load average counts runnable tasks **plus tasks in uninterruptible sleep (D)**. Here `df`, `ls /mnt` and the report cron job all blocked inside the NFS client (`rpc_wait_bit_killable` in `sunrpc`) - they use no CPU but each adds 1 to load, and you can't Ctrl-C them.

**Why:** the mount uses `hard` (retry forever). SEC-410 "egress lockdown" added `DROP tcp dport 2049` to the NAS (`iptables -L OUTPUT -n -v` shows the counter rising). The server is unreachable, but the client waits for ever.

**Investigate safely:**

- `findmnt -t nfs,nfs4` - reads the mount table only (safe)
- `timeout 5 stat -f /mnt/reports` - not a bare `ls`/`df`
- `cat /proc/<PID>/stack`, `ps -eo pid,stat,wchan:32,cmd | awk '$2 ~ /D/'`, `dmesg -T | grep -i nfs`
- `nc -vz -w3 <ip> 2049`

**Fix:** allow the NAS egress; the hard mount recovers by itself (TCP backoff - up to a minute or two). As a last resort `umount -f -l`.

**Boot safety:** `_netdev,nofail` (and optionally `x-systemd.automount`, `x-systemd.mount-timeout=30`) so a dead NAS can't block boot. Keep `hard` for data you write: `soft` can silently corrupt writes on timeouts.
""",
mcq=[
("Load average is 20 but CPU is idle. What do you look for?",
 ["Processes in D (uninterruptible sleep) state, e.g. blocked on I/O or NFS", "A CPU hog", "Zombie processes", "Swap size"],
 "D-state tasks count toward load but use no CPU."),
("Which command lets you list NFS mounts without risking a hang?",
 ["findmnt -t nfs,nfs4", "df -h", "ls /mnt/reports", "du -sh /mnt/reports"],
 "findmnt reads the mount table; df/ls/du touch the (dead) server."),
("Which fstab options make an NFS mount safe for boot when the NAS may be down?",
 ["_netdev,nofail (optionally x-systemd.automount / mount-timeout)", "soft,ro only", "noauto,hard", "defaults,sync"],
 "_netdev = needs network; nofail = don't fail boot if it can't mount."),
],
qa=[
("Explain `hard` vs `soft` NFS mounts and which you keep for report data.",
 "hard retries I/O forever (processes block until the server returns; no silent data loss); soft returns an error after retries (can leave partially written or corrupted data). For data you write, keep `hard` and make boot safe with `_netdev,nofail`, and use `timeout` in scripts/monitoring."),
("Why can't you interrupt `df -h` with Ctrl-C, and what does that tell you about its state?",
 "The process is in uninterruptible sleep (D) inside the kernel NFS client waiting for the server; signals are not delivered until the I/O returns (for hard mounts only fatal signals may work, depending on kernel). Its state `D` and wchan `rpc_wait_bit_killable` identify it."),
]),

"h10": dict(
explain="""
**The host is idle - but shopapp is not allowed to use it.** FINOPS-77 added a drop-in `50-finops.conf`:

```
[Service]
CPUQuota=5%
Slice=shop.slice
```

and `shop.slice` itself has `CPUQuota=10%`. systemd turns these into cgroup v2 `cpu.max`:

- `cpu.max = 5000 100000` -> **5000 us of CPU per 100000 us period = 5% of one CPU**
- `cpu.stat`: `nr_throttled 39877` of `nr_periods 41210` -> throttled in almost every period; `throttled_usec` huge

Host-level `top` shows 90% idle because other CPUs have nothing to do - the quota stops *this cgroup* at its allowance regardless.

**Limits stack:** service -> slice -> parent slice. The **tightest wins**. Removing only the service quota still leaves the slice cap at 10%.

**Find them:** `systemd-cgtop`, `systemctl status shopapp` (`CGroup: /shop.slice/...`), `systemctl cat shopapp` (shows every drop-in), `systemd-delta --type=extended`, `cat /sys/fs/cgroup/<path>/cpu.max` on **every level**.

**Fix:** remove the drop-in (and the slice quota), `daemon-reload`, restart; confirm `cpu.max = max 100000` and `nr_throttled` stays 0. Prefer **`CPUWeight=`** (matters only under contention) to hard **`CPUQuota=`** for latency-sensitive services.
""",
mcq=[
("The host is 90% idle but one service is very slow. Which mechanism could explain it?",
 ["CPU throttling by a cgroup quota (cpu.max / CPUQuota)", "A full disk", "Zombie processes", "An expired certificate"],
 "A quota throttles the cgroup even when the host has free CPU."),
("What does `cpu.max` = `5000 100000` mean?",
 ["5000 us of CPU time per 100000 us period = 5% of one CPU", "5000 CPUs", "100000 shares", "5% of total host CPU"],
 "quota/period."),
("Which is better for a latency-sensitive service on a shared host?",
 ["CPUWeight (relative share applied only under contention)", "A hard CPUQuota of 5%", "Nice 19", "Removing the cgroup"],
 "Weights don't throttle an idle host; quotas do."),
],
qa=[
("Why isn't removing only the service's CPUQuota enough in this lab?",
 "The service sits in `shop.slice`, which has its own 10% quota. Limits stack and the tightest applies, so shopapp would still be throttled at 10% of one CPU. Remove the drop-in that moves it into shop.slice (and/or the slice quota) and verify cpu.max on every level."),
("How do you prove throttling to a skeptic who says 'it can't be CPU, the host is idle'?",
 "Show `cpu.max` for the service cgroup and `cpu.stat` with `nr_throttled`/`throttled_usec` increasing (nr_throttled close to nr_periods), plus `systemd-cgtop` showing shopapp stuck at ~5% while the host shows 90% idle."),
]),

"method": dict(
explain="",
mcq=[
("`Connection refused` - which layer is most likely at fault?",
 ["Nothing listens on that port (service down or wrong port)", "A firewall drop", "DNS", "TLS"],
 "Refused = an active RST from the kernel: reachable host, no listener."),
("`Connection timed out` - which layer is most likely at fault?",
 ["Packets are dropped: firewall, routing or host down", "Nothing listens on that port", "Wrong file permissions", "Out of memory"],
 "Silence is typical for DROP rules and routing problems."),
("nginx returns 502 versus 504. What is the difference?",
 ["502: backend down/refusing; 504: backend up but not answering in time", "502: DNS; 504: TLS", "502: client error; 504: server error", "They are identical"],
 "Check the backend first for 502; for 504 look for hangs and overload."),
("`No space left on device` (ENOSPC) with `df -h` showing free space. What next?",
 ["df -i - inodes may be exhausted", "Reboot", "Add RAM", "Run fsck on a mounted fs"],
 "ENOSPC means no blocks OR no inodes."),
("What does `Cannot assign requested address` on an outgoing connect indicate?",
 ["Out of local (ephemeral) ports", "The remote IP is wrong", "DNS failure", "Disk full"],
 "EADDRNOTAVAIL on connect: see TIME_WAIT and ip_local_port_range."),
("A systemd service exits with 127. What does that mean?",
 ["Command not found (PATH)", "Out of memory", "Permission denied", "Port in use"],
 "127 = not found; 126 = not executable."),
("What does the USE method stand for?",
 ["Utilisation, Saturation, Errors - for each resource", "User, System, Exit", "Up, Slow, Error", "Usage, Swap, Entropy"],
 "Check all of CPU, memory, disk and network; don't stop at the first busy thing."),
("Why should you preserve evidence before restarting a failing service?",
 ["A restart destroys live state (open fds, memory, stuck threads) you need for root cause", "Restarts are forbidden", "It makes the service faster", "Logs are deleted on restart"],
 "Capture ps, /proc/PID/fd, ss, logs first - then restart if you must."),
("`Too many open files` (EMFILE) points to:",
 ["The per-process file descriptor limit", "A full disk", "No inodes", "A bad certificate"],
 "Check /proc/PID/limits and the unit's LimitNOFILE."),
("`Read-only file system` (EROFS) most often means:",
 ["The filesystem was remounted read-only after errors (or mounted ro)", "Wrong file mode", "No inodes", "A full disk"],
 "Check the kernel log; run e2fsck on the unmounted fs - don't just remount rw."),
],
qa=[
("List the 8 steps of the senior troubleshooting method from the README.",
 "1) Confirm the symptom yourself. 2) Define scope and ask 'what changed?'. 3) Work outside-in, layer by layer. 4) USE method for performance. 5) One hypothesis, one test, one change at a time. 6) Preserve evidence before fixing. 7) Fix the cause, not only the symptom. 8) Verify, persist (survive reboot), document."),
("Give three production safety rules from the guide.",
 "Look before destructive commands (ls before rm, find ... | wc -l before -delete, pgrep -af before pkill -f); prefer reload over restart and run the config test first; never chmod 777 or run the service as root to 'fix' permissions; never fsck a mounted fs or just remount a broken fs rw; announce what you are doing in the incident channel."),
]),
}
