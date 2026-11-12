# H04 - Solution

> Long commands below are built up short-first (`# 1.`, `# 2.` ...). Each rung adds one flag;
> the last rung is what the lab uses. The README **Warm-up** explains every flag from scratch.

## 1. First 60 seconds - whole system view

```bash
uptime                 # load ~2-3 on 2 CPUs
vmstat 1 5
# procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
#  r  b   swpd   free  ...           bi    bo   in   cs us sy id wa st
#  1  1      0 1.2g  ...              0  3900  ... ... 0  6  0 44  0
#           ^ b = blocked on IO                         ^ wa high
top          # header: %Cpu(s): 0.3 us, 6.0 sy, 49.0 ni, 0.0 id, 44.0 wa
```

Read the CPU line:

- `ni 49%` = CPU used by **niced** processes (batch-encoder). This is "spare" CPU it was allowed to use.
- `wa 44%` = CPUs idle **waiting for disk IO**. This is the pain.
- `us` (normal tasks) is tiny - nothing is starved of CPU.

## 2. Prove batch-encoder is not the problem

```bash
ps -o pid,ni,pri,%cpu,cmd -C python3
#  PID  NI PRI %CPU CMD
# 2201  19   0 99.0 /usr/bin/python3 /usr/local/bin/batch-encoder
time (for i in $(seq 200000); do :; done)    # a normal-priority CPU task is still fast
```

A nice 19 task yields to any nice 0 task. It cannot make the shell feel slow.

## 3. Find the disk and the process

```bash
iostat                  # 1. summary since boot
iostat -x               # 2. + extended columns: %util, await
iostat -xz 1 3          # 3. + hide idle disks, every 1 s, 3 times
# Device  r/s   w/s   wkB/s  w_await  aqu-sz  %util
# sda     0.0  950   3800    1.0      0.95    98.0     <-- saturated with tiny writes
sudo pidstat -d         # 1. disk IO per process, one sample
sudo pidstat -d 1 5     # 2. every 1 s, 5 times
#  UID  PID  kB_rd/s kB_wr/s kB_ccwr/s iodelay Command
#    0 3310     0.00 3800.00     0.00     95  dd
ps -eo pid,stat,wchan:22,cmd | awk '$2 ~ /D/'
# 3310 D  ... dd if=/dev/zero of=/var/tmp/audit-sync.dat bs=4k ... oflag=dsync
```

~4 MB/s is tiny, but **every 4 KB write waits for the disk** (`oflag=dsync`), so the
disk is 98% busy and every other writer queues behind it.

## 4. Who runs it, and why does it come back?

```bash
systemctl status 3310 --no-pager
# ● audit-sync.service - Compliance audit record sync
#    TriggeredBy: ● audit-sync.timer
systemctl list-timers --all | grep audit
systemctl cat audit-sync.timer          # OnUnitInactiveSec=20s -> restarts 20s after it stops
```

## 5. Fix - pick one, with the owner

**A) Stop it until the compliance team fixes the job**

```bash
sudo systemctl disable --now audit-sync.timer
sudo systemctl stop audit-sync.service
```

**B) Keep it running, but only on idle disk time** (better if the job is required)

```bash
sudo systemctl edit audit-sync.service
# [Service]
# IOSchedulingClass=idle
# IOWeight=10
sudo systemctl restart audit-sync.service
```

(`IOSchedulingClass` needs the BFQ/CFQ IO scheduler to fully work; `IOWriteBandwidthMax=/dev/sda 1M`
is a hard limit that works with any scheduler.)

Then confirm:

```bash
vmstat 1 5           # wa near 0, b = 0
iostat -xz 1 3       # %util down
```

## Root cause and prevention

| | |
|---|---|
| Root cause | audit-sync does continuous 4 KB synchronous writes (`dsync`), saturating the disk; restarted by a systemd timer every 20s |
| Red herring | batch-encoder at 100% CPU, but at nice 19 - it only used idle CPU |
| Prevent | Batch the writes or use one `fsync` per batch; give batch jobs `IOWeight`/`Nice`; alert on iowait and disk `%util`, not only CPU |
