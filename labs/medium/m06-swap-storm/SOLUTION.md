# M06 - Solution

> Long commands below are built up short-first (`# 1.`, `# 2.` ...). Each rung adds one flag;
> the last rung is what the lab uses. The README **Warm-up** explains every flag from scratch.

## 1. Confirm: CPU idle, but the box is slow

```bash
uptime                     # load average: 6.8, 5.9, 3.1  on 2 CPUs
vmstat 1 5
# procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
#  r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
#  1  4 812344  61200   1020  40312 9120 8840 10200  8900 3100 5200  6 14 32 48  0
```

- `si`/`so` in the thousands every second = **swap storm**.
- `b` (blocked) > 0 and high `wa` = tasks waiting on the disk (here: on swap).
- `cache` is tiny - the page cache was squeezed out, so even normal file reads hit disk.

```bash
free -m
#        total  used  free  shared  buff/cache  available
# Mem:    1967  1880    60       2          27         18
# Swap:   1023   790   233
```

`available` is almost zero.

## 2. Who uses the memory?

```bash
ps -eo pid,user,rss,cmd                  # 1. rss = RAM actually used (KB)
ps -eo pid,user,rss,cmd --sort=-rss      # 2. biggest first
ps -eo pid,user,rss,cmd --sort=-rss | head   # 3. top 10
# 5121 root 182340 /usr/bin/python3 /usr/local/bin/report-builder
# 5122 root 179112 /usr/bin/python3 /usr/local/bin/report-builder
# ... 10 workers
grep VmSwap /proc/[0-9]*/status 2>/dev/null | sort -k2 -n | tail -3
systemctl status report-builder        # Memory: 1.9G (swap: 790M)
```

Ten workers, each with ~200 MB. Total is more than the RAM of the host.

## 3. What did CHG-552 change?

```bash
ls -lt /etc/sysctl.d/ /etc/*.conf | head
cat /etc/sysctl.d/60-batch-tuning.conf
# # swap more eagerly so the batch gets more page cache
# vm.swappiness = 100
cat /etc/report-builder.conf
# workers = 10            # CHG-552: was 2   (the number depends on your VM's RAM)
# worker_mb = 200
```

Two changes: workers 2 → 10 (more memory than the host has), and swappiness 100
(swap application memory even earlier).

## 4. Fix

```bash
sudo sed -i 's/^workers *=.*/workers = 2/' /etc/report-builder.conf
sudo systemctl restart report-builder

sudo rm /etc/sysctl.d/60-batch-tuning.conf     # or set 60 / remove the line
sudo sysctl -w vm.swappiness=60                 # runtime value (default)
sudo sysctl --system | grep swappiness          # confirm nothing else sets it
```

Optional: pull pages back from swap (only when there is enough free RAM!):
`sudo swapoff -a && sudo swapon -a`.

## 5. Verify

```bash
vmstat 1 5              # si/so 0
free -m
sudo ./labctl.sh check m06
```

## Root cause and prevention

| | |
|---|---|
| Root cause | CHG-552 raised batch workers 2 → 10 (2 GB on a 2 GB host) and set swappiness 100 -> thrashing |
| Fix | Workers back to 2, swappiness default, sysctl file removed |
| Prevent | Capacity check for changes (workers × MB vs RAM); `MemoryMax=`/`MemoryHigh=` on batch units; alert on swap-in rate, not only swap used |
