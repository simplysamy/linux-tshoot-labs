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

## Warm-up: build the commands up from simple

The solution uses long command lines. They are just short commands with one flag added at a time.
Practise each ladder on any Linux box first (all read-only). Every rung adds **one** thing to the
rung above - stop at the rung you understand, and read the next one only when you are ready.
The lab itself uses the last rung of each ladder.

### findmnt / mount - what is mounted

```bash
mount | head                         # 1. old way: long list
findmnt                              # 2. tree of all mounts
findmnt /srv/shopdata                # 3. one mount: source, type, options (look for ro / rw)
findmnt -t nfs,nfs4                  # 4. -t = only these types
findmnt -no OPTIONS /srv/shopdata    # 5. -n no header, -o choose column -> script-friendly
```

### dmesg / journalctl -k - the kernel's messages

```bash
dmesg                           # 1. kernel ring buffer (needs sudo on some systems)
dmesg -T                        # 2. -T = readable timestamps
sudo dmesg -T | tail -5         # 3. only the newest lines
journalctl -k --since "1 hour ago"    # 4. kernel log from the journal, time window
journalctl -k | grep -iE 'oom|ext4'   # 5. filter for what you suspect
```

### fuser / umount - free the mount point

```bash
cd /                                    # 1. make sure YOUR shell is not inside the mount
sudo fuser -vm /srv/shopdata            # 2. who uses it? (-v verbose, -m everything on that mount)
sudo systemctl stop shopapp             # 3. stop the user of the mount, then
sudo umount /srv/shopdata               # 4. unmount
```

### fsck - check a filesystem (unmounted!)

```bash
sudo umount /srv/shopdata               # 1. a filesystem must not be mounted while you repair it
sudo e2fsck -n /path/to.img             # 2. -n = read-only check, answer 'no' to everything: SAFE dry run
sudo e2fsck -f /path/to.img             # 3. -f = force a full check; it asks before each repair (y)
sudo dumpe2fs -h /path/to.img | grep -i state   # 4. -h = header only: 'clean' or 'not clean'
```

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
