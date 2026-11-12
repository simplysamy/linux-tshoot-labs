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

## Warm-up: build the commands up from simple

The solution uses long command lines. They are just short commands with one flag added at a time.
Practise each ladder on any Linux box first (all read-only). Every rung adds **one** thing to the
rung above - stop at the rung you understand, and read the next one only when you are ready.
The lab itself uses the last rung of each ladder.

### openssl - look at a certificate

```bash
openssl x509 -in cert.crt -text -noout          # 1. -text = everything in the cert, -noout = no raw base64
openssl x509 -in cert.crt -noout -dates         # 2. only notBefore / notAfter
openssl x509 -in cert.crt -noout -subject -dates   # 3. + who it is for
openssl s_client -connect host:443              # 4. connect and see the cert the SERVER really presents
echo | openssl s_client -connect host:443 -servername host 2>/dev/null | openssl x509 -noout -dates
                                                # 5. -servername = SNI; 2>/dev/null hides noise; pipe into x509
openssl x509 -in cert.crt -noout -checkend 2592000   # 6. will it still be valid in 30 days? (exit 0 = yes)
```

### curl - talk to a web service

```bash
curl http://localhost/                                   # 1. fetch a page, print the body
curl -s http://localhost/                                # 2. -s = silent (no progress bar)
curl -s -o /dev/null http://localhost/                   # 3. -o /dev/null = throw the body away
curl -s -o /dev/null -w '%{http_code}\n' http://localhost/   # 4. -w = print only the HTTP status code
curl -v http://localhost/                                # 5. -v = verbose: shows connect, headers (debug)
curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' --max-time 5 http://localhost/   # 6. + timing, + give up after 5 s
```

### nginx - test before you restart

```bash
nginx -t                                  # 1. check the config syntax, change nothing
sudo nginx -t                             # 2. needs root to read all files
sudo nginx -T                             # 3. -T = test AND print the full effective config
sudo nginx -T | grep -n listen            # 4. find one directive in it
sudo nginx -t && sudo systemctl reload nginx   # 5. && = reload only if the test passed
```

### --resolve / --cacert - test TLS without real DNS

```bash
curl https://shop.lab.internal/                                              # 1. fails: name unknown / CA unknown
curl --resolve shop.lab.internal:443:127.0.0.1 https://shop.lab.internal/    # 2. pretend the name points to 127.0.0.1
curl --resolve shop.lab.internal:443:127.0.0.1 --cacert lab-ca.crt https://shop.lab.internal/   # 3. + trust this CA
# the error message (expired / unknown CA / name mismatch) tells you which TLS problem you have
```

### matching a key to a certificate

```bash
openssl x509 -in c.crt -noout -pubkey | sha256sum       # 1. fingerprint of the cert's public key
openssl pkey -in c.key -pubout | sha256sum              # 2. fingerprint of the key's public half
# identical hashes = they belong together
```

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
