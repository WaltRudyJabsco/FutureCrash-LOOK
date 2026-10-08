#!/usr/bin/env python3
"""Activate the shared Kitty profile with a recoverable user-config backup."""
import argparse
import datetime
from pathlib import Path
import shutil
import uuid


def configure(directory, source, *, dry_run=False):
    destination = directory / 'kitty.conf'
    data = source.read_bytes()
    if destination.exists() and destination.read_bytes() == data:
        print(f'Kitty profile already current: {destination}')
        return
    backup = None
    if destination.exists() or destination.is_symlink():
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        backup = directory / f'kitty.conf.before-look-{stamp}-{uuid.uuid4().hex[:8]}'
    if dry_run:
        if backup: print(f'[dry-run] back up {destination} to {backup}')
        print(f'[dry-run] activate {source} at {destination}')
        return
    directory.mkdir(parents=True, exist_ok=True)
    if backup:
        # Preserve a symlink itself; replacing the profile never writes its target.
        if destination.is_symlink(): backup.symlink_to(destination.readlink())
        else: shutil.copy2(destination, backup)
        print(f'Previous Kitty config: {backup}')
    temporary = directory / f'.kitty.conf-{uuid.uuid4().hex}'
    try:
        temporary.write_bytes(data)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(f'Kitty profile activated: {destination}')
    print(f'Personal overrides: {directory / "kitty-local.conf"}')
    print('Restart Kitty to apply Option-key behavior. Existing shells stay unchanged.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    configure(Path.home() / '.config/kitty', Path(__file__).resolve().parents[1] / 'terminal/kitty.conf',
              dry_run=args.dry_run)
