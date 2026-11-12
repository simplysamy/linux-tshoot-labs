# E04 - Solution

> Long commands below are built up short-first (`# 1.`, `# 2.` ...). Each rung adds one flag;
> the last rung is what the lab uses. The README **Warm-up** explains every flag from scratch.

## 1. IP or DNS?

```bash
ping -c2 8.8.8.8          # works -> routing/internet OK
ping -c2 ubuntu.com       # "Temporary failure in name resolution" -> DNS
```

## 2. Which resolver do we use?

```bash
ls -l /etc/resolv.conf
# -rw-r--r-- 1 root root ... /etc/resolv.conf     <-- a plain file, normally a symlink
cat /etc/resolv.conf
# nameserver 10.255.255.53                        <-- dead server
dig ubuntu.com                      # ;; connection timed out; no servers could be reached
dig @127.0.0.53 ubuntu.com           # 1. ask one specific server (127.0.0.53 = systemd-resolved)
dig @127.0.0.53 ubuntu.com +short    # 2. only the answer: systemd-resolved still works
resolvectl status                    # 1. everything systemd-resolved knows
resolvectl status | grep -A2 'DNS Servers'   # 2. -A2 = the match + 2 lines after it
```

## 3. Fix fault 1 - give resolv.conf back to systemd-resolved

```bash
sudo ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf
getent ahosts ubuntu.com | head -2
sudo apt update     # works
```

## 4. Fault 2 - example.com still broken

```bash
dig +short example.com          # real IP (DNS is fine now)
getent hosts example.com        # 203.0.113.77  <-- different!
grep -n example /etc/hosts
grep hosts /etc/nsswitch.conf   # hosts: files dns  -> /etc/hosts wins
```

Remove the stale line:

```bash
sudo sed -i '/203\.0\.113\.77/d' /etc/hosts
getent hosts example.com
curl -sI https://example.com | head -1
```

## Root cause and prevention

| | |
|---|---|
| Root cause | 1) `/etc/resolv.conf` symlink replaced with a hand-written file pointing to a dead resolver. 2) Stale `/etc/hosts` override for example.com |
| Prevent | Manage DNS through netplan/systemd-resolved, not hand edits; never leave test entries in `/etc/hosts`; track both files in config management |
