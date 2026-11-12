# H05 - Solution

> Long commands below are built up short-first (`# 1.`, `# 2.` ...). Each rung adds one flag;
> the last rung is what the lab uses. The README **Warm-up** explains every flag from scratch.

## 1. What failed?

```bash
systemctl --failed
#   UNIT                 LOAD   ACTIVE SUB    DESCRIPTION
# ● srv-shopdata.mount   loaded failed failed /srv/shopdata
systemctl status shopapp --no-pager
# Active: inactive (dead)
# Dependency failed for shopapp.service - ShopApp demo web service
systemctl list-dependencies shopapp | head      # srv-shopdata.mount shown as failed
```

The first failure in the chain is the mount. Start there.

## 2. Fault 1 - the mount

```bash
systemctl status srv-shopdata.mount --no-pager
journalctl -b -u srv-shopdata.mount --no-pager | tail
# mount: /srv/shopdata: failed to setup loop device for /var/lib/tshoot/shop-data.img.
grep shopdata /etc/fstab
# /var/lib/tshoot/shop-data.img /srv/shopdata ext4 loop,...
ls -l /var/lib/tshoot/*.img
# /var/lib/tshoot/shopdata.img        <-- the real file has no dash
```

The "naming cleanup" renamed the path in fstab but not the file. Fix fstab (not the file -
other things may use the real name):

```bash
sudo sed -i 's#/var/lib/tshoot/shop-data.img#/var/lib/tshoot/shopdata.img#' /etc/fstab
sudo systemctl daemon-reload
sudo mount -a                       # or: sudo systemctl start srv-shopdata.mount
findmnt /srv/shopdata
```

(Real-world version: wrong UUID / LABEL. Compare with `blkid` and `lsblk -f`.
A bad fstab line *without* `nofail` can drop a server into emergency mode at boot.)

## 3. Fault 2 - the service account

```bash
sudo systemctl start shopapp
systemctl status shopapp --no-pager
# Main process exited, code=exited, status=217/USER
journalctl -u shopapp -n 5 --no-pager
# Failed to determine user credentials: No such process
# Failed at step USER spawning /usr/bin/python3: No such process
systemctl cat shopapp
# # /etc/systemd/system/shopapp.service.d/20-service-account.conf
# User=shop-app
getent passwd shop-app    # nothing - the account was never created
getent passwd shopapp     # exists, owns /srv/shopdata and /var/log/shopapp
```

`217/USER` = systemd could not switch to the user. The app never ran, so app logs are empty.

Options: create `shop-app` (then you must also fix ownership of config, logs, data - big change at 3am),
or roll back the half-done SEC-117 change. Roll back:

```bash
sudo mv /etc/systemd/system/shopapp.service.d/20-service-account.conf /root/20-service-account.conf.rolled-back
sudo systemctl daemon-reload
sudo systemctl restart shopapp
curl -s localhost/health
```

Do **not** "fix" it with `User=root`.

## 4. Prove it survives a reboot

```bash
sudo systemctl stop shopapp && sudo umount /srv/shopdata
sudo systemctl daemon-reload && sudo systemctl start shopapp
systemctl is-active srv-shopdata.mount shopapp
sudo ./labctl.sh check h05
```

## Root cause and prevention

| | |
|---|---|
| Root cause | 1) fstab renamed to a non-existent image path -> mount failed -> shopapp dependency failed. 2) Drop-in set `User=shop-app`, account never created -> 217/USER |
| Prevent | Validate before reboot: `findmnt --verify`, `mount -a`, `systemd-analyze verify`, test-start services; apply changes completely or not at all (config management); reboot test in staging |
