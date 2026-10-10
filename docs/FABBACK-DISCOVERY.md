# FabBack discovery

The existing external SSD on 3090 is labeled **FabBack**. It contains valuable
files and is not an empty backup disk. This first inspection creates no backup,
does not format, partition, mount, unlock, install, or modify anything, and does
not read file contents or Fabric credentials.

From the updated FutureCrash-LOOK checkout on 3090:

```sh
bash tools/fabback-discovery.sh
```

The report identifies block devices, filesystem labels and UUIDs, current mount
paths and options, exact free space, mount permissions, installed backup tools,
and the current checkout commit/status. Label matching ignores capitalization
and also checks the mount name; the report preserves the actual device label.
It does not traverse the drive's files. It needs no `sudo`.

Use the results to choose an existing filesystem and a dedicated, explicitly
authorized backup directory. Preserve other drive contents. Identify the
destination by its stable UUID rather than a mutable label or mount path. Before
creating an encrypted repository, choose the backup engine and recovery-key
handling, inventory Fabric's essential state, and establish a restore check.
Automatic backups, retention, cleanup, and backup initialization are future work.
