# M09 - Solution

## 1. Reproduce

```bash
curl -v --resolve shop.lab.internal:443:127.0.0.1 --cacert /etc/ssl/shopapp/lab-ca.crt https://shop.lab.internal/
# * SSL certificate problem: certificate has expired
```

## 2. What is served?

```bash
openssl s_client -connect 127.0.0.1:443 -servername shop.lab.internal </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -dates
# subject=CN = shop.lab.internal
# notBefore=... 2024
# notAfter=Nov  7 09:12:00 2026 GMT       <- 3 days ago
```

## 3. What is on disk, and what does nginx use?

```bash
ls -l /etc/ssl/shopapp/
# -rw-r--r-- root root  lab-ca.crt
# -rw-r--r-- root root  shop-2025.crt
# -rw------- root root  shop-2025.key
# -rw-r--r-- root root  shop-2026.crt
# -rw------- root root  shop-2026.key
# -rw-r--r-- root root  shop-2026-renewal.key     <- world-readable private key!

for c in /etc/ssl/shopapp/shop-*.crt; do echo "$c"; openssl x509 -in "$c" -noout -enddate; done
# shop-2025.crt  notAfter=Nov  7 ... 2026      expired
# shop-2026.crt  notAfter=Nov  5 ... 2027      good

sudo nginx -T 2>/dev/null | grep ssl_certificate
# ssl_certificate     /etc/ssl/shopapp/shop-2025.crt;
# ssl_certificate_key /etc/ssl/shopapp/shop-2025.key;
```

The renewal put new files on disk, but nginx was never pointed at them.

## 4. Which key matches the new cert?

```bash
cd /etc/ssl/shopapp
openssl x509 -in shop-2026.crt -noout -pubkey | sha256sum
for k in shop-2026.key shop-2026-renewal.key; do echo -n "$k "; openssl pkey -in $k -pubout | sha256sum; done
# shop-2026.key          9c1e...   <- does NOT match (left over from a first CSR attempt)
# shop-2026-renewal.key  4b7a...   <- matches the cert
```

If you had used `shop-2026.key`, `nginx -t` would say:
`SSL_CTX_use_PrivateKey ... key values mismatch`.

## 5. Fix

```bash
sudo chmod 600 /etc/ssl/shopapp/shop-2026-renewal.key
sudo sed -i 's#shop-2025.crt#shop-2026.crt#; s#shop-2025.key#shop-2026-renewal.key#' \
    /etc/nginx/sites-available/shopapp-tls
sudo nginx -t && sudo systemctl reload nginx
```

The key was world-readable for a week: in production, report it to security - it may
have to be treated as compromised (new key + new cert + revoke the old one).

## 6. Verify

```bash
curl -s --resolve shop.lab.internal:443:127.0.0.1 --cacert /etc/ssl/shopapp/lab-ca.crt https://shop.lab.internal/
echo | openssl s_client -connect 127.0.0.1:443 -servername shop.lab.internal 2>/dev/null \
  | openssl x509 -noout -checkend 2592000 && echo "valid > 30 days"
sudo ./labctl.sh check m09
```

## Root cause and prevention

| | |
|---|---|
| Root cause | Renewal copied new files but nginx still referenced the expired cert; new key world-readable; a non-matching key file with a misleading name |
| Fix | Point nginx to the new cert + matching key, `chmod 600`, `nginx -t`, reload |
| Prevent | Automate renewal (ACME/certbot, cert-manager) incl. reload; monitor the **served** expiry date (`-checkend`); clear file names |
