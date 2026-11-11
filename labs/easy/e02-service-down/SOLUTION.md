# E02 - Solution

## 1. Confirm

```bash
curl -v http://localhost/
# connect to 127.0.0.1 port 80 failed: Connection refused
sudo ss -ltnp 'sport = :80'      # empty -> nothing listens on 80
```

## 2. Check the service

```bash
systemctl status nginx
# Active: failed (Result: exit-code)
journalctl -u nginx -n 20 --no-pager
# nginx: [emerg] unexpected end of file, expecting ";" or "}" ... or
# nginx: [emerg] invalid number of arguments in "proxy_read_timeout" directive in /etc/nginx/sites-enabled/shopapp:15
```

## 3. Validate the config

```bash
sudo nginx -t
sudo grep -n timeout /etc/nginx/sites-available/shopapp
#  proxy_read_timeout 30s            <-- missing ;
#  proxy_send_timeout 30s;
```

Without the `;` nginx reads both lines as one directive:
`proxy_read_timeout 30s proxy_send_timeout 30s` - too many arguments.

## 4. Fix - keep the colleague's change, add the `;`

```bash
sudo sed -i 's/proxy_read_timeout 30s$/proxy_read_timeout 30s;/' /etc/nginx/sites-available/shopapp
sudo nginx -t && sudo systemctl restart nginx
curl -s -o /dev/null -w '%{http_code}\n' http://localhost/
```

## Root cause and prevention

| | |
|---|---|
| Root cause | Syntax error (missing `;`) in nginx site config; nginx was restarted without a config test |
| Prevent | Always `nginx -t && systemctl reload nginx`; keep config in git with CI linting; use config management |
