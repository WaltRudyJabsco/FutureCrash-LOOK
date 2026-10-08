#!/usr/bin/env python3
"""Register the installed mpv as a Linux desktop app, retaining working defaults."""
from __future__ import annotations
import argparse, os, shutil, subprocess, sys
from pathlib import Path

MIME_TYPES=('video/mp4','video/x-m4v','video/webm','video/x-matroska','video/quicktime','video/x-msvideo','video/mpeg','audio/mpeg','audio/mp4','audio/flac','audio/ogg','audio/x-wav')
DESKTOP_ID='look-mpv.desktop'


def app_exists(name,data_home):
    bases=[data_home,*[Path(p) for p in os.environ.get('XDG_DATA_DIRS','/usr/local/share:/usr/share').split(':') if p],Path.home()/'.local/share/flatpak/exports/share',Path('/var/lib/flatpak/exports/share'),Path('/home/linuxbrew/.linuxbrew/share')]
    return bool(name) and not Path(name).is_absolute() and '..' not in Path(name).parts and any((base/'applications'/name).is_file() for base in bases)


def configure(binary,data_home,*,dry_run=False):
    target=data_home/'applications'/DESKTOP_ID
    escaped=str(binary).replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')
    content=f'[Desktop Entry]\nType=Application\nName=LOOK mpv\nComment=Play local audio and video with mpv\nExec="{escaped}" --player-operation-mode=pseudo-gui -- %U\nTryExec={binary}\nTerminal=false\nIcon=mpv\nCategories=AudioVideo;Player;Video;\nMimeType={";".join(MIME_TYPES)};\n'
    if dry_run:
        print(f'[dry-run] register mpv at {target}; retain existing working media defaults')
        return
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(content); target.chmod(0o644)
    updater=shutil.which('update-desktop-database')
    if updater: subprocess.run([updater,str(target.parent)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15,check=False)
    mime=shutil.which('xdg-mime')
    changed=[]
    if mime:
        for kind in MIME_TYPES:
            result=subprocess.run([mime,'query','default',kind],capture_output=True,text=True,timeout=8,check=False)
            if not app_exists(result.stdout.strip(),data_home):
                result=subprocess.run([mime,'default',DESKTOP_ID,kind],capture_output=True,text=True,timeout=8,check=False)
                if result.returncode==0: changed.append(kind)
        print('mpv desktop registered · missing associations repaired: '+(', '.join(changed) or 'none'))
    else: print('mpv desktop registered; xdg-mime unavailable, choose LOOK mpv in the file manager')


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--dry-run',action='store_true'); args=parser.parse_args()
    if not sys.platform.startswith('linux'): return 0
    binary=shutil.which('mpv')
    if not binary: print('mpv desktop registration skipped: mpv unavailable'); return 0
    try: configure(binary,Path(os.environ.get('XDG_DATA_HOME') or Path.home()/'.local/share'),dry_run=args.dry_run)
    except (OSError,subprocess.SubprocessError) as exc: print(f'mpv desktop registration: {exc}',file=sys.stderr); return 1
    return 0

if __name__=='__main__': raise SystemExit(main())
