# E05 - Solution

> Long commands below are built up short-first (`# 1.`, `# 2.` ...). Each rung adds one flag;
> the last rung is what the lab uses. The README **Warm-up** explains every flag from scratch.

## 1. Why nginx fails

```bash
systemctl status nginx --no-pager
journalctl -u nginx -n 10 --no-pager
# nginx: [emerg] bind() to 0.0.0.0:80 failed (98: Address already in use)
```

## 2. Who owns port 80

```bash
sudo ss -ltnp 'sport = :80'
# LISTEN 0 5 0.0.0.0:80 0.0.0.0:* users:(("python3",pid=2345,fd=3))
ps -fp 2345
# root 2345 1 ... /usr/bin/python3 -m http.server 80 --directory /var/www/legacy-status
```

## 3. Map the PID to a service

```bash
systemctl status 2345 --no-pager
# ● legacy-status.service - Legacy maintenance status page
#    Loaded: loaded (/etc/systemd/system/legacy-status.service; enabled ...)
```

`sudo kill 2345` would not help: `Restart=always` starts it again in 100 ms.

## 4. Fix

```bash
sudo systemctl disable --now legacy-status
sudo ss -ltnp 'sport = :80'          # empty
sudo systemctl start nginx
curl -s localhost/                   # shopapp is running
```

Optional cleanup after you ask the owner: remove the unit file and `systemctl daemon-reload`.

## Root cause and prevention

| | |
|---|---|
| Root cause | Old `legacy-status.service` (enabled, Restart=always) bound port 80 before nginx |
| Prevent | Remove retired units instead of leaving them on disk; monitor that the expected process owns each public port |
