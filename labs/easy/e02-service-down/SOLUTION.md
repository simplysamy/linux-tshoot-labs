# E02 - Solution

> Long commands below are built up short-first (`# 1.`, `# 2.` ...). Each rung adds one flag;
> the last rung is what the lab uses. The README **Warm-up** explains every flag from scratch.

## 1. Confirm

```bash
curl http://localhost/                  # 1. plain request
curl -v http://localhost/               # 2. -v shows the connect step
# connect to 127.0.0.1 port 80 failed: Connection refused
sudo ss -l                              # 1. every listening socket
sudo ss -ltn                            # 2. TCP only, numbers
sudo ss -ltnp 'sport = :80'             # 3. + owning process, + only port 80
#   (empty -> nothing listens on 80)
```

## 2. Check the service

```bash
systemctl status nginx
# Active: failed (Result: exit-code)
journalctl -u nginx                     # 1. whole log
journalctl -u nginx -n 20               # 2. last 20 lines
journalctl -u nginx -n 20 --no-pager    # 3. print straight to the terminal
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
