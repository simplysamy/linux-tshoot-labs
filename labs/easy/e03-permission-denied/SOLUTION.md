# E03 - Solution

## 1. Find the failing layer

```bash
curl -s -o /dev/null -w '%{http_code}\n' localhost/    # 502 -> nginx up, backend down
systemctl status shopapp
# Active: activating (auto-restart) (Result: exit-code) ... status=2
journalctl -u shopapp -n 5 --no-pager
# FATAL: cannot read config /etc/shopapp/config.ini: [Errno 13] Permission denied
```

## 2. Test as the service user

```bash
systemctl show -p User -p Group shopapp       # User=shopapp Group=shopapp
sudo -u shopapp cat /etc/shopapp/config.ini   # Permission denied
namei -l /etc/shopapp/config.ini
# f: /etc/shopapp/config.ini
# drwxr-xr-x root root /
# drwxr-xr-x root root etc
# drwx------ root root shopapp        <-- no x for shopapp
# -rw------- root root config.ini     <-- no r for shopapp
```

Two problems: directory `0700` and file `root:root 0600`.

## 3. Fix with least privilege

```bash
sudo chmod 0755 /etc/shopapp                 # dir: contains no secrets, normal mode
sudo chown root:shopapp /etc/shopapp/config.ini
sudo chmod 0640 /etc/shopapp/config.ini      # root rw, group shopapp r, others nothing
sudo -u shopapp cat /etc/shopapp/config.ini  # works now
sudo systemctl restart shopapp
curl -s localhost/health
```

(`0750 root:shopapp` on the directory is also fine and stricter.)

Wrong fixes: `chmod 777`, `chmod 644` on the config (world-readable), or
changing the service to `User=root`.

## Root cause and prevention

| | |
|---|---|
| Root cause | Hardening script set config to `root:root 0600` and dir to `0700`; service user lost access |
| Prevent | Test hardening in staging; manage file modes in config management; health-check after changes |
