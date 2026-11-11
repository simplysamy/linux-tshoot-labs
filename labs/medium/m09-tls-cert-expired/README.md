# M09 - "Your connection is not private"

**Level:** Medium · **Time:** 30 min · **Skills:** `openssl s_client`, `openssl x509`, cert/key matching, nginx TLS config, key file permissions

## Ticket

> **INC-2009 · P1**
> Customers get a certificate warning on **https://shop.lab.internal**.
> The certificate was renewed last week by the platform team (files are in
> `/etc/ssl/shopapp/`) and the change ticket was closed as done.
> Reproduce like a customer (the lab CA plays the role of a public CA):
> `curl -v --resolve shop.lab.internal:443:127.0.0.1 --cacert /etc/ssl/shopapp/lab-ca.crt https://shop.lab.internal/`
> Fix it and make sure the setup passes a security review.

## Success criteria

- The `curl` above succeeds without `-k`
- The served certificate is valid for at least 30 more days
- The private key nginx uses is readable only by root
- nginx config test passes; plain HTTP on port 80 still works

Check with `sudo ./labctl.sh check m09`.

## Hints

<details><summary>Hint 1 - what is served right now?</summary>

`openssl s_client -connect 127.0.0.1:443 -servername shop.lab.internal </dev/null 2>/dev/null | openssl x509 -noout -subject -dates`
</details>

<details><summary>Hint 2 - what is on disk?</summary>

For every `.crt`: `openssl x509 -in FILE -noout -subject -enddate`.
Which files does nginx actually use? `sudo nginx -T | grep ssl_`.
</details>

<details><summary>Hint 3 - which key belongs to which cert?</summary>

Compare public keys:
`openssl x509 -in CERT -noout -pubkey | sha256sum` vs `openssl pkey -in KEY -pubout | sha256sum`.
Same hash = pair. Then check `ls -l` on the key.
</details>

## What you should learn

- Always check what the server **serves** (`s_client`), not only what is on disk.
- Renewing a cert = new files **and** config pointing to them **and** a reload.
- A cert and key must be a pair - check before you reload (`nginx -t` also catches it).
- Private keys: `0600 root` (or `0640` for a service group). World-readable = treat as leaked.

Solution: [SOLUTION.md](SOLUTION.md)
