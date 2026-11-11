# H02 - "Read-only file system"

**Level:** Hard · **Time:** 45 min · **Skills:** kernel log, mount options, unmount safely, fsck, restore from backup

## Ticket

> **INC-3002 · P1 · Customer facing**
> `/health` returns `500 ERROR: [Errno 30] Read-only file system`. Checkout is broken.
> Nobody changed mounts. The storage team reported a "brief glitch" on the hypervisor overnight.
> Get the data volume `/srv/shopdata` healthy and writable again. If data was lost, restore it -
> last night's backups are in `/srv/backups/`.

## Success criteria

- `/srv/shopdata` mounted read-write and the filesystem is **clean** (no errors flag)
- `catalog/products.db` restored from backup, owned by `shopapp`
- `/health` returns 200

## Hints

<details><summary>Hint 1 - why read-only?</summary>

`findmnt /srv/shopdata` shows the options now. The kernel decided this, so the kernel
logged why: `journalctl -k | grep -i ext4` or `sudo dmesg -T | grep -i -E 'ext4|remount'`.
</details>

<details><summary>Hint 2 - don't just remount rw</summary>

`mount -o remount,rw` makes the error go away and leaves a corrupt filesystem.
Look at `sudo dumpe2fs -h <device> | grep -i -E 'state|error'`. A filesystem with errors
needs `e2fsck`, and `e2fsck` needs it **unmounted**.
</details>

<details><summary>Hint 3 - "target is busy"</summary>

Who uses the mount? `sudo fuser -vm /srv/shopdata` or `sudo lsof /srv/shopdata`.
Stop the service (and `cd` out of the directory yourself). After fsck, check
`lost+found` and what is missing - then restore from backup.
</details>

## What you should learn

- `errors=remount-ro`: ext4 goes read-only on corruption to protect your data. It is a symptom.
- The kernel log tells you the device, inode and function that hit the error.
- Correct order: stop writers -> unmount -> `e2fsck -f` -> mount -> verify data -> restore -> start app.
- Never run `fsck` on a mounted filesystem. Never "fix" read-only by just remounting rw.
- After fsck, files can disappear or move to `lost+found`. Backups are part of recovery.

Solution: [SOLUTION.md](SOLUTION.md)
