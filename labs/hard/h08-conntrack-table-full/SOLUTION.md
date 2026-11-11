# H08 - Solution

## 1. Confirm the pattern

```bash
for i in $(seq 10); do curl -s -o /dev/null -w '%{http_code} %{time_connect}s\n' --max-time 5 localhost/; done
# 200 0.000412s
# 200 1.012344s     <- 1 s = one SYN retransmit
# 000 5.001200s     <- gave up
# 200 3.020018s     <- 2 retransmits
```

Connect times of exactly ~1 s / ~3 s mean the **SYN was lost** and retransmitted.
The app logs show nothing because those packets never reach nginx.

## 2. Ask the kernel

```bash
sudo dmesg -T | tail -5
# nf_conntrack: nf_conntrack: table full, dropping packet
```

## 3. The table

```bash
sudo conntrack -C                               # 1024
sysctl net.netfilter.nf_conntrack_max           # 1024   (default on this VM: 65536 or similar)
sudo conntrack -S | head -2                     # drop=... early_drop=... growing
grep -r conntrack /etc/sysctl.d/
# /etc/sysctl.d/70-memory-saving.conf:net.netfilter.nf_conntrack_max = 1024
sudo iptables -S | grep SEC-099
# -A INPUT -m conntrack --ctstate INVALID -m comment --comment "SEC-099 drop invalid packets" -j DROP
```

The SEC-099 rule uses conntrack, so the kernel tracks every connection (loopback too).
CHG-830 lowered the table size to 1024.

## 4. Who fills it?

```bash
sudo conntrack -L -p tcp 2>/dev/null | grep -o 'dport=[0-9]*' | sort | uniq -c | sort -rn | head -3
#   1480 dport=9100
#      4 dport=22
ss -tnp state established '( dport = :9100 )' | head -3     # users:(("python3",pid=...)) - metrics-scraper
cat /etc/metrics-scraper.conf
# pool_size = 1500          ; v2: keep connections warm
journalctl -u metrics-scraper -n 3 --no-pager
```

metrics-scraper v2 keeps a pool of **1500** open connections to one local exporter
(a typo for 15). Established TCP entries are "assured" and live for days, so the kernel's
`early_drop` cannot evict them - the table stays full and new connections are dropped.

## 5. Fix both

```bash
# the leak
sudo sed -i 's/^pool_size *=.*/pool_size = 15/' /etc/metrics-scraper.conf
sudo systemctl restart metrics-scraper

# the limit (runtime + persistent)
sudo rm /etc/sysctl.d/70-memory-saving.conf
sudo sysctl -w net.netfilter.nf_conntrack_max=65536
```

Memory note: each entry is ~300 bytes; 65536 entries ≈ 20 MB. CHG-830 saved almost nothing
and created an outage.

## 6. Verify

```bash
sudo conntrack -C
for i in $(seq 10); do curl -s -o /dev/null -w '%{time_connect}\n' localhost/; done
sudo ./labctl.sh check h08
```

## Root cause and prevention

| | |
|---|---|
| Root cause | CHG-830 set `nf_conntrack_max=1024`; metrics-scraper v2 held 1500 idle connections -> table full -> new SYNs dropped |
| Fix | Pool 15, conntrack max back to 65536, sysctl file removed |
| Prevent | Alert on `nf_conntrack_count / nf_conntrack_max > 80%` and on "table full" in the kernel log; review sysctl changes; load-test new versions of agents |
