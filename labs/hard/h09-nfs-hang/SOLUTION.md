# H09 - Solution

> Long commands below are built up short-first (`# 1.`, `# 2.` ...). Each rung adds one flag;
> the last rung is what the lab uses. The README **Warm-up** explains every flag from scratch.

## 1. Confirm safely

```bash
uptime                                          # load average: 9.1, 6.0, 2.4
top -bn1 | head -5                              # %Cpu(s): 98 id
ps -eo pid,stat,cmd                                                    # 1. state of every process
ps -eo pid,stat,etime,wchan:32,cmd                                     # 2. + age, + kernel function it waits in
ps -eo pid,stat,etime,wchan:32,cmd | awk 'NR==1 || $2 ~ /D/'          # 3. keep header (NR==1) + rows in state D
#   PID STAT  ELAPSED WCHAN                            CMD
#  8101 D       07:12 rpc_wait_bit_killable            df -h
#  8120 D       06:01 rpc_wait_bit_killable            /bin/bash /usr/local/bin/report-export
sudo cat /proc/8101/stack | head -5
# [<0>] rpc_wait_bit_killable+0x1e/0x90 [sunrpc]
# [<0>] __rpc_execute+0x... [sunrpc]
# [<0>] nfs4_proc_statfs ...
```

The tasks are not using CPU. They wait inside the **NFS client** (`sunrpc`) - each one adds 1 to the load.

## 2. Which mount, which server?

```bash
findmnt -t nfs,nfs4                 # safe: reads the mount table only
# /mnt/reports nas01.lab.internal:/srv/nfs/reports nfs4 rw,relatime,vers=4.2,hard,timeo=50,retrans=2,...
dmesg -T | grep -i nfs | tail -3
# nfs: server nas01.lab.internal not responding, still trying
getent hosts nas01.lab.internal     # 10.240.0.10
timeout 5 stat -f /mnt/reports || echo "mount hangs"
```

## 3. Why can't we reach the NAS?

```bash
nc -vz -w3 10.240.0.10 2049         # timed out
sudo iptables -L OUTPUT -n -v --line-numbers
# 1   212 15k DROP tcp -- * * 0.0.0.0/0 10.240.0.10 tcp dpt:2049 /* SEC-410 egress lockdown */
```

SEC-410 blocked outgoing NFS to the NAS. Counters increase while the client retries.

## 4. Fix the path

Agree with security - the NAS is an approved destination - and remove/except the rule:

```bash
sudo iptables -D OUTPUT 1           # or: -I OUTPUT 1 -d 10.240.0.10 -p tcp --dport 2049 -j ACCEPT
```

The `hard` mount now recovers by itself. TCP backoff means it can take up to a minute or two.
Watch: `watch -n2 "ps -eo stat | grep -c '^D'"` going to 0. `dmesg`: `nfs: server ... OK`.

If the server is really gone and you must free the host: `sudo umount -f -l /mnt/reports`
(stuck writes get errors - data written by them is lost).

## 5. Make boot safe

```bash
grep reports /etc/fstab
# nas01.lab.internal:/srv/nfs/reports /mnt/reports nfs4 hard,timeo=50,retrans=2 0 0
```

Without `nofail`, a missing NAS at boot puts the host into emergency mode; without `_netdev`
systemd may try before the network is up. Fix:

```
nas01.lab.internal:/srv/nfs/reports /mnt/reports nfs4 _netdev,nofail,hard,timeo=50,retrans=2,x-systemd.mount-timeout=30 0 0
```

```bash
sudo systemctl daemon-reload
sudo mount -o remount /mnt/reports     # or umount + mount
```

`hard` vs `soft`: keep `hard` for data you write (soft can silently corrupt writes on timeouts).
`x-systemd.automount` is a nice addition: the mount is only touched on access.

## 6. Verify

```bash
ps -eo stat | grep -c '^D'            # 0
timeout 5 df -h /mnt/reports
sudo /usr/local/bin/report-export && ls -lt /mnt/reports | head -3
sudo ./labctl.sh check h09
```

## Root cause and prevention

| | |
|---|---|
| Root cause | SEC-410 dropped egress NFS (tcp/2049) to the NAS; `hard` mount blocked every process touching it (D state); cron added a stuck export every minute |
| Fix | Allowed NFS to the NAS; mount recovered; fstab `_netdev,nofail` |
| Prevent | Firewall changes checked against a dependency list (NAS, DB, DNS, NTP); alert on D-state count and "not responding" in kernel log; monitoring agents use `timeout` |
