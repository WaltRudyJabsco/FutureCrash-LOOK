"""Preserve explicitly supplied Shortcuts files before launching asynchronous LO."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys

MAX_ATTACHMENT_BYTES=100*1024*1024


def prepare(inputs,home=None):
    home=Path(home or Path.home())
    temporary=home/'Library/Group Containers/group.com.apple.shortcuts/Temporary'
    result=[]
    for value in inputs:
        path=Path(value).expanduser()
        try:is_temporary=path.is_absolute() and path.resolve().is_relative_to(temporary.resolve())
        except (OSError,ValueError):is_temporary=False
        if not is_temporary:
            result.append(value);continue
        if not path.is_file():raise ValueError('Shortcuts attachment has expired. Share the original again: '+path.name)
        if path.stat().st_size>MAX_ATTACHMENT_BYTES:raise ValueError('Attachment exceeds 100 MiB; save it to a regular folder first.')
        root=home/'.local/share/look/attachments/shortcuts';root.mkdir(parents=True,exist_ok=True,mode=0o700)
        folder=Path(tempfile.mkdtemp(dir=root));target=folder/path.name
        try:
            shutil.copyfile(path,target);target.chmod(0o600)
        except OSError:
            shutil.rmtree(folder);raise
        result.append(str(target))
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(prog='lk handoff',description=__doc__)
    parser.add_argument('--instruction',default='Help me with this; read supplied documents and follow up as necessary:')
    parser.add_argument('inputs',nargs='+')
    args=parser.parse_args(argv)
    if sys.platform!='darwin':print('LOOK handoff currently supports macOS Shortcuts.');return 1
    try:
        inputs=prepare(args.inputs)
        subprocess.run(['open','-na','kitty','--args',str(Path.home()/'.local/bin/lk'),'o',args.instruction,*inputs],check=True)
        return 0
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        print('LOOK handoff: '+str(exc));return 1
