# Command Guide - Linux Troubleshooting

Every command used in the labs, explained. For each one: **what it answers**, the
**flags that matter**, **how to read the output**, and **traps**. Lab IDs in brackets
show where you practise it.

Tip: `man <command>` is the full reference; `<command> --help` is the short one;
`tldr <command>` (if installed) gives examples.

**Reading a long command.** Never type a long command in one go. Start with the bare command, run it,
then add one flag or one `|` at a time and run it again after each step:

```bash
du /var/log                          # bare: works, but noisy
du -h /var/log                       # + human sizes
du -h --max-depth=1 /var/log         # + one level deep
du -xh --max-depth=1 /var/log | sort -h   # + stay on one filesystem, + sort: biggest last
```

Each lab README has a **Warm-up** section with these ladders for the commands that lab uses.

## Contents

0. [The first 60 seconds](#0-the-first-60-seconds)
1. [Services and logs - systemd & journal](#1-services-and-logs)
2. [Processes](#2-processes)
3. [CPU and load](#3-cpu-and-load)
4. [Memory and the OOM killer](#4-memory-and-the-oom-killer)
5. [Disk space and inodes](#5-disk-space-and-inodes)
6. [Disk I/O performance](#6-disk-io-performance)
7. [Filesystems and mounts](#7-filesystems-and-mounts)
8. [Files, permissions and users](#8-files-permissions-and-users)
9. [Open files, file descriptors and limits](#9-open-files-file-descriptors-and-limits)
10. [Networking](#10-networking)
11. [DNS](#11-dns)
12. [Firewall](#12-firewall)
13. [Scheduled jobs - cron and timers](#13-scheduled-jobs)
14. [Tracing - strace](#14-tracing)
15. [Text tools you use while troubleshooting](#15-text-tools)
16. [SSH](#16-ssh)
17. [Time and clocks](#17-time-and-clocks)
18. [Exit codes and environments](#18-exit-codes-and-environments)
19. [Memory pressure, swap and process states](#19-memory-pressure-swap-and-process-states)
20. [Log rotation](#20-log-rotation)
21. [TLS certificates](#21-tls-certificates)
22. [Advanced networking - netns, ports, MTU, conntrack](#22-advanced-networking)
23. [NFS and stuck (D-state) processes](#23-nfs-and-stuck-d-state-processes)
24. [cgroups and resource limits](#24-cgroups-and-resource-limits)
25. [Symptom -> first commands cheat sheet](#25-symptom---first-commands)

---

## 0. The first 60 seconds

Log in to a sick box and run these, in this order, before you form any theory.
(Adapted from Brendan Gregg's "Linux performance analysis in 60 seconds".)

```bash
uptime                      # load averages: is it busy? getting better or worse?
dmesg -T | tail -20         # kernel errors: OOM kills, disk errors, fs errors
journalctl -p err -b --since "1 hour ago" --no-pager | tail -30   # recent errors from everything
systemctl --failed          # which units are broken
vmstat 1 5                  # CPU, run queue, blocked tasks, swap, IO wait
free -m                     # memory and swap
df -h ; df -i               # space and inodes on every filesystem
iostat -xz 1 3              # per-disk utilisation and latency
ss -s ; ss -ltnp            # socket summary; what listens where
top                         # who is using it all (press q to quit)
```

You now have a picture of CPU, memory, disk, network and errors. Then go deep where it looks wrong.

---

## 1. Services and logs

Modern Linux (Ubuntu, RHEL, Debian...) uses **systemd** to start and supervise services
("units") and **journald** to collect their logs.

### `systemctl status <unit>` [E02 E03 E05 M04 H05]

**Answers:** is the service running, since when, what is its main PID, why did it stop, last log lines.

```bash
systemctl status nginx
systemctl status nginx --no-pager -l     # don't page, don't cut long lines
systemctl status 2345                    # which unit owns PID 2345?
```

Reading the output:

```
● nginx.service - A high performance web server
     Loaded: loaded (/lib/systemd/system/nginx.service; enabled; preset: enabled)
     Active: failed (Result: exit-code) since Tue 2026-11-10 09:12:01 UTC; 2min ago
    Process: 1234 ExecStartPre=/usr/sbin/nginx -t -q (code=exited, status=1/FAILURE)
   Main PID: 1100 (code=exited, status=0/SUCCESS)
```

| Field | Meaning |
|-------|---------|
| `Loaded: ...; enabled` | unit file path; `enabled` = starts at boot |
| `Active: active (running)` | healthy |
| `Active: failed` | it stopped with an error - read `Result:` |
| `Active: activating (auto-restart)` | crashed and systemd will restart it - a crash loop |
| `Result: exit-code` / `oom-kill` / `signal` / `timeout` | **how** it died |
| `status=217/USER`, `203/EXEC`, `200/CHDIR` | systemd failed **before** running the program (bad user, bad path, bad dir) |
| `TriggeredBy:` | a `.timer` or `.socket` starts this service |
| `Drop-In:` | override files that change the unit (see `systemctl cat`) |

### `systemctl start | stop | restart | reload | enable | disable` [all]

```bash
sudo systemctl restart shopapp       # stop + start (drops connections)
sudo systemctl reload nginx          # re-read config, keep running (if the service supports it)
sudo systemctl enable --now nginx    # start at boot AND start now
sudo systemctl disable --now legacy-status   # don't start at boot AND stop now
sudo systemctl daemon-reload         # re-read unit files and /etc/fstab after you edit them
sudo systemctl reset-failed          # clear "failed" state (and start-rate limits)
```

**Traps:** `stop` without `disable` -> it comes back at reboot. Editing a unit without
`daemon-reload` -> systemd still uses the old version (it warns you in `status`).

### `systemctl cat <unit>` [H01 H05]

**Answers:** what is the *effective* configuration - the main unit file **plus every drop-in**, each with its path.

```bash
systemctl cat shopapp
# # /etc/systemd/system/shopapp.service
# ...
# # /etc/systemd/system/shopapp.service.d/10-limits.conf
# [Service]
# LimitNOFILE=64
```

Drop-ins live in `/etc/systemd/system/<unit>.d/*.conf` and override the main file.
They are easy to miss with `cat /etc/systemd/system/shopapp.service`. Always use `systemctl cat`.

Make your own override safely: `sudo systemctl edit shopapp` (creates a drop-in; never edit
files in `/lib/systemd/system` - package updates overwrite them). `systemd-delta` lists all overrides on the box.

### `systemctl show -p <Property> <unit>`

**Answers:** one exact property, machine-readable. Great for scripts and for limits.

```bash
systemctl show -p MainPID --value shopapp
systemctl show -p User -p Group shopapp
systemctl show -p NRestarts cache-warmer           # how many times systemd restarted it
systemctl show -p MemoryMax -p MemoryCurrent cache-warmer
systemctl show -p LimitNOFILE shopapp
```

### `systemctl --failed`, `list-units`, `list-dependencies`, `list-timers` [H05 H04 M03]

```bash
systemctl --failed                          # all failed units - the first thing after a reboot problem
systemctl list-units --type=service --state=running
systemctl list-dependencies shopapp         # tree of what shopapp needs (failed ones in red)
systemctl list-timers --all                 # scheduled timers: next run, last run, which service
```

### `journalctl` [all]

**Answers:** what did the service / kernel / system log.

```bash
journalctl -u nginx                     # one unit
journalctl -u nginx -n 50 --no-pager    # last 50 lines, print directly
journalctl -u shopapp -f                # follow live (like tail -f)
journalctl -u cron --since "10 min ago" # time filter; also "2026-11-10 09:00", "yesterday"
journalctl -b                           # since this boot;  -b -1 = previous boot
journalctl -k                           # kernel messages only (same as dmesg)
journalctl -p err                       # priority err and worse (emerg, alert, crit, err)
journalctl -t shopapp-backup            # by tag (what `logger -t` writes)
journalctl -xe                          # end of log with explanations (-x) - after a failed start
```

| Flag | Meaning |
|------|---------|
| `-u UNIT` | only this unit |
| `-n N` | last N lines |
| `-f` | follow |
| `--since / --until` | time window |
| `-b [N]` | boot (0 = current, -1 = previous) |
| `-k` | kernel ring buffer |
| `-p LEVEL` | minimum priority |
| `-o short-iso` / `-o json` | output format |
| `--no-pager` | don't open `less` |

**Traps:** many apps also write their own log files (`/var/log/nginx/`, `/var/log/shopapp/`). Check both.
Without persistent journal (`/var/log/journal`), logs from before a reboot are gone.

### `dmesg` [M04 H02]

**Answers:** what the kernel said: OOM kills, disk/IO errors, filesystem errors, network link up/down, segfaults.

```bash
sudo dmesg -T | tail -30         # -T = human timestamps
sudo dmesg -T -l err,warn        # only errors and warnings
sudo dmesg -w                    # follow
```

Key messages: `Out of memory: Killed process`, `Memory cgroup out of memory`,
`EXT4-fs error`, `Remounting filesystem read-only`, `I/O error, dev sda`, `segfault at`.

### `logger` [M05]

Write a line into the system log from a script: `logger -t mytag "backup ok"`. Read it with `journalctl -t mytag`.

---

## 2. Processes

### `ps` [M03 M04 H04 H05]

**Answers:** what processes exist right now and their state.

```bash
ps aux                                   # all processes, BSD style
ps -ef                                   # all processes, with PPID (parent)
ps -fp 2345                              # one PID, full command line
ps -eo pid,ppid,user,ni,%cpu,%mem,rss,stat,etime,cmd --sort=-%cpu | head    # custom columns
ps -o pid,rss,cmd -C python3             # by command name
ps -o unit= -p 2345                      # which systemd unit
ps -eo pid,stat,wchan:20,cmd | awk '$2 ~ /D/'   # tasks blocked in the kernel (usually disk IO)
```

| Column | Meaning |
|--------|---------|
| `PID / PPID` | process id / parent's id |
| `NI` | nice value: -20 (highest priority) to 19 (lowest) |
| `%CPU` | CPU share (100 = one full core) |
| `RSS` | resident memory in KB (really in RAM) |
| `VSZ` | virtual size - usually not useful |
| `ETIME` | how long it has run |
| `STAT` | state - see below |
| `WCHAN` | kernel function it is sleeping in |

`STAT` letters: `R` running/runnable · `S` sleeping (normal) · `D` uninterruptible sleep
(waiting for IO - can't be killed until IO finishes) · `Z` zombie (dead, parent didn't reap) ·
`T` stopped · `<` high priority · `N` low priority (niced) · `s` session leader · `l` multi-threaded · `+` foreground.

### `top` / `htop` [M03 H04 H01]

**Answers:** live view of the busiest processes and system-wide CPU/memory.

```bash
top                  # inside: P = sort by CPU, M = by memory, 1 = per-CPU lines,
                     #         c = full command, k = kill, q = quit
top -o %MEM          # start sorted by memory
top -p 2345          # one process
htop                 # friendlier, F5 = tree view, F6 = sort
```

The CPU header line - **learn it by heart**:

```
%Cpu(s):  0.3 us,  6.0 sy, 49.0 ni,  0.0 id, 44.0 wa,  0.0 hi,  0.3 si,  0.0 st
```

| Field | Meaning | High means |
|-------|---------|-----------|
| `us` | user code, normal priority | app is CPU-bound |
| `sy` | kernel code | lots of syscalls, IO, networking, context switches |
| `ni` | user code of **niced** processes | low-priority batch work - usually harmless |
| `id` | idle | spare CPU |
| `wa` | idle **while waiting for IO** | disk (or NFS) bottleneck |
| `hi/si` | hardware / software interrupts | heavy network or device traffic |
| `st` | stolen by the hypervisor | noisy neighbour / undersized VM |

### `pgrep` / `pkill` / `kill` [M03]

```bash
pgrep -af shopapp-reindex                # list matching PIDs + command lines (ALWAYS run this first)
pkill -f '^/usr/bin/python3 /usr/local/bin/shopapp-reindex'   # kill by full command line
kill 2345                                # SIGTERM (15): ask nicely, process can clean up
kill -9 2345                             # SIGKILL: forced, no cleanup - last resort
kill -0 2345                             # signal 0: just tests if the PID exists
```

**Traps:** `pkill -f pattern` matches the **whole command line of every process**, including
your own `sudo pkill -f pattern` and editors with the file open. Look with `pgrep -af` first and anchor with `^`.
Killing a process does nothing lasting if systemd (`Restart=`), cron or a timer restarts it.

### `pstree` [M03]

**Answers:** who started this process? (the parent chain)

```bash
pstree -ps 4102          # -p show PIDs, -s show parents of this PID
# systemd(1)---cron(650)---cron(4098)---sh(4099)---flock(4100)---python3(4101)
pstree -p shopapp        # all processes of a user, as a tree
```

### `nice` / `renice` / `ionice`

```bash
nice -n 10 ./job.sh              # start with lower CPU priority
sudo renice -n 19 -p 2345        # change a running process
ionice -c3 -p 2345               # IO class idle: only use disk when nobody else does
ionice -p 2345                   # show IO class
```

### `/proc/<PID>/` - the process's own view

| Path | What |
|------|------|
| `/proc/PID/cmdline` | full command line (`tr '\0' ' ' < /proc/PID/cmdline`) |
| `/proc/PID/status` | state, memory (VmRSS), threads, uid |
| `/proc/PID/limits` | the limits that apply to **this** process |
| `/proc/PID/fd/` | one symlink per open file descriptor |
| `/proc/PID/cwd` | current directory (blocks `umount` too!) |
| `/proc/PID/environ` | environment (`tr '\0' '\n' < ...`) |

---

## 3. CPU and load

### `uptime` [M03 H04]

```
 09:15:02 up 3 days,  2:01,  1 user,  load average: 2.10, 1.80, 1.05
```

The three numbers = average number of tasks **running or waiting to run, plus tasks in `D` state**,
over 1, 5 and 15 minutes. Compare with the CPU count (`nproc`):

- load ≈ nproc -> fully busy, ok · load >> nproc -> queueing, slow
- 1-min > 15-min -> getting worse · 1-min < 15-min -> recovering
- High load but low CPU usage -> tasks in `D` state -> look at disk IO (`vmstat` `b` column)

### `nproc`, `lscpu`

`nproc` = number of CPUs available. `lscpu` = model, cores, threads, NUMA.

### `vmstat` [H04]

**Answers:** whole-system CPU, memory, swap, IO in one line per second.

```bash
vmstat 1 5          # every 1 second, 5 samples (ignore the first line - it's the average since boot)
```

```
procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
 1  1      0 1203412 40212 512344    0    0     0  3900  950 1900  0  6  0 44  0
```

| Column | Meaning | Watch for |
|--------|---------|-----------|
| `r` | runnable tasks | > nproc = CPU saturation |
| `b` | blocked tasks (D state) | > 0 for long = IO problem |
| `si/so` | swap in/out per second | > 0 constantly = memory pressure |
| `bi/bo` | blocks in/out (KB/s) | disk traffic |
| `cs` | context switches/s | very high = lock contention, too many threads |
| `us sy id wa st` | CPU % | same as `top` |

### `mpstat` / `pidstat` (package `sysstat`)

```bash
mpstat -P ALL 1 3       # per-CPU usage: is one core at 100% (single-threaded app)?
pidstat 1 5             # CPU per process over time
pidstat -d 1 5          # disk IO per process (see section 6)
pidstat -r 1 5          # memory/page faults per process
```

### `sar` - history

`sysstat` records stats every 10 minutes. You can look at **the past** - when did it start?

```bash
sar -u                  # CPU today
sar -q                  # load / run queue
sar -r                  # memory
sar -d                  # disks
sar -n DEV              # network interfaces
sar -u -f /var/log/sysstat/sa09     # day 09 of the month
```

---

## 4. Memory and the OOM killer

### `free` [M04]

```bash
free -m          # in MB;  free -h = human units
```

```
               total        used        free      shared  buff/cache   available
Mem:            1967         420         950           1         600        1400
Swap:           2047           0        2047
```

Read **`available`**, not `free`. Linux uses spare RAM as disk cache (`buff/cache`) and gives it
back when apps need it. Low `available` + swap in use + `si/so` in vmstat = real pressure.

### Who uses memory?

```bash
ps aux --sort=-rss | head              # biggest RSS first
ps -o pid,rss,cmd -C python3
systemctl show -p MemoryCurrent cache-warmer     # memory of a whole service (cgroup)
systemd-cgtop                          # live: CPU/memory per cgroup (per service)
cat /proc/meminfo                      # every detail
watch -n1 'systemctl show -p MemoryCurrent cache-warmer'   # growing in a straight line = leak
```

### The OOM killer [M04]

When memory runs out the kernel kills a process to survive. Two kinds:

| Kind | Kernel log | Cause |
|------|-----------|-------|
| Global OOM | `Out of memory: Killed process 1234 (java)` | the whole machine is out of RAM+swap |
| cgroup OOM | `Memory cgroup out of memory: Killed process ...` and `constraint=CONSTRAINT_MEMCG` | the process hit **its service's** limit (`MemoryMax=`, container limit) |

```bash
journalctl -k | grep -iE 'oom|killed process'
sudo dmesg -T | grep -i -A5 'out of memory'
systemctl status cache-warmer        # Result: oom-kill
```

**Trap:** a cgroup OOM happens while `free -m` shows plenty of RAM. The limit is per service.
Raising the limit hides a leak; find why it grows.

---

## 5. Disk space and inodes

### `df` [E01 M01 M02]

**Answers:** how full is each **filesystem**.

```bash
df -h                      # human sizes
df -h /var/log/shopapp     # only the filesystem that holds this path
df -i                      # INODES instead of blocks
df -hT                     # add filesystem type
df --output=pcent,ipcent /srv/shopdata
```

- Out of **blocks** -> `Use%` 100%. Out of **inodes** -> `IUse%` 100%. Both give `No space left on device`.
- ext4 keeps ~5% reserved for root: a non-root app sees "full" at 95% `Use%`.

### `du` [E01 M01 M02]

**Answers:** how much space do these **files/directories** use (it adds up names it can see).

```bash
sudo du -sh /var/log/*                    # -s summary per argument, -h human
sudo du -xh --max-depth=1 / | sort -h     # -x stay on one filesystem, biggest last
sudo du --inodes -x /srv/shopdata | sort -n | tail   # count files instead of bytes
```

**`df` and `du` disagree?**
- `df` much bigger than `du` -> **deleted files still held open** (M01), or files hidden **under a mount point**
  (data written to `/mnt/x` before something was mounted on top).
- Use `-x` so `du` doesn't wander into other mounted filesystems.

### `find` [E01 M02]

```bash
sudo find /var/log -xdev -type f -size +100M -exec ls -lh {} +      # files > 100 MB
sudo find /srv/shopdata/sessions -type f -mmin +1440 | wc -l        # older than 24h - COUNT first
sudo find /srv/shopdata/sessions -type f -mmin +1440 -delete        # then delete
sudo find / -xdev -newer /etc/hostname -type f 2>/dev/null          # files changed after X
sudo find /proc/*/fd -lname '*(deleted)' -printf '%p -> %l\n' 2>/dev/null   # deleted-but-open
```

| Test | Meaning |
|------|---------|
| `-type f / d / l` | file / directory / symlink |
| `-size +100M` | bigger than 100 MiB (`k`, `M`, `G`) |
| `-mtime +7` | modified more than 7×24h ago; `-mmin` = minutes |
| `-name 'sess_*'` | name glob (quote it!) |
| `-xdev` | don't cross into other filesystems |
| `-delete` | delete matches - **must be last**, test without it first |

### `truncate` / `: >` [E01 M01]

```bash
sudo truncate -s 0 /var/log/big.log      # empty a file in place - safe even if a process has it open
sudo sh -c ': > /proc/3120/fd/3'         # empty a DELETED file through the process's fd
```

### `ncdu` (optional)

Interactive `du`: `sudo ncdu -x /`. Great on a full disk if installed.

---

## 6. Disk I/O performance

### `iostat` (sysstat) [H04]

**Answers:** how busy and how slow is each disk.

```bash
iostat -xz 1 3        # -x extended, -z hide idle devices, every 1s, 3 times
```

```
Device   r/s    w/s   rkB/s   wkB/s  r_await w_await aqu-sz  %util
sda      0.0  950.0     0.0  3800.0     0.0     1.0    0.95   98.0
```

| Column | Meaning |
|--------|---------|
| `r/s`, `w/s` | IO operations per second (IOPS) |
| `rkB/s`, `wkB/s` | throughput |
| `r_await`, `w_await` | average ms per IO **including queue time** - latency users feel |
| `aqu-sz` | average queue length - saturation |
| `%util` | % of time the device was busy. ~100% on a single disk = saturated (on SSD/RAID arrays it can be misleading; trust `await`) |

High `%util` with low `kB/s` and high `w/s` -> many tiny (often synchronous) writes.

### `pidstat -d` and `iotop` [H04]

```bash
sudo pidstat -d 1 5       # kB_rd/s kB_wr/s iodelay per process
sudo iotop -o             # live, only processes doing IO (-o); -P per process, -a accumulated
```

### Blocked tasks

`vmstat` column `b`, `ps` state `D`, and `top` `wa` all point to IO waits.
`cat /proc/PID/wchan` or `ps -o wchan:30` tells you where in the kernel it waits.

---

## 7. Filesystems and mounts

### `findmnt` / `mount` / `lsblk` / `blkid` [H02 H05]

```bash
findmnt /srv/shopdata              # source device, fs type, OPTIONS (rw/ro!)
findmnt -no OPTIONS /srv/shopdata
findmnt --verify                   # sanity check /etc/fstab
mount | column -t                  # all mounts (older style)
lsblk -f                           # disks, partitions, fs type, UUID, LABEL, mount point
sudo blkid                         # UUID/LABEL/TYPE of block devices - compare with fstab
```

### `/etc/fstab` [H05]

```
# <source>                     <mountpoint>   <type> <options>                        <dump> <pass>
UUID=3f1c...                   /data          ext4   defaults,nofail                  0      2
/var/lib/tshoot/shopdata.img   /srv/shopdata  ext4   loop,defaults,nofail,errors=remount-ro 0 2
```

- systemd turns each line into a `.mount` unit (`/srv/shopdata` -> `srv-shopdata.mount`;
  `systemd-escape -p --suffix=mount /srv/shopdata`). After edits: `sudo systemctl daemon-reload`.
- `nofail` = boot continues if it fails. Without it, a bad line can stop boot in **emergency mode**.
- Test without rebooting: `sudo mount -a` (mounts everything not mounted yet) and `findmnt --verify`.

### `mount` / `umount` [H02 H05]

```bash
sudo mount /srv/shopdata               # mount using the fstab line
sudo mount -o remount,rw /srv/x        # change options on a mounted fs (NOT a fix for errors)
sudo umount /srv/shopdata
# umount: target is busy  -> find who:
sudo fuser -vm /srv/shopdata           # processes using the filesystem (-k would kill them)
sudo lsof +f -- /srv/shopdata          # open files on it
```

Your own shell sitting in the directory (`cd /srv/shopdata`) also makes it busy. `cd /` first.
Avoid `umount -l` (lazy) before fsck - it only hides the mount; the fs is still in use.

### `e2fsck` / `dumpe2fs` / `tune2fs` (ext2/3/4) [H02]

```bash
sudo dumpe2fs -h /dev/sdb1 | grep -iE 'state|error|mount count'   # superblock info
#   Filesystem state: clean with errors   <- needs fsck
sudo e2fsck -n /dev/sdb1     # read-only check, changes nothing (safe dry run)
sudo e2fsck -f /dev/sdb1     # force full check, asks before each fix
sudo e2fsck -fy /dev/sdb1    # answer yes to everything (know what you are doing)
sudo tune2fs -l /dev/sdb1    # same info as dumpe2fs -h;  tune2fs -e remount-ro sets error behaviour
```

**Never run fsck on a mounted filesystem.** Run it twice: the second run must be clean.
After fsck, check `lost+found/` and compare data with backups. XFS uses `xfs_repair` instead.

### `debugfs` (expert)

Low-level ext4 debugger. The lab uses it to simulate corruption. Read-only use:
`sudo debugfs -R 'stat /path' /dev/sdb1`. Don't use `-w` on real data.

---

## 8. Files, permissions and users

### `ls -l` / `stat` [E03]

```
-rw-r----- 1 root shopapp 180 Nov 10 09:00 config.ini
│└┬┘└┬┘└┬┘   └┬─┘ └──┬──┘
│ │  │  │     │      └ group owner
│ │  │  │     └ user owner
│ │  │  └ other: ---
│ │  └ group: r--
│ └ user: rw-
└ type: - file, d dir, l symlink
```

| Bit | On a file | On a directory |
|-----|-----------|----------------|
| `r` (4) | read content | list names (`ls`) |
| `w` (2) | change content | create / delete / rename entries |
| `x` (1) | execute | **enter / pass through** (`cd`, open files inside) |

`stat file` shows mode in octal (`0640`), owner, size, inode, link count and timestamps.

### `namei -l` [E03]

**Answers:** permissions of **every component** of a path. Finds the directory that blocks you.

```bash
namei -l /etc/shopapp/config.ini
# drwxr-xr-x root root /
# drwxr-xr-x root root etc
# drwx------ root root shopapp     <- no x for others: nobody but root can reach config.ini
# -rw------- root root config.ini
```

### `chmod` / `chown` / `chgrp` [E03 M05]

```bash
sudo chown root:shopapp /etc/shopapp/config.ini    # user:group
sudo chmod 0640 /etc/shopapp/config.ini            # rw- r-- ---
sudo chmod 0755 /usr/local/bin/script              # rwx r-x r-x (executable)
sudo chmod g+r,o-rwx file                          # symbolic form
sudo chown -R shopapp: /srv/shopdata               # recursive, group = user's primary group
```

Common modes: `0644` normal file · `0640` secret readable by a group · `0600` private · `0755` dir or program · `0700` private dir.
**Never `chmod 777`.**

### `id`, `getent`, `sudo -u` [E03 H05]

```bash
id shopapp                          # uid, gid, groups
getent passwd shopapp               # does the user exist? (works with LDAP too, unlike grep /etc/passwd)
getent group shopapp
sudo -u shopapp cat /etc/shopapp/config.ini     # TEST AS THE SERVICE USER
sudo -u shopapp test -r /etc/shopapp/config.ini && echo can-read
```

Root bypasses file permissions, so "it works for me with sudo" proves nothing. Test as the real user.

### Other permission layers

If modes look right and it still fails: ACLs (`getfacl file`; a `+` at the end of `ls -l` mode),
SELinux (`getenforce`, `ls -Z`, `ausearch -m avc`), AppArmor (`aa-status`, `journalctl -k | grep apparmor`),
`noexec` mount option (`findmnt -no OPTIONS`), immutable flag (`lsattr`).

---

## 9. Open files, file descriptors and limits

Everything a process has open - files, sockets, pipes - is a **file descriptor (fd)**, a small number.
0 = stdin, 1 = stdout, 2 = stderr.

### `lsof` [E01 E05 M01 H01]

```bash
sudo lsof -p 2345                   # all open files of a process
sudo lsof /var/log/app.log          # who has this file open
sudo lsof +L1                       # open files with link count 0 = DELETED but still open
sudo lsof -nP +L1 /var/log/shopapp  # same, only that filesystem; -n -P = no DNS/port name lookups (faster)
sudo lsof -i :80                    # who uses port 80
sudo lsof -u shopapp                # files open by a user
```

`lsof +L1` columns: `COMMAND PID USER FD TYPE ... SIZE/OFF NLINK NAME (deleted)` -
`SIZE/OFF` is how much space it still holds; `FD` like `3w` = fd 3, open for writing.

### `/proc/<PID>/fd` and `/proc/<PID>/limits` [H01 M01]

```bash
sudo ls -l /proc/2345/fd                    # each fd -> what it points to
sudo ls /proc/2345/fd | wc -l               # how many are open
sudo ls -l /proc/2345/fd | awk '{print $NF}' | sort | uniq -c | sort -rn | head   # most repeated target = leak
cat /proc/2345/limits                       # Max open files  <soft>  <hard>
```

### `ulimit` / `prlimit` / systemd `Limit*`

```bash
ulimit -n                         # fd limit of YOUR SHELL (not of services!)
prlimit -p 2345 --nofile          # see/change limits of a running process
systemctl show -p LimitNOFILE shopapp
```

Services started by systemd get limits from the unit (`LimitNOFILE=`), **not** from
`/etc/security/limits.conf` (that file is for login sessions).

---

## 10. Networking

### `ip` (iproute2) [H03]

```bash
ip addr  (ip a)                   # interfaces and their IPs; look for state UP
ip -br a                          # brief one-line-per-interface view
ip link                           # link layer: UP/DOWN, MTU, MAC
ip route  (ip r)                  # routing table; "default via X" = gateway
ip route get 10.200.0.2           # which route/interface/source IP the kernel would use
ip neigh                          # ARP table: FAILED/INCOMPLETE = no L2 reply
ip -s link show eth0              # packet / error / drop counters
```

Network namespaces (containers use these) [H03]:

```bash
ip netns list
sudo ip netns exec app-ns ip a                # run any command inside a namespace
sudo ip -n app-ns route                       # short form for ip commands
sudo ip -n app-ns route add default via 10.200.0.1
```

### `ss` [E02 E05 H03]

**Answers:** which sockets exist: who listens on which port, which connections are open. (Replaces `netstat`.)

```bash
sudo ss -ltnp                   # -l listening, -t TCP, -n numeric, -p process
sudo ss -lunp                   # UDP listeners
sudo ss -ltnp 'sport = :80'     # filter by port
ss -tn state established        # open TCP connections
ss -s                           # summary: totals, TIME-WAIT count
```

Reading `LISTEN 0 511 127.0.0.1:8080 0.0.0.0:* users:(("python3",pid=900,fd=3))`:
listens only on **127.0.0.1** (local only!) port 8080, owned by PID 900. `0.0.0.0` / `*` = all IPs.
`Recv-Q` growing on a LISTEN socket = app not accepting fast enough (backlog full).

### `ping`, `tracepath` / `traceroute`, `mtr`

```bash
ping -c3 10.200.0.2             # L3 reachability + latency. -W1 = 1s timeout
traceroute -n 10.200.0.2        # each router hop; * * * = no answer there (could be filtering)
tracepath 10.200.0.2            # also finds path MTU, no root needed
mtr -n 8.8.8.8                  # ping + traceroute live, shows loss per hop
```

**Trap:** ping uses ICMP. Ping OK but TCP fails = a firewall filtering by port (H03). Ping failing does not
always mean down - many hosts block ICMP.

### `curl` [all]

```bash
curl -v http://localhost/                    # verbose: DNS, connect, request, response headers
curl -sI https://example.com                 # headers only
curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' http://localhost/   # status + time
curl --max-time 5 ...                        # don't hang forever
curl --resolve example.com:443:1.2.3.4 https://example.com/   # bypass DNS for one test
```

Error -> layer: `Could not resolve host` (DNS) · `Connection refused` (no listener) ·
`Connection timed out` (filtered / routing) · `SSL certificate problem` (TLS) · HTTP 5xx (app/proxy).

### `nc` (netcat)

`nc -zv 10.200.0.2 9000` - is the TCP port open? Fast port test when curl isn't available.

### `tcpdump` [H03]

**Answers:** what packets actually go over an interface. The ground truth.

```bash
sudo tcpdump -ni h-ap                          # -n no name lookups, -i interface
sudo tcpdump -ni any port 9000                 # one port on all interfaces
sudo tcpdump -ni eth0 host 10.201.0.2 and tcp
sudo tcpdump -ni eth0 icmp
sudo tcpdump -ni eth0 -c 50 -w /tmp/cap.pcap   # save 50 packets for Wireshark
```

How to use it: capture on each hop. **Request seen, no reply** -> the problem is on the reply side
(return route, firewall on the server). **Request not seen** -> problem is before this point.
TCP `[S]` repeated with no `[S.]` = SYN not answered (filtered / no route back). `[R]` = reset (port closed).

### `sysctl` [H03]

```bash
sysctl net.ipv4.ip_forward              # read a kernel setting
sudo sysctl -w net.ipv4.ip_forward=1    # change at runtime (lost at reboot)
echo 'net.ipv4.ip_forward = 1' | sudo tee /etc/sysctl.d/90-router.conf   # persist
sudo sysctl --system                    # reload all sysctl files
```

---

## 11. DNS

### `getent hosts` / `getent ahosts` [E04]

**Answers:** what an **application** gets when it resolves a name - uses `/etc/nsswitch.conf`
order (`files` = `/etc/hosts`, then `dns`).

```bash
getent hosts example.com
getent ahosts ubuntu.com
grep hosts /etc/nsswitch.conf       # hosts: files dns
```

### `dig` / `nslookup` [E04]

**Answers:** what a **DNS server** answers. Does **not** read `/etc/hosts`.

```bash
dig example.com                 # full answer; look at status: NOERROR / NXDOMAIN / SERVFAIL, and SERVER line
dig +short example.com          # just the IPs
dig @1.1.1.1 example.com        # ask a specific server - is MY resolver the problem?
dig @127.0.0.53 example.com     # ask systemd-resolved
dig -x 8.8.8.8                  # reverse lookup
dig example.com MX / NS / TXT   # other record types
```

| Result | Meaning |
|--------|---------|
| `connection timed out; no servers could be reached` | resolver unreachable/dead |
| `status: NXDOMAIN` | name does not exist |
| `status: SERVFAIL` | resolver failed (upstream, DNSSEC) |
| dig OK but app fails | check `/etc/hosts` and nsswitch -> `getent` |

### `/etc/resolv.conf` and `resolvectl` [E04]

```bash
ls -l /etc/resolv.conf      # on Ubuntu: symlink -> /run/systemd/resolve/stub-resolv.conf
cat /etc/resolv.conf        # nameserver 127.0.0.53 = systemd-resolved stub
resolvectl status           # the REAL upstream DNS servers per interface
resolvectl query ubuntu.com
sudo resolvectl flush-caches
```

---

## 12. Firewall

Linux filters packets in the kernel (netfilter). Front-ends: `iptables` (legacy syntax, still everywhere),
`nft` (nftables, modern), `ufw` (Ubuntu), `firewalld` (RHEL).

### `iptables` [H03]

```bash
sudo iptables -L -nv --line-numbers          # all chains of the filter table, with counters
sudo iptables -L FORWARD -nv --line-numbers  # one chain
sudo iptables -S                             # rules as commands (easy to copy / delete)
sudo iptables -t nat -L -nv                  # NAT table
sudo iptables -D FORWARD 1                   # delete rule number 1
sudo iptables -I INPUT -p tcp --dport 22 -j ACCEPT    # insert at top
sudo iptables -Z FORWARD                     # zero the counters, then re-test and watch them
```

Which chain sees my packet?

| Traffic | Chain |
|---------|-------|
| to this host (a local service) | `INPUT` |
| from this host | `OUTPUT` |
| **through** this host (router, containers, VMs) | `FORWARD` |

Read the `pkts` counter: re-run your test, the rule whose counter goes up is the one matching.
Also check the chain **policy** (`Chain FORWARD (policy DROP)`).

### `nft`, `ufw`, `firewalld`

```bash
sudo nft list ruleset
sudo ufw status verbose
sudo firewall-cmd --list-all
```

Runtime rules are lost at reboot unless saved (`iptables-save > /etc/iptables/rules.v4` with
`iptables-persistent`, `/etc/nftables.conf`, ufw/firewalld manage their own).

---

## 13. Scheduled jobs

### cron [M02 M03 M05]

```bash
crontab -l                      # current user's crontab;  sudo crontab -l -u shopapp
ls -l /etc/cron.d/ ; cat /etc/crontab
grep -r jobname /etc/cron* /var/spool/cron 2>/dev/null     # where is it scheduled?
journalctl -u cron --since "1 hour ago"                     # every run is logged (Ubuntu: cron; RHEL: crond)
```

Line format:

```
# m   h  dom mon dow  [user]  command
 30   2   *   *   *    root   /usr/local/bin/backup        <- /etc/crontab and /etc/cron.d have a USER column
*/5   *   *   *   *           /path/job                    <- user crontabs (crontab -e) do NOT
```

Why cron jobs "silently" don't run:

- File in `/etc/cron.d` has a `.` in its name (ignored) or is group/world writable / not owned by root (rejected - logged as `INSECURE MODE` / `WRONG FILE OWNER`)
- Missing user column in `/etc/cron.d`, or missing newline at the end of the file
- Script not executable, or relies on your shell's `PATH` / environment (cron's PATH is minimal: `/usr/bin:/bin`)
- `%` in the command (means newline to cron - escape as `\%`)
- Output is mailed - with no mail server it is thrown away. Redirect: `>> /var/log/job.log 2>&1`

Test a job like cron runs it: `sudo -u <user> env -i PATH=/usr/bin:/bin /path/to/script`.

### systemd timers [H04]

```bash
systemctl list-timers --all             # NEXT, LEFT, LAST, PASSED, UNIT, ACTIVATES
systemctl cat audit-sync.timer          # OnCalendar=, OnUnitInactiveSec= ...
systemctl status audit-sync.service     # look for TriggeredBy:
sudo systemctl disable --now audit-sync.timer   # stop the schedule (stop the service separately)
journalctl -u audit-sync.service
```

---

## 14. Tracing

### `strace` [H01]

**Answers:** which system calls a process makes and which ones fail - when logs say nothing.

```bash
sudo strace -f -p 2345                      # attach to running process (+ threads/children with -f)
sudo strace -f -p 2345 -e trace=openat,close,accept4   # only these syscalls
sudo strace -f -e trace=file ./program      # file-related calls of a new program
sudo strace -f -o /tmp/st.txt -p 2345       # write to a file
sudo strace -c -p 2345                      # summary: count and time per syscall (Ctrl-C to stop)
strace -f -e trace=%network curl -s localhost
```

Reading: `openat(AT_FDCWD, "/etc/shopapp/config.ini", O_RDONLY) = -1 EACCES (Permission denied)` -
the call, args, return value and the errno. Look for `= -1 E...`.

**Trap:** strace slows the process a lot. Short captures only on production.

---

## 15. Text tools

| Command | Use |
|---------|-----|
| `tail -n 50 file`, `tail -f file` | end of a file, follow live |
| `less +F file` | follow; Ctrl-C to scroll, `/` to search |
| `grep -i -n -E 'err|fail' file` | search (`-i` ignore case, `-n` line numbers, `-E` regex, `-r` recursive, `-v` invert, `-A3/-B3` context) |
| `awk '{print $1}'` | pick a column |
| `sort | uniq -c | sort -rn` | count duplicates, most common first |
| `wc -l` | count lines |
| `sort -h` | sort human sizes (`du -h` output) |
| `watch -n1 'cmd'` | re-run a command every second |
| `sed -i 's/a/b/' file` | in-place edit - **make a backup first** (`cp file file.bak`) |
| `diff -u a b` | compare a config with its backup |
| `column -t` | align columns |
| `tee` | write to file and screen; `echo x | sudo tee file` writes as root |

Example - top 5 IPs hitting nginx:

```bash
awk '{print $1}' /var/log/nginx/shopapp.access.log | sort | uniq -c | sort -rn | head -5
```

---

## 16. SSH

### `ssh -v` [E06]
Client-side debug. Answers: did we connect, which keys were offered, which auth methods the
server allows.

```bash
ssh -v -i KEY user@host            # -vv / -vvv for more
# debug1: Offering public key: KEY ED25519 SHA256:...
# debug1: Authentications that can continue: publickey     <- key offered and refused
```

Trap: the client **never** learns *why* a key was refused. That is in the server log.

### Server side: `journalctl -u ssh`, `sshd -t`, `sshd -T` [E06]

```bash
journalctl -u ssh -n 30          # unit is "ssh" on Ubuntu, "sshd" on RHEL
# Authentication refused: bad ownership or modes for directory /home/deploy
sudo sshd -t                     # syntax-check sshd_config - ALWAYS before restarting sshd
sudo sshd -T | grep -i strictmodes   # effective config after all includes
```

`StrictModes yes` (default) refuses keys when home, `~/.ssh` or `authorized_keys` are
writable by others. Correct modes: home `755`/`750`, `~/.ssh` `700`, `authorized_keys` `600`.

Safety: keep a second session open while you change sshd - a broken config can lock you out.

---

## 17. Time and clocks

### `timedatectl` [E07]

```bash
timedatectl
#                Local time: ...
#            Universal time: ...
#                 Time zone: America/Los_Angeles (PST, -0800)
# System clock synchronized: no          <- NTP has not synced
#               NTP service: inactive    <- sync turned off
sudo timedatectl set-timezone Etc/UTC
sudo timedatectl set-ntp true
timedatectl timesync-status      # systemd-timesyncd: server, offset, poll interval
chronyc tracking                 # if the host uses chrony instead
date; date -u                    # local vs UTC
```

- Timezone only changes **display**; a wrong **clock** is really wrong (breaks TLS, Kerberos, logs).
- Processes read the timezone at start - restart services after changing it.
- NTP uses UDP 123 - firewalls block it surprisingly often.

---

## 18. Exit codes and environments

### Exit codes [E08 E10 M04]

| Code | Meaning |
|------|---------|
| 0 | success |
| 1, 2 ... | program-specific error (read the program's docs / log) |
| 126 | command found but not executable (mode, `noexec` mount) |
| 127 | command not found (PATH!) |
| 128+N | killed by signal N: 137 = 9 (SIGKILL, often OOM), 143 = 15 (SIGTERM) |

`systemctl status` shows it as `status=127`; in a shell: `echo $?`.

### "Works in my shell, fails in systemd/cron" [E08]

```bash
type shopctl                     # where my shell finds it
systemctl show-environment       # PATH that services get
sudo cat /proc/<PID>/environ | tr '\0' '\n'     # env of a running process
sudo systemd-run --wait --pty -p User=shopapp /path/to/cmd   # run exactly like a service would
```

systemd and cron do **not** read `/etc/profile`, `/etc/profile.d/*`, `~/.bashrc`.
`sudo` uses `secure_path`. Scripts for machines: full paths, or set `PATH=` / `Environment=PATH=`.

### Run as the service user [E10 E03]

```bash
sudo -u shopapp /usr/bin/python3 /opt/shopapp/app.py      # debug as the right user
sudo -u shopapp test -w /var/log/shopapp/app.log && echo writable
```

Running a service by hand as root creates root-owned files the real service can't use.

---

## 19. Memory pressure, swap and process states

### `vmstat` swap columns, `swapon`, `VmSwap` [M06]

```bash
vmstat 1 5        # si = swapped in KB/s, so = swapped out KB/s
swapon --show     # swap devices/files and how full they are
free -m           # look at "available", and at Swap used
grep VmSwap /proc/[0-9]*/status | sort -k2 -n | tail     # who is swapped out
ps -eo pid,rss,cmd --sort=-rss | head
```

- Swap *used* alone is fine (idle pages parked). **Swap activity** (`si`/`so` > 0 every second) = thrashing.
- Thrashing: high load, high `wa`, idle CPU, everything slow.
- `vm.swappiness` (0-200, default 60): how eagerly the kernel swaps anonymous memory vs dropping cache.

### `sysctl` persistence [M06 H06 H08]

```bash
sysctl vm.swappiness                     # runtime value
sudo sysctl -w vm.swappiness=60          # change now (lost at reboot)
grep -r swappiness /etc/sysctl.conf /etc/sysctl.d/    # what comes back at boot
sudo sysctl --system                     # re-apply all files, prints each one
```

Trap: `sysctl.d` files don't support comments at the end of a line - put `#` comments on their own line.

### Zombies and task limits [M07]

```bash
ps -eo pid,ppid,stat,cmd | awk '$3 ~ /Z/'      # STAT Z = zombie (<defunct>)
systemctl status <unit> | grep Tasks          # Tasks: 150 (limit: 150)
systemctl show -p TasksMax -p TasksCurrent <unit>
```

Process `STAT` letters: `R` running, `S` sleeping, `D` uninterruptible (I/O, NFS), `Z` zombie,
`T` stopped. A zombie has exited; only its parent's `wait()` (or the parent's death) removes it.
`kill -9` on a zombie does nothing. Zombies use PIDs, so they count against `TasksMax`/`pid_max`.

---

## 20. Log rotation

### `logrotate` [M08]

```bash
sudo logrotate -d /etc/logrotate.d/shopapp        # dry run: shows decisions + errors
sudo logrotate -v -f /etc/logrotate.d/shopapp     # force a real rotation, verbose
cat /var/lib/logrotate/status                     # when each file was last rotated
systemctl list-timers logrotate.timer             # when it runs
```

Directives that matter:

| Directive | Meaning |
|-----------|---------|
| `daily` / `weekly`, `rotate 7` | how often, how many old files to keep |
| `size 50M` / `maxsize 50M` | rotate on size (maxsize: size *or* time) |
| `compress` + `delaycompress` | gzip old files, but not the newest one |
| `create 0640 user group` | rename the file, create a new empty one - app must reopen its log |
| `copytruncate` | copy, then truncate in place - for apps that never reopen (needs free space for the copy) |
| `postrotate ... endscript` | command after rotation, e.g. `systemctl reload app` |
| `su user group` | rotate as this user - needed when the log dir is writable by non-root |

Trap: after `create` + `compress`, an app that keeps its fd writes into a **deleted** file -
check `lsof +L1` after a rotation.

---

## 21. TLS certificates

### `openssl s_client` - what does the server serve? [M09]

```bash
openssl s_client -connect 127.0.0.1:443 -servername shop.lab.internal </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates -ext subjectAltName
```

- `-servername` sends SNI - without it you may get a different (default) certificate.
- `Verify return code: 0 (ok)` at the end of full `s_client` output = chain validated.

### `openssl x509` / `openssl pkey` - what is on disk? [M09]

```bash
openssl x509 -in cert.crt -noout -subject -enddate
openssl x509 -in cert.crt -noout -checkend 2592000 && echo "valid > 30 days"
# does this key belong to this cert? same hash = pair
openssl x509 -in cert.crt -noout -pubkey | sha256sum
openssl pkey -in key.key -pubout | sha256sum
sudo nginx -T | grep ssl_certificate              # which files nginx really uses
curl -v --cacert ca.crt https://host/             # client view incl. verification error
```

Private keys: `0600 root` (or `0640 root:<service-group>`). World-readable = assume leaked.

---

## 22. Advanced networking

### Test from somewhere else: `ip netns exec` [M10 H03 H07]

```bash
sudo ip netns list
sudo ip netns exec mon-ns curl -v http://10.210.0.1/   # run a command "on another machine"
sudo ip -n vpn-ns link                                 # ip commands inside a namespace
```

`curl localhost` skips the NIC, the firewall rules for other sources and the listen address.
Always reproduce from the user's side.

### Listen address [M10]

```bash
sudo ss -ltnp
# 0.0.0.0:80 / *:80 / [::]:80  -> all addresses
# 127.0.0.1:80                 -> local only: refused for everyone else
```

### Socket states and ephemeral ports [H06]

```bash
ss -s                                          # summary: estab, timewait, ...
ss -tan state time-wait | wc -l
ss -tan state time-wait | awk 'NR>1{print $5}' | sort | uniq -c | sort -rn | head   # by peer
sysctl net.ipv4.ip_local_port_range            # ports for outgoing connections
sysctl net.ipv4.tcp_tw_reuse                   # 2 = reuse for loopback (default), 1 = all outgoing
```

- Whoever closes a TCP connection first keeps it in **TIME_WAIT for 60 s** (fixed).
- New outgoing connections to one destination/s ≈ number of ports / 60.
- `EADDRNOTAVAIL` / "Cannot assign requested address" on connect = out of local ports.
- `tcp_fin_timeout` is FIN_WAIT_2, not TIME_WAIT. `tcp_tw_recycle` no longer exists.
- Real fix: connection reuse (HTTP keep-alive, connection pools).

### MTU and Path MTU Discovery [H07]

```bash
ip link | grep mtu
ping -M do -s 1472 HOST        # 1472 + 28 = 1500 bytes, DF set; error or silence?
ping -M do -s 1372 HOST        # 1400 bytes
tracepath -n HOST              # shows "pmtu" per hop (needs ICMP to come back)
tcpdump -ni IF 'icmp or tcp'   # look for retransmits of the same big segment
```

- `ping: local error: message too long, mtu=1400` = you were told the MTU (PMTUD works).
- No reply and no error for big packets = **black hole** (ICMP "frag needed" is dropped).
- Fixes: allow ICMP type 3 code 4; on tunnel gateways clamp MSS:
  `iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1360`.

### Connection tracking (conntrack) [H08]

```bash
sudo conntrack -C                               # entries now
sysctl net.netfilter.nf_conntrack_max           # limit
sudo conntrack -S                               # per-CPU: insert, drop, early_drop ...
sudo conntrack -L -p tcp | grep -o 'dport=[0-9]*' | sort | uniq -c | sort -rn | head
dmesg -T | grep conntrack                       # "nf_conntrack: table full, dropping packet"
```

Any stateful firewall rule (`-m conntrack`, `-m state`, NAT, Docker) makes the kernel track
every connection. Full table = new packets dropped = SYN retransmits (1 s, 3 s, 7 s ...).
Established connections keep working.

### `nc` / `/dev/tcp` - is a TCP port reachable? [H09]

```bash
nc -vz -w3 10.240.0.10 2049         # succeeded / timed out / refused
timeout 3 bash -c '</dev/tcp/10.240.0.10/2049' && echo open    # no nc installed
```

---

## 23. NFS and stuck (D-state) processes

### Find stuck tasks [H09]

```bash
ps -eo pid,stat,etime,wchan:32,cmd | awk 'NR==1 || $2 ~ /D/'
sudo cat /proc/<PID>/stack           # kernel stack: where it waits (sunrpc/nfs = NFS)
cat /proc/loadavg                    # D-state tasks count in the load average
```

High load + idle CPU + D-state tasks = waiting for storage (disk, NFS, iSCSI).

### Safe vs. unsafe commands on a dead NFS mount [H09]

| Safe (no server access) | Hangs on a `hard` mount |
|-------------------------|-------------------------|
| `findmnt -t nfs,nfs4`, `cat /proc/mounts`, `mount` | `df`, `ls`, `stat`, `du`, tab-completion in that path |
| `dmesg -T \| grep -i nfs` | anything that opens files there |

Wrap risky commands: `timeout -s KILL 5 df -h` (NFS waits react to SIGKILL, not SIGTERM).

```bash
sudo umount -f -l /mnt/reports       # last resort: force + lazy detach
```

### NFS mount options in `/etc/fstab` [H09]

| Option | Meaning |
|--------|---------|
| `hard` (default) | retry forever - safe for data, hangs processes during outages |
| `soft` | give up after `retrans` - processes get EIO, writes can be lost |
| `timeo=50,retrans=2` | 5 s per try, 2 retries before "server not responding" |
| `_netdev` | needs network - mount after the network is up |
| `nofail` | boot continues if the mount fails |
| `x-systemd.automount` | mount on first access instead of at boot |

---

## 24. cgroups and resource limits

### Who gets how much CPU? [H10 M04]

```bash
systemd-cgtop                                  # CPU/memory/tasks per cgroup, live
systemctl status shopapp | grep CGroup         # where the unit lives (which slice)
systemctl show shopapp -p Slice -p CPUQuotaPerSecUSec -p CPUWeight -p MemoryMax -p TasksMax
cat /sys/fs/cgroup/<path>/cpu.max              # "5000 100000" = 5 ms per 100 ms = 5%; "max 100000" = none
cat /sys/fs/cgroup/<path>/cpu.stat             # nr_throttled / throttled_usec growing = quota hit
```

- Limits stack: service -> slice -> parent slice. The tightest wins.
- `CPUQuota=` throttles always; `CPUWeight=` only matters when CPUs are contended.
- Throttling hides from host-level `top` - the host is idle while one cgroup waits.

### Find hidden changes to units [H10 H01 H05]

```bash
systemctl cat <unit>                           # unit + every drop-in, with file names
systemd-delta --type=extended,overridden       # all drop-ins/overrides on the host
```

---

## 25. Symptom -> first commands

| Symptom | First commands | Lab |
|---------|---------------|-----|
| Website down / connection refused | `systemctl status <svc>`, `journalctl -u <svc>`, `ss -ltnp` | E02 E05 |
| 502 Bad Gateway | backend: `systemctl status`, `curl localhost:<backend-port>`, backend logs | E03 H05 |
| 504 Gateway Timeout | backend hung: `top -p`, `/proc/PID/fd`, `/proc/PID/limits`, `strace -p` | H01 |
| "No space left on device" | `df -h`, `df -i`, `du -xh --max-depth=1`, `lsof +L1` | E01 M01 M02 |
| Deleted file, space not freed | `lsof +L1` | M01 |
| Permission denied | `namei -l <path>`, `sudo -u <svc-user> ...`, `id <user>` | E03 |
| Can't resolve names | `getent hosts`, `dig`, `dig @1.1.1.1`, `cat /etc/resolv.conf`, `resolvectl status` | E04 |
| Address already in use | `ss -ltnp 'sport = :<port>'`, `systemctl status <PID>` | E05 |
| High load / slow | `uptime`, `vmstat 1`, `top`, `iostat -xz 1`, `pidstat -d 1` | M03 H04 |
| Process keeps coming back | `pstree -ps <PID>`, `systemctl status <PID>`, cron, `list-timers` | M03 H04 |
| Service restarts in a loop | `systemctl status`, `systemctl show -p NRestarts`, `journalctl -u`, `journalctl -k \| grep -i oom` | M04 |
| Job didn't run | `journalctl -u cron`, `ls -l /etc/cron.d`, run it by hand as the job user | M05 |
| Too many open files | `ls /proc/PID/fd \| wc -l`, `cat /proc/PID/limits`, `systemctl cat` | H01 |
| Read-only file system | `findmnt`, `dmesg -T \| grep -i ext4`, `dumpe2fs -h`, then umount + `e2fsck` | H02 |
| Host can't reach host | `ip a`, `ip r`, `ip route get`, `ping`, `tcpdump`, `sysctl ip_forward`, `iptables -L -nv` | H03 |
| Not back after reboot | `systemctl --failed`, `list-dependencies`, `journalctl -b`, `/etc/fstab`, `systemctl is-enabled` | H05 |
| SSH key refused | `ssh -v`, `journalctl -u ssh`, `namei -l ~/.ssh/authorized_keys`, `sshd -T` | E06 |
| Wrong timestamps / clock | `timedatectl`, `timedatectl timesync-status`, `date -u` | E07 |
| Job works by hand, fails in systemd/cron (127) | `systemctl status`, `systemctl show-environment`, `type <cmd>` | E08 |
| Service gone after reboot | `systemctl is-enabled`, `systemctl cat` (`[Install]`) | E09 H05 |
| Crash loop after manual debugging | `journalctl -u`, `ls -l` on its files, `sudo -u <svc-user> test -w` | E10 |
| Slow, CPU idle, high load | `vmstat 1` (si/so, b, wa), `free -m`, `ps -eo stat \| grep D` | M06 H09 |
| `<defunct>` / fork fails EAGAIN | `ps -eo ppid,stat`, `systemctl status` (Tasks), parent's config | M07 |
| Logs never rotate | `logrotate -d`, `logrotate -v -f`, `lsof +L1` | M08 |
| Certificate warning | `openssl s_client ... \| openssl x509 -dates`, `nginx -T \| grep ssl_` | M09 |
| Works locally, not from outside | test from the client side, `ss -ltnp`, `iptables -L -nv`, `tcpdump` | M10 |
| Cannot assign requested address | `ss -s`, `ss -tan state time-wait`, `sysctl ip_local_port_range` | H06 |
| Small requests OK, big ones hang | `ping -M do -s`, `ip link` MTUs, `tracepath`, ICMP rules, `tcpdump` | H07 |
| Random connect delays 1 s / 3 s | `dmesg -T`, `conntrack -C`, `sysctl nf_conntrack_max`, `conntrack -S` | H08 |
| `df` hangs | `findmnt -t nfs4`, `ps ... wchan`, `/proc/PID/stack`, `nc -vz <nas> 2049` | H09 |
| Slow app, host idle | `systemd-cgtop`, `cpu.max`, `cpu.stat`, `systemctl cat` drop-ins | H10 |
