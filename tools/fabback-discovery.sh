#!/usr/bin/env bash
# Inspect the existing FabBack destination. No mounts, writes, or backup jobs.
set -u
if [[ "$(uname -s)" != Linux ]]; then
  printf '%s\n' 'Run this read-only discovery on the Linux 3090.' >&2
  exit 1
fi
printf '%s\n' 'FabBack discovery · read-only' 'Disk inventory:'
lsblk -o NAME,TYPE,SIZE,FSTYPE,LABEL,UUID,MOUNTPOINTS || exit 1
python3 - <<'PY'
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess

command=['lsblk','--json','--bytes','--output','PATH,TYPE,SIZE,FSTYPE,LABEL,UUID,MOUNTPOINTS']
inventory=json.loads(subprocess.check_output(command,text=True))
matches=[]
def inspect(rows):
    for row in rows:
        mounts=[value for value in row.get('mountpoints') or [] if value]
        if str(row.get('label') or '').casefold()=='fabback' or any(Path(value).name.casefold()=='fabback' for value in mounts):
            matches.append({key:row.get(key) for key in ('path','type','size','fstype','label','uuid','mountpoints')})
        inspect(row.get('children') or [])
inspect(inventory.get('blockdevices') or [])
print('\nFabBack matching volumes:')
print(json.dumps(matches,indent=2))
if not matches:
    print('No matching label/mount found. Use the inventory above to identify the existing drive; do not format it.')
for volume in matches:
    for mount in volume.get('mountpoints') or []:
        if not mount:continue
        try:
            usage=shutil.disk_usage(mount)
            info=os.stat(mount)
            print(json.dumps({'mount':mount,'total_bytes':usage.total,'used_bytes':usage.used,
                              'free_bytes':usage.free,'mode':oct(stat.S_IMODE(info.st_mode)),
                              'uid':info.st_uid,'gid':info.st_gid},indent=2))
            subprocess.run(['findmnt','--target',mount,'--output','TARGET,SOURCE,FSTYPE,OPTIONS'],check=False)
        except OSError as exc:print('Mount inspection unavailable:',str(exc))
PY
printf '\n%s\n' 'Available backup tools:'
for tool in restic borg rsync rclone sqlite3 cryptsetup; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf '  %s: %s\n' "$tool" "$(command -v "$tool")"
  else
    printf '  %s: unavailable\n' "$tool"
  fi
done
repo_dir="${1:-.}"
printf '\n%s\n' 'Repository snapshot (when run from the checkout):'
if git -C "$repo_dir" rev-parse --show-toplevel 2>/dev/null; then
  git -C "$repo_dir" log -1 --format='%h %s'
  GIT_OPTIONAL_LOCKS=0 git -C "$repo_dir" status --short
fi
printf '\n%s\n' 'Discovery complete. Existing files remain untouched; no backup directory or repository was created.'
