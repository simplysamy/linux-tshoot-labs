# M10 - Solution

## 1. Test as the user

```bash
curl -s localhost/health                                      # OK  (misleading)
sudo ip netns exec mon-ns curl -sv --max-time 5 http://10.210.0.1/health
# * Connection timed out after 5001 milliseconds
```

Timed out = the packets are dropped somewhere. `localhost` never touches the network
interface or the INPUT rules for that subnet, which is why it "works".

## 2. Is the traffic arriving? Who drops it?

```bash
sudo tcpdump -ni h-mon port 80          # SYNs arrive from 10.210.0.2, nothing answers
sudo iptables -L INPUT -n -v --line-numbers
# num pkts bytes target prot opt in  out source          destination
# 1     14   840 DROP   tcp  --  *   *   10.210.0.0/24   0.0.0.0/0   tcp dpt:80 /* SEC-118 block scanner subnet */
```

The counter goes up each time the probe tries. SEC-118 blocked the whole `10.210.0.0/24`
subnet - which is the monitoring network.

Fix the rule, not the whole firewall. Ask security which host was the scanner. In the lab:
allow the probe, keep the block.

```bash
sudo iptables -I INPUT 1 -s 10.210.0.2/32 -p tcp --dport 80 -m comment --comment "INC-2010 monitoring probe" -j ACCEPT
# or, if the block was a mistake:  sudo iptables -D INPUT <num>
```

In production also make it persistent (`netfilter-persistent save`, or your firewall tool).

## 3. Re-test - the error changes

```bash
sudo ip netns exec mon-ns curl -sv --max-time 5 http://10.210.0.1/health
# * connect to 10.210.0.1 port 80 failed: Connection refused
```

Progress: packets now reach the host, but nothing listens on `10.210.0.1:80`.

```bash
sudo ss -ltnp | grep ':80 '
# LISTEN 0 511  127.0.0.1:80   0.0.0.0:*  users:(("nginx",pid=812,fd=6),...)
# LISTEN 0 511      [::1]:80      [::]:*  ...
sudo nginx -T 2>/dev/null | grep -n listen
#   listen 127.0.0.1:80 default_server;   # CHG-610 hardening: loopback only
```

CHG-610 bound nginx to loopback. That "hardens" the web server by switching it off for
everyone else. Fix:

```bash
sudoedit /etc/nginx/sites-available/shopapp
#   listen 80 default_server;
#   listen [::]:80 default_server;
sudo nginx -t && sudo systemctl reload nginx
sudo ss -ltn | grep ':80 '          # 0.0.0.0:80 and [::]:80
```

## 4. Verify

```bash
sudo ip netns exec mon-ns curl -s http://10.210.0.1/health   # OK
sudo ./labctl.sh check m10
```

Side finding for the incident notes: shopapp itself listens on `0.0.0.0:8080`, so the
probe can reach the backend directly and bypass nginx
(`ip netns exec mon-ns curl 10.210.0.1:8080/`). *That* is what real hardening should fix.

## Root cause and prevention

| | |
|---|---|
| Root cause | (1) SEC-118 dropped the monitoring subnet; (2) CHG-610 bound nginx to 127.0.0.1 |
| Fix | ACCEPT for the probe before the DROP; nginx listens on all addresses |
| Prevent | Test changes from outside (synthetic checks in the change pipeline); never close an alert as false positive without testing from the alert's source |
