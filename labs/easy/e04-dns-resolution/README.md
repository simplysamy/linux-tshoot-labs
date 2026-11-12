# E04 - "The internet is down" (DNS)

**Level:** Easy · **Time:** 20 min · **Skills:** name resolution, resolv.conf, /etc/hosts, nsswitch

## Ticket

> **INC-1004 · P2**
> `sudo apt update` fails with `Temporary failure resolving 'archive.ubuntu.com'`.
> Also, a payment check calls `https://example.com` and fails with a TLS/connection error.
> Ping to `8.8.8.8` still works. Fix name resolution on this host.

## Success criteria

- Public names resolve (`getent ahosts ubuntu.com`)
- `example.com` resolves to its real address and `curl https://example.com` works

## Warm-up: build the commands up from simple

The solution uses long command lines. They are just short commands with one flag added at a time.
Practise each ladder on any Linux box first (all read-only). Every rung adds **one** thing to the
rung above - stop at the rung you understand, and read the next one only when you are ready.
The lab itself uses the last rung of each ladder.

### ping / dig / getent - names and addresses

```bash
ping 8.8.8.8                       # 1. is the network reachable? (Ctrl-C to stop)
ping -c2 8.8.8.8                   # 2. -c2 = send 2 and stop
ping -c2 ubuntu.com                # 3. same, by name: tests DNS + network
dig ubuntu.com                     # 4. ask DNS directly (shows the whole answer)
dig +short ubuntu.com              # 5. only the answer
dig @8.8.8.8 +short ubuntu.com     # 6. @server = ask THAT server instead of the default
getent hosts ubuntu.com            # 7. resolve like programs do (/etc/hosts first, then DNS)
```

### ls -l / cat - is resolv.conf a file or a symlink?

```bash
cat /etc/resolv.conf                 # 1. which DNS server do programs use?
ls -l /etc/resolv.conf               # 2. a leading 'l' and '->' mean symlink; '-' means plain file
resolvectl status                    # 3. what systemd-resolved itself uses
resolvectl status | grep -A2 'DNS Servers'    # 4. only the DNS part
grep hosts /etc/nsswitch.conf        # 5. the lookup ORDER programs use (files = /etc/hosts, dns = DNS servers)
```

### ln - symlinks

```bash
ln -s TARGET LINKNAME                # 1. LINKNAME now points to TARGET
ln -sf TARGET LINKNAME               # 2. -f = replace LINKNAME if it exists
readlink -f LINKNAME                 # 3. where does it really point?
```

## Hints

<details><summary>Hint 1 - network or DNS?</summary>

`ping -c2 8.8.8.8` works, `ping -c2 ubuntu.com` does not -> IP works, names do not.
That is DNS. Which server does this host ask? `cat /etc/resolv.conf`, `resolvectl status`.
</details>

<details><summary>Hint 2 - test the resolver directly</summary>

`dig ubuntu.com` uses resolv.conf. `dig @127.0.0.53 ubuntu.com` asks systemd-resolved.
`dig @1.1.1.1 ubuntu.com` asks a public resolver. Compare. `ls -l /etc/resolv.conf` - what is it normally on Ubuntu?
</details>

<details><summary>Hint 3 - dig and curl disagree</summary>

After fixing DNS, `dig example.com` may be right but `curl` still goes to a wrong IP.
`dig` asks DNS only. Apps use `getent hosts` order from `/etc/nsswitch.conf` -
`files` (= `/etc/hosts`) comes before `dns`.
</details>

## What you should learn

- Split the problem: IP connectivity (`ping <ip>`) vs. name resolution (`getent hosts <name>`).
- On modern Ubuntu, `/etc/resolv.conf` is a symlink managed by systemd-resolved. Hand edits get lost or break things.
- `dig`/`nslookup` bypass `/etc/hosts`. `getent hosts` shows what applications really get.
- Stale `/etc/hosts` entries are a classic cause of "works on my box, not on this one".

Solution: [SOLUTION.md](SOLUTION.md)
