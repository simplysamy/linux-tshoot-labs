# H10 - Solution

## 1. Confirm

```bash
for i in 1 2 3 4 5; do curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' localhost/; done
# 200 2.913s
# 200 3.402s
# 504 10.001s
top -bn1 | head -4          # %Cpu(s): 6.1 us, 2.0 sy, 91.2 id
```

Slow, but the host is idle. Not a host CPU problem - maybe a problem of what shopapp is *allowed* to use.

## 2. Look at the cgroup

```bash
systemctl status shopapp | grep -E 'CGroup|CPU'
#      CPU: 1min 2.381s
#   CGroup: /shop.slice/shopapp.service          <- not in system.slice!
systemd-cgtop -n 1 | head                         # shopapp ~5% CPU, never more
CG=/sys/fs/cgroup/shop.slice/shopapp.service
cat $CG/cpu.max                                   # 5000 100000  = 5% of one CPU
cat $CG/cpu.stat
# nr_periods 41210
# nr_throttled 39877        <- throttled in almost every period
# throttled_usec 912384112
```

## 3. Where do the limits come from?

```bash
systemctl cat shopapp
# # /etc/systemd/system/shopapp.service
# ...
# # /etc/systemd/system/shopapp.service.d/50-finops.conf
# [Service]
# # FINOPS-77 right-size noisy services
# CPUQuota=5%
# Slice=shop.slice
systemd-delta --type=extended                     # lists all drop-ins on the host

systemctl cat shop.slice
# [Slice]
# # FINOPS-77 cap the whole shop at 10%
# CPUQuota=10%
cat /sys/fs/cgroup/shop.slice/cpu.max             # 10000 100000
```

Two layers: the service is capped at 5% and its slice at 10%. Removing only the
service quota still leaves the slice cap - latency improves a bit and stays bad.

## 4. Fix

```bash
sudo rm /etc/systemd/system/shopapp.service.d/50-finops.conf     # puts shopapp back in system.slice
sudo systemctl daemon-reload
sudo systemctl restart shopapp
systemctl show shopapp -p Slice -p CPUQuotaPerSecUSec
# Slice=system.slice
# CPUQuotaPerSecUSec=infinity
cat /sys/fs/cgroup/system.slice/shopapp.service/cpu.max           # max 100000
```

If you keep `shop.slice` (grouping is useful), remove its quota or use `CPUWeight=`
instead: weights only matter when CPU is actually contended, quotas throttle always.

```bash
sudo rm /etc/systemd/system/shop.slice && sudo systemctl daemon-reload   # if unused now
```

## 5. Verify

```bash
for i in $(seq 10); do curl -s -o /dev/null -w '%{time_total}\n' localhost/; done
grep nr_throttled /sys/fs/cgroup/system.slice/shopapp.service/cpu.stat    # stays 0
sudo ./labctl.sh check h10
```

## Root cause and prevention

| | |
|---|---|
| Root cause | FINOPS-77 drop-in moved shopapp into `shop.slice` with `CPUQuota=5%`, slice capped at 10%; under normal traffic the app was throttled every period |
| Fix | Removed the drop-in (and slice quota); shopapp back in `system.slice` without quota |
| Prevent | Resource-limit changes go through review with load data; monitor `nr_throttled` / `throttled_usec` per service; prefer `CPUWeight` to hard quotas for latency-sensitive services |
