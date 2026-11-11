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
