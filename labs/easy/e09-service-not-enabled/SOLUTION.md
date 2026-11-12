# E09 - Solution

> Long commands below are built up short-first (`# 1.`, `# 2.` ...). Each rung adds one flag;
> the last rung is what the lab uses. The README **Warm-up** explains every flag from scratch.

## 1. Running, but not enabled

```bash
systemctl is-active shopapp     # active
systemctl is-enabled shopapp    # static   <- no [Install] section, cannot be enabled
```

`static` means: the unit has no `[Install]` section, so it only starts if another unit
pulls it in. Nothing does, so it never starts at boot.

## 2. Try to enable it

```bash
sudo systemctl enable shopapp
# The unit files have no installation config (WantedBy=, RequiredBy=, UpheldBy=,
# Also=, or Alias= settings in the [Install] section, and DefaultInstance= for
# template units). This means they are not meant to be enabled or disabled ...
systemctl cat shopapp      # ends after [Service] - [Install] is gone
```

## 3. Fix the unit file

```bash
sudoedit /etc/systemd/system/shopapp.service
# add at the end:
# [Install]
# WantedBy=multi-user.target

sudo systemctl daemon-reload
sudo systemctl enable shopapp
# Created symlink /etc/systemd/system/multi-user.target.wants/shopapp.service -> ...
```

Don't create the symlink by hand: the next `systemctl disable/enable` or config
management run will not know about it.

Also: tell the owner of the "template cleanup" - other services from the same
template are probably broken too: `grep -L '^\[Install\]' /etc/systemd/system/*.service`.

## 4. Verify

```bash
systemctl is-enabled shopapp            # enabled
systemctl list-dependencies multi-user.target | grep shopapp
sudo ./labctl.sh check e09
```

## Root cause and prevention

| | |
|---|---|
| Root cause | Template rollout removed the `[Install]` section; service was never enabled for boot |
| Fix | Restore `[Install] WantedBy=multi-user.target`, `systemctl enable` |
| Prevent | Lint unit files in CI (`systemd-analyze verify`); reboot-test hosts after changes; alert on "service not running" not just "service failed" |
