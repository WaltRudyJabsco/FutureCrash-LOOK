"""Foreground screenshot commands. No model, remote capture, or background service."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

MAX_DELAY = 60


def selection(value, count):
    if value == 'all':return list(range(count))
    try: result=list(dict.fromkeys(int(n.strip())-1 for n in value.split(',')))
    except ValueError:raise ValueError('Choose all or display numbers such as 1,3')
    if not result or any(n<0 or n>=count for n in result):raise ValueError('Choose connected display numbers')
    return result


def copy_image(path):
    """Copy full-resolution PNG without applying the shelf attachment size limit."""
    if sys.platform=='darwin':
        script="ObjC.import('AppKit'); function run(a){var p=$.NSPasteboard.generalPasteboard; var d=$.NSData.dataWithContentsOfFile(a[0]); if(!ObjC.unwrap(d)) throw Error('Image unavailable'); p.clearContents; if(!p.setDataForType(d,'public.png')) throw Error('Clipboard write failed');}"
        subprocess.run(['osascript','-l','JavaScript','-e',script,str(path)],check=True,timeout=5,capture_output=True)
    else:
        command=['wl-copy','--type','image/png'] if os.environ.get('WAYLAND_DISPLAY') else ['xclip','-selection','clipboard','-t','image/png']
        if not shutil.which(command[0]):raise ValueError('Install '+command[0]+' for image clipboard support')
        with Path(path).open('rb') as stream:subprocess.run(command,stdin=stream,check=True,timeout=5)


def recording():
    if sys.platform=='darwin':
        return subprocess.run(['/usr/sbin/screencapture','-i','-U','-J','video']).returncode
    if 'gnome' in os.environ.get('XDG_CURRENT_DESKTOP','').lower() and shutil.which('gdbus'):
        print('Choose video mode in the desktop capture toolbar; its stop control ends recording.')
        return subprocess.run(['gdbus','call','--session','--dest','org.gnome.Shell.Screenshot','--object-path','/org/gnome/Shell/Screenshot','--method','org.gnome.Shell.Screenshot.ShowScreenshotUI']).returncode
    if shutil.which('spectacle'):
        print('Use the recording tab in Spectacle.')
        return subprocess.run(['spectacle']).returncode
    raise ValueError('No desktop recorder found. Use your desktop recorder or OBS; screenshot capture is still available.')


def portal_capture(output):
    # Reuse the existing bounded portal helper, with explicit interactive selection.
    sys.path.insert(0,str(Path.home()/'.local/share/future-crash-look/core'))
    import fabric_vision
    python=fabric_vision._portal_python()
    if not python:raise ValueError('Desktop screenshot portal requires Python PyGObject (python3-gi).')
    script=fabric_vision._PORTAL_HELPER.replace('GLib.timeout_add_seconds(12, timeout)', 'GLib.timeout_add_seconds(60, timeout)').replace('"interactive": GLib.Variant("b", False)', '"interactive": GLib.Variant("b", True)')
    result=subprocess.run([python,'-c',script,str(output)],capture_output=True,text=True,timeout=90)
    if result.returncode or not output.exists():raise ValueError(result.stderr.strip() or result.stdout.strip() or 'Screenshot cancelled')


def main(argv=None):
    parser=argparse.ArgumentParser(prog='lk shot',description=__doc__)
    parser.add_argument('screens',nargs='?',help='all, 2, 1,3, or record; omit for numbered picker')
    parser.add_argument('--delay',type=int,default=3,help='Countdown seconds (0–60, default 3)')
    parser.add_argument('--save',type=Path,help='Also save PNG to this file (existing files are not overwritten)')
    args=parser.parse_args(argv)
    if not 0<=args.delay<=MAX_DELAY:parser.error('Delay must be between 0 and 60 seconds')
    try:
        if args.screens=='record':
            if args.save or args.delay!=3:raise ValueError('Recording uses desktop controls for destination and timing; run lk shot record without screenshot options')
            return recording()
        if args.save:
            args.save=args.save.expanduser().absolute()
            if args.save.suffix.lower()!='.png':raise ValueError('Use a .png filename for screenshots')
            if args.save.exists():raise ValueError('Save destination already exists; choose a new filename')
        if sys.platform!='darwin' and (os.environ.get('WAYLAND_DISPLAY') or os.environ.get('XDG_SESSION_TYPE')=='wayland'):
            if args.screens:raise ValueError('Wayland selects screens in the desktop picker. Run lk shot without display numbers.')
            print('Opening the desktop screenshot picker. Selection and timing are controlled by your desktop.')
            with tempfile.TemporaryDirectory(prefix='look-shot-') as folder:
                path=Path(folder)/'screen.png';portal_capture(path);copy_image(path)
                if args.save:
                    with args.save.open('xb') as out:out.write(path.read_bytes())
            print('Screenshot copied to clipboard.');return 0
        if sys.platform!='darwin' and not os.environ.get('DISPLAY'):
            raise ValueError('Run lk shot inside the graphical desktop session')
        import saver
        python=saver.interpreter()
        if not python:raise ValueError('Run lk saver setup to install the shared graphical picker runtime.')
        import json
        return subprocess.run([str(python),str(Path(__file__).with_name('screen_shot_gui.py'))],input=json.dumps(dict(screens=args.screens,delay=args.delay,save=str(args.save) if args.save else '')),text=True).returncode
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        print('LOOK Shot: '+str(exc));return 1
    except KeyboardInterrupt:
        print('Screenshot cancelled.');return 0


if __name__=='__main__':raise SystemExit(main())
