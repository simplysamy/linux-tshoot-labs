# H06 - Solution

## 1. Confirm and find the failing component

```bash
for i in $(seq 10); do curl -s -o /dev/null -w '%{http_code} ' localhost/; done; echo
# 000 000 200 000 000 000 200 000 000 000
curl -v localhost/
# *   Trying 127.0.0.1:80...
# * Immediate connect fail for 127.0.0.1: Cannot assign requested address
journalctl -u price-sync -n 3 --no-pager
# ERROR 183 failed syncs in last 10s (last: [Errno 99] Cannot assign requested address)
```

`000` = curl never got an HTTP answer. errno 99 `EADDRNOTAVAIL` on `connect()` = the kernel
found **no free local port** for a new outgoing connection to `127.0.0.1:80`.
Outside customers use *their own* ports, which is why they are fine: this is a
client-side (outgoing) problem on this host.

## 2. Socket states

```bash
ss -s
# TCP:   188 (estab 4, closed 180, orphaned 0, timewait 180)
ss -tan state time-wait | awk 'NR>1{print $4}' | cut -d: -f2 | sort -n | sed -n '1p;$p'
# 61000
# 61100
```

All `TIME_WAIT` sockets use local ports 61000-61100 - only **101 ports**.

## 3. Why so few ports? (CHG-701)

```bash
sysctl net.ipv4.ip_local_port_range net.ipv4.tcp_tw_reuse net.ipv4.tcp_fin_timeout
# net.ipv4.ip_local_port_range = 61000	61100
# net.ipv4.tcp_tw_reuse = 0
# net.ipv4.tcp_fin_timeout = 120
cat /etc/sysctl.d/90-net-tuning.conf
```

- Port range: default is `32768 60999` (28 232 ports). CHG-701 cut it to 101.
- `tcp_tw_reuse = 0`: default `2` lets loopback connections reuse TIME_WAIT ports. Turned off.
- `tcp_fin_timeout = 120`: a **red herring**. It controls FIN_WAIT_2, not TIME_WAIT.
  TIME_WAIT is always 60 s in Linux (`TCP_TIMEWAIT_LEN`).

Math: 101 ports / 60 s ≈ **1.7 new connections per second** to the same destination.

## 4. Who makes so many connections?

```bash
journalctl -u price-sync -n 5 --no-pager
# price-sync: 20 req/s, reuse_connections=False
cat /etc/price-sync.conf
# reuse_connections = false
```

price-sync opens a **new TCP connection for every request** and closes it first, so the
TIME_WAIT is on our side (whoever closes first gets TIME_WAIT). 20 req/s × 60 s = 1 200 ports needed just for price-sync.

## 5. Fix both causes

```bash
# 1) undo the bad tuning (runtime + persistent)
sudo rm /etc/sysctl.d/90-net-tuning.conf
sudo sysctl -w net.ipv4.ip_local_port_range="32768 60999"
sudo sysctl -w net.ipv4.tcp_tw_reuse=2
sudo sysctl -w net.ipv4.tcp_fin_timeout=60
sudo sysctl --system >/dev/null      # re-applies all files; check nothing else narrows the range

# 2) make the client reuse connections (HTTP keep-alive)
sudo sed -i 's/^reuse_connections *=.*/reuse_connections = true/' /etc/price-sync.conf
sudo systemctl restart price-sync
```

`tcp_tw_recycle` does not exist on modern kernels (`sysctl: cannot stat ... tcp_tw_recycle`) -
the colleague's advice is from an old blog post.

## 6. Verify

```bash
ss -s                                   # timewait small and falling
for i in $(seq 30); do curl -s -o /dev/null -w '%{http_code} ' localhost/; done; echo
sudo ./labctl.sh check h06
```

## Root cause and prevention

| | |
|---|---|
| Root cause | CHG-701 narrowed `ip_local_port_range` to 101 ports and disabled `tcp_tw_reuse`; price-sync opened and closed a new connection per request (20/s). Ports ran out -> EADDRNOTAVAIL |
| Fix | Default sysctls (file removed), keep-alive in price-sync |
| Prevent | Review sysctl changes with numbers, not blog posts; connection pooling as a coding standard; alert on TIME_WAIT count and on errno 99 in logs |
