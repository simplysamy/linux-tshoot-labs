# Per-command explanations for the hard labs' solution walkthroughs.
# Pipes (|) are only allowed inside `code` spans (the table parser splits on bare pipes).

CMDS = {
"h01": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `curl -s -o /dev/null -w '%{http_code}\n' --max-time 15 localhost/` | Status code only, give up after 15 s. | `504`: the app is hanging, not erroring. |
| `PID=$(systemctl show -p MainPID --value shopapp)` | Captures the main PID into a shell variable. `--value` prints just the number. | Reused in every following command; **gather evidence before restarting**, a restart destroys it. |
| `top -p $PID` | Live view of one process. | High CPU while hung: an event loop spinning. |
| `ls /proc/$PID/fd | wc -l` | Counts open file descriptors. | 64 fds open. |
| `grep 'open files' /proc/$PID/limits` | The **effective** limits of the running process. | `Max open files 64` - the process is at its ceiling. |
| `journalctl -u shopapp --since "15 min ago" | grep -i errno | tail -3` | Search recent errors. | `Errno 24 Too many open files: trace.log`. |
| `ls -l /proc/$PID/fd | awk '{print $NF}' | sort | uniq -c | sort -rn | head` | Prints the last field (the target path) of each fd, groups and counts identical lines, biggest first. | 56 fds are the **same file**: `trace.log` opened repeatedly = a leak. |
| `strace -f -p $PID -e trace=openat,close -o /tmp/st.txt &` | Traces system calls of the process (and its threads, `-f`), only `openat`/`close`, into a file, in the background. | Watch one request: `openat(trace.log)` with no matching `close()`. |
| `grep trace.log /tmp/st.txt` | Filter the trace. | Proves the leak at the syscall level. |
| `grep -n trace /etc/shopapp/config.ini` | Search config. | `trace_requests = true` set yesterday for debugging INC-1999. |
| `systemctl cat shopapp` | Unit file **plus all drop-ins**. | Reveals `LimitNOFILE=64` in `10-limits.conf`: the old tiny limit made the leak fail within minutes. |
| `sed -i 's/^trace_requests = true.*/trace_requests = false/'` | Turns tracing off. | Stops the leak. |
| `rm .../10-limits.conf; systemctl daemon-reload; systemctl restart shopapp` | Removes the override, reloads units, restarts. | Removes the bad limit. Custom limits belong in a drop-in made with `systemctl edit`, never in `/lib/systemd`. |
| `for i in $(seq 300); do curl -s -o /dev/null localhost:8080/; done` | 300 quick requests. | Load test; fd count must stay small and stable afterwards. |
""",

"h02": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `curl -s localhost/health` | Health call. | `Errno 30 Read-only file system`. |
| `findmnt /srv/shopdata` | Shows mount source, type and **options**. | `ro,...,errors=remount-ro`: the kernel flipped it to read-only after an error. |
| `touch /srv/shopdata/x` | Tries a write. | Quick proof. |
| `journalctl -k --since "1 hour ago" | grep -iE 'ext4|remount'` | Kernel messages about ext4. | `EXT4-fs error ... deleted inode referenced` followed by `Remounting filesystem read-only`: on-disk corruption. |
| `dumpe2fs -h /dev/loop1 | grep -iE 'state|error'` | Prints the ext4 superblock header. | `clean with errors`, error count, last error function. |
| `cd /` | Leaves the mount point. | Your own shell would make the unmount fail with "busy". |
| `fuser -vm /srv/shopdata` | Lists processes using the mounted filesystem. | Find what to stop before unmounting. |
| `systemctl stop shopapp; umount /srv/shopdata` | Stop the writer, unmount. | `e2fsck` must only run on an **unmounted** filesystem. Avoid `umount -l` (lazy) here. |
| `grep shopdata /etc/fstab` | Find the backing device/image. | The "disk" here is a loop file. |
| `e2fsck -f IMAGE` | Filesystem check and repair; `-f` forces a check even if flagged clean. | Clears the bad directory entry. Run it **twice**: the second must be clean. Use `-n` first for a read-only dry run on real disks. |
| `mount /srv/shopdata` | Mounts using the fstab entry. | Back to `rw`. |
| `ls -l lost+found/ ... backups/catalog/` | Look for what fsck removed or moved. | `products.db` is gone: restore from backup. |
| `cp backup /srv/shopdata/catalog/products.db; chown shopapp:shopapp ...` | Restore and fix ownership. | The service user must be able to read it. |
| `mount -o remount,rw` (the **wrong** fix) | Flips to rw without repair. | Hides the problem: error flag and broken entry remain; it can go read-only again. |
""",

"h03": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `C="sudo ip netns exec client-ns"` etc. | Shell variables as shortcuts. | `ip netns exec NS CMD` runs a command inside a network namespace (simulated host). |
| `$A ss -ltnp` | Listeners inside app-ns. | Start at the **destination**: is the service even listening? Yes, `10.200.0.2:9000`. |
| `$A curl -s 10.200.0.2:9000` | Local test on the app host. | App works, so the fault is on the path. |
| `$C ip addr show cl0` / `$C ip route` | Client's address and routes. | Check the first hop config: correct IP, default via the router. |
| `$C ping -c2 10.201.0.1` | Ping the gateway. | Gateway OK = L2/L3 to the first hop works. |
| `$C ping -c2 -W1 10.200.0.2` | `-W1` = 1 s timeout. | 100% loss: the problem is beyond the gateway. |
| `tcpdump -ni h-cl icmp` + `tcpdump -ni h-ap icmp` | Capture ICMP on each side of the router. | Packets arrive on the client side and nothing leaves on the app side = the router does not forward. |
| `sysctl net.ipv4.ip_forward` | Reads the kernel setting. | `0` = this host will not route. |
| `sysctl -w net.ipv4.ip_forward=1` | Sets it now. | Fault 1 fixed at runtime. |
| `echo '...' | tee /etc/sysctl.d/90-router.conf` | Writes the setting to a file; `tee` is used because `sudo echo > file` would redirect as you. | Makes it survive a reboot. |
| `$A ip route` and `$A ip route get 10.201.0.2` | Routing table, and which route would be used for an address. | `Network is unreachable`: the server has **no return route** (fault 2). |
| `$A ip route add default via 10.200.0.1` | Adds a default route. | Replies can now find their way back. |
| `iptables -L FORWARD -nv --line-numbers` | Router's forwarding rules with counters. | Fault 3: `DROP tcp dpt:9000` (SEC-204) with growing counter. ICMP works but TCP 9000 does not -> port filter. |
| `iptables -D FORWARD 1` | Delete rule 1. | Only after agreeing with security (change ticket). |
| `iptables-save > /etc/iptables/rules.v4` | Dump current rules. | Persist so the change survives reboot. |
""",

"h04": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `uptime` | Load. | Load 2-3 on 2 CPUs: looks like CPU problem... |
| `vmstat 1 5` | 1 s samples. | `b` (blocked) and `wa` (IO wait) high, `us` low: waiting on disk, not CPU. |
| `top` (header) | CPU line breakdown. | `ni 49%` = niced batch work (harmless, yields). `wa 44%` = the real pain. |
| `ps -o pid,ni,pri,%cpu,cmd -C python3` | Shows nice value and priority for processes named `python3`. | `batch-encoder` is `NI 19` = lowest priority. |
| `time (for i in $(seq 200000); do :; done)` | Times a CPU-bound loop at normal priority. | Still fast = the nice 19 process is not slowing normal tasks. **Prove or reject the red herring.** |
| `iostat -xz 1 3` | Extended per-device disk stats (`-x`), skip idle devices (`-z`). | `%util 98%` with `w_await` ~1 ms and ~950 writes/s: the disk is saturated by many tiny writes. |
| `pidstat -d 1 5` | Per-process disk IO. | `dd` writes 3800 kB/s, `iodelay` 95. |
| `ps -eo pid,stat,wchan:22,cmd | awk '$2 ~ /D/'` | Shows processes in state `D` (uninterruptible IO wait) and what kernel function they wait in. | Finds `dd ... oflag=dsync`: every 4 KB write is forced to disk synchronously. |
| `systemctl status 3310` | Maps PID to unit. | `audit-sync.service`, `TriggeredBy: audit-sync.timer`. |
| `systemctl list-timers --all | grep audit` / `systemctl cat audit-sync.timer` | Timer schedule. | `OnUnitInactiveSec=20s`: restarts 20 s after it ends, which is why killing it fails. |
| `systemctl disable --now audit-sync.timer` | Stop the schedule and never start at boot. | Option A. |
| `systemctl edit audit-sync.service` + `IOSchedulingClass=idle` `IOWeight=10` | Drop-in override that gives the job lowest IO priority. | Option B: keep a required job from hurting others. |
| `IOWriteBandwidthMax=/dev/sda 1M` | Hard IO bandwidth cap. | Works with any IO scheduler. |
""",

"h05": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `systemctl --failed` | Lists failed units. | `srv-shopdata.mount` is the first failure. |
| `systemctl status shopapp` | Status of the app. | `Dependency failed for shopapp.service`: it never started because its mount is missing. |
| `systemctl list-dependencies shopapp` | Dependency tree with states. | Shows which dependency is red. **Fix the first failure in the chain.** |
| `journalctl -b -u srv-shopdata.mount` | Logs of the mount unit from the current boot (`-b`). | `failed to setup loop device for .../shop-data.img`. |
| `grep shopdata /etc/fstab` and `ls -l /var/lib/tshoot/*.img` | Compare fstab path with real files. | fstab says `shop-data.img`, the file is `shopdata.img`. Typo from the "naming cleanup". |
| `sed -i 's#...shop-data.img#...shopdata.img#' /etc/fstab` | Fix the path. | Fix fstab (not the file): other things may use the real name. |
| `systemctl daemon-reload` | Regenerates mount units from fstab. | **Required** after editing fstab. |
| `mount -a` / `findmnt /srv/shopdata` | Mount everything in fstab / verify. | Fault 1 fixed. |
| `systemctl start shopapp` -> `status=217/USER` | systemd could not switch to the configured user. | Fault 2: drop-in says `User=shop-app`. |
| `getent passwd shop-app` / `getent passwd shopapp` | Lookup in the user database. | The new account was never created; the old one exists and owns the data. |
| `mv .../20-service-account.conf /root/...rolled-back` | Moves the override out of the way, keeps a copy. | Roll back the half-done SEC-117 change. Never "fix" with `User=root`. |
| `systemctl stop shopapp && umount /srv/shopdata ... start shopapp` | Simulate a boot sequence. | Proves the mount is pulled in as a dependency and the whole chain survives a reboot. |
""",

"h06": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `for i in $(seq 10); do curl -s -o /dev/null -w '%{http_code} ' localhost/; done; echo` | 10 requests, print only status codes on one line. | Mixed `000` and `200` = intermittent. `000` = no HTTP answer at all. |
| `curl -v localhost/` | Verbose single request. | `Cannot assign requested address` = errno 99 `EADDRNOTAVAIL`: no free **local** port for an outgoing connection. |
| `journalctl -u price-sync -n 3` | Client log. | Same errno 99; it is the busy client. |
| `ss -s` | Socket summary by state. | Many `timewait` sockets. |
| `ss -tan state time-wait | awk 'NR>1{print $4}' | cut -d: -f2 | sort -n | sed -n '1p;$p'` | Lists TIME_WAIT sockets, takes the local address column, strips the IP, sorts numerically, prints first and last line. | Shows the used port span: 61000-61100 = only 101 ports. |
| `sysctl net.ipv4.ip_local_port_range net.ipv4.tcp_tw_reuse net.ipv4.tcp_fin_timeout` | Read three tunables at once. | Range narrowed to 101 ports, `tw_reuse=0`. `tcp_fin_timeout` is a **red herring** (it affects FIN_WAIT_2, TIME_WAIT is fixed at 60 s). |
| `cat /etc/sysctl.d/90-net-tuning.conf` | Persistent settings. | The source of the bad values (CHG-701). |
| `cat /etc/price-sync.conf` | Client config. | `reuse_connections = false`: a new TCP connection per request - 20/s x 60 s = 1200 ports needed. |
| `rm /etc/sysctl.d/90-net-tuning.conf` + `sysctl -w ...` x3 | Remove the file and restore defaults now. | `32768 60999`, `tw_reuse=2` (loopback only), `fin_timeout=60`. |
| `sysctl --system` | Re-apply all sysctl files. | Make sure no other file narrows the range again. |
| `sed -i 's/^reuse_connections *=.*/reuse_connections = true/' ...` and restart | Enable HTTP keep-alive. | Fixes the cause at the client. |
""",

"h07": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `$C curl -s http://10.230.2.2:8000/small.txt` | Small download from the customer namespace. | Works: handshake and small packets are fine. |
| `$C curl -o /dev/null -m 20 -w '%{size_download}\n' .../catalog.bin` | Large download; `-m 20` time limit; prints bytes received. | Hangs with 0 bytes: classic **MTU black hole** symptom (small works, big hangs). |
| `$D ping -c2 -M do -s 1372 10.230.1.2` | `-M do` = set Don't Fragment; `-s` payload size (+28 bytes of headers). | 1372+28 = 1400 bytes: replies. |
| `$D ping -c2 -M do -s 1472 10.230.1.2` | Same with 1500-byte packets. | No reply **and no error**. Normally a router would return "Frag needed". Silence = ICMP is being dropped. |
| `ip -n NS link | grep mtu` | Shows MTU of interfaces in each namespace. | Finds the weak link: tunnel `r0` has MTU 1400. |
| `tcpdump -ni ap0 'tcp or icmp'` | Capture on the server side. | The same 1448-byte segments are retransmitted again and again; no ICMP ever arrives. |
| `$V iptables -L OUTPUT -n -v` | Gateway's output rules. | `DROP icmp` (SEC-311): the gateway **does** generate "fragmentation needed" and the firewall eats it. |
| `iptables -I OUTPUT 1 -p icmp --icmp-type fragmentation-needed -j ACCEPT` | Allow just that ICMP type, before the drop. | Fix a: PMTUD works again; the sender learns MTU 1400. |
| `iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1360` | Rewrites the MSS option in SYN packets to 1360 (1400 - 20 IP - 20 TCP). | Fix b (MSS clamping): neither side sends packets bigger than the tunnel can carry. |
| `$D tracepath -n 10.230.1.2` | Discovers path MTU hop by hop. | After the fix it reports `pmtu 1400`. |
""",

"h08": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `curl ... -w '%{http_code} %{time_connect}s\n' --max-time 5 localhost/` | Prints status and TCP connect time. | Connect times of exactly ~1 s / ~3 s = SYN retransmits: the first SYN was **dropped** (before nginx ever saw it). |
| `dmesg -T | tail -5` | Kernel ring buffer with readable timestamps. | `nf_conntrack: table full, dropping packet`. |
| `conntrack -C` | Counts current tracked connections. | 1024 - exactly the max. |
| `sysctl net.netfilter.nf_conntrack_max` | The table limit. | 1024 (should be tens of thousands). |
| `conntrack -S | head -2` | Per-CPU statistics. | `drop`/`early_drop` counters growing. |
| `grep -r conntrack /etc/sysctl.d/` | Where was it set? | `70-memory-saving.conf` (CHG-830). |
| `iptables -S | grep SEC-099` | Rules in `-A` form. | A rule using `-m conntrack` forces connection tracking for everything, even loopback. |
| `conntrack -L -p tcp 2>/dev/null | grep -o 'dport=[0-9]*' | sort | uniq -c | sort -rn | head -3` | Lists TCP entries, extracts the destination port, counts per port, top 3. | 1480 entries to port 9100: that is who fills the table. |
| `ss -tnp state established '( dport = :9100 )' | head -3` | Established connections to port 9100 with owners. | Owner is `metrics-scraper`. |
| `cat /etc/metrics-scraper.conf` | App config. | `pool_size = 1500` (typo for 15). Established entries are "assured" and cannot be early-dropped. |
| `sed -i 's/^pool_size *=.*/pool_size = 15/'` + restart | Fix the leak. | Cause fix. |
| `rm /etc/sysctl.d/70-memory-saving.conf` + `sysctl -w net.netfilter.nf_conntrack_max=65536` | Remove persistent bad limit and set it now. | 65536 entries is ~20 MB: the "saving" was negligible, the outage was not. |
""",

"h09": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `uptime` and `top -bn1 | head -5` | Load vs CPU (`-b` batch mode, `-n1` one iteration). | Load 9, CPU 98% idle: load comes from tasks **waiting**, not working. |
| `ps -eo pid,stat,etime,wchan:32,cmd | awk 'NR==1 || $2 ~ /D/'` | Keeps header + processes in state `D`; shows the kernel wait function. | `df`, `report-export` stuck in `rpc_wait_bit_killable` = NFS client. |
| `cat /proc/8101/stack | head -5` | Kernel stack of the stuck task. | `sunrpc`, `nfs4_proc_statfs`: waiting for the NFS server. |
| `findmnt -t nfs,nfs4` | Lists NFS mounts. **Safe**: reads the mount table only, does not touch the server. | Which mount and server: `nas01:/srv/nfs/reports`, options `hard`. |
| `dmesg -T | grep -i nfs | tail -3` | Kernel NFS messages. | `server nas01 not responding, still trying`. |
| `getent hosts nas01.lab.internal` | Resolve the server name. | Rules out DNS. |
| `timeout 5 stat -f /mnt/reports || echo "mount hangs"` | Test with a time limit so **your** shell does not hang too. | Safe probe. |
| `nc -vz -w3 10.240.0.10 2049` | TCP connect test (`-z` scan only, `-w3` timeout). | Port 2049 times out: network path blocked. |
| `iptables -L OUTPUT -n -v --line-numbers` | Egress rules. | `DROP ... dpt:2049` (SEC-410) with counters rising as the client retries. |
| `iptables -D OUTPUT 1` or `-I OUTPUT 1 -d 10.240.0.10 -p tcp --dport 2049 -j ACCEPT` | Remove or make an exception. | Agree with security first. The `hard` mount then recovers by itself. |
| `umount -f -l /mnt/reports` | Force + lazy unmount. | Last resort if the server is truly gone: frees the host but pending writes are lost. |
| `fstab` options `_netdev,nofail,x-systemd.mount-timeout=30` | `_netdev` = wait for network, `nofail` = do not block boot, timeout = do not hang forever. | Makes the next NAS outage non-fatal at boot. |
| `systemctl daemon-reload; mount -o remount /mnt/reports` | Re-read fstab and apply. | Activate the new options. |
""",

"h10": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' localhost/` | Status and total time. | 3-10 s and 504s... |
| `top -bn1 | head -4` | CPU header. | 91% idle: the **host** is not busy, so something is restricting this service. |
| `systemctl status shopapp | grep -E 'CGroup|CPU'` | Shows total CPU time and the cgroup path. | CGroup is `/shop.slice/...`, not `system.slice`: someone moved it. |
| `systemd-cgtop -n 1` | Per-cgroup resource view. | The service never goes above ~5%. |
| `cat $CG/cpu.max` | Raw cgroup v2 CPU limit: `quota period` in microseconds. | `5000 100000` = 5% of one CPU. |
| `cat $CG/cpu.stat` | Counters. | `nr_throttled` almost equals `nr_periods`: throttled nearly every period. |
| `systemctl cat shopapp` | Unit file and drop-ins. | Finds `50-finops.conf`: `CPUQuota=5%` and `Slice=shop.slice`. |
| `systemd-delta --type=extended` | Lists every override across the host. | Find all drop-ins from the FinOps change at once. |
| `systemctl cat shop.slice` and `cat /sys/fs/cgroup/shop.slice/cpu.max` | The parent slice. | A second cap: 10%. Removing only the service quota would still leave the slice limit. |
| `rm .../50-finops.conf; systemctl daemon-reload; systemctl restart shopapp` | Remove override, reload, restart. | Puts it back in `system.slice` with no quota. |
| `systemctl show shopapp -p Slice -p CPUQuotaPerSecUSec` | Effective values. | Verify `system.slice` and `infinity`. |
| `CPUWeight=` (alternative) | Relative share, only matters under contention. | Better than quotas for fair sharing; quotas throttle even when the CPU is idle. |
| `grep nr_throttled .../cpu.stat` | Re-read counter. | Must stay at 0 after the fix. |
""",
}
