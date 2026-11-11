# M10 - Works on the box, down for everyone else

**Level:** Medium · **Time:** 30 min · **Skills:** listen addresses, `ss -ltn`, refused vs. timed out, INPUT firewall rules, testing from another host

## Ticket

> **INC-2010 · P1**
> External monitoring says the shop is **DOWN**. On the server itself `curl localhost/` works fine,
> so on-call closed the first alert as "false positive" - and it fired again.
> Recent changes: **CHG-610** "web tier hardening" and **SEC-118** "block scanner subnet".
> The monitoring probe lives at `10.210.0.2` (namespace `mon-ns` in the lab). Test as the probe:
> `sudo ip netns exec mon-ns curl -sv --max-time 5 http://10.210.0.1/health`
> Make the shop reachable for the probe again.

## Success criteria

- The probe gets `200` from `http://10.210.0.1/health`
- `curl localhost/` on the server still works
- `nginx -t` passes

Check with `sudo ./labctl.sh check m10`.

## Hints

<details><summary>Hint 1 - read the client error exactly</summary>

`Connection refused` and `Connection timed out` mean different things. Which one do you get?
Which layer does each point to? (README "How a senior SRE troubleshoots" table.)
</details>

<details><summary>Hint 2 - do the packets arrive? who drops them?</summary>

`sudo tcpdump -ni h-mon port 80` shows if SYNs arrive and if anything answers.
`sudo iptables -L INPUT -n -v --line-numbers` - watch the packet counters while the probe tries.
</details>

<details><summary>Hint 3 - after the firewall, the error changes</summary>

On which address does nginx listen? `sudo ss -ltnp | grep ':80 '`.
`0.0.0.0:80` / `*:80` = all addresses; `127.0.0.1:80` = only local. `sudo nginx -T | grep listen`.
</details>

## What you should learn

- Always test from where the user is. `localhost` skips the network, the firewall and the listen address.
- **Refused** = packet arrived, nothing listens on that address/port (or REJECT with RST).
  **Timed out** = packet dropped on the way (firewall DROP, routing).
- Fixing one layer can reveal the next one. Re-test after each change - a *changed* error is progress.
- Firewall rules: read them with counters (`-v`) and in order; narrow a rule instead of deleting it blindly.

Solution: [SOLUTION.md](SOLUTION.md)
