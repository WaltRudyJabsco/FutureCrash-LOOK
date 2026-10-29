"""Artwork children cannot access the TUI's controlling terminal or change input mode."""
import base64
import json
import os
import pty
import re
import select
import shutil
import struct
import subprocess
import sys
import termios
import time
import zlib
from pathlib import Path

import pytest


def png(path,color):
    def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',16,16,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+bytes(color)*16)*16))+chunk(b'IEND',b''))


@pytest.mark.parametrize('kind',['audio','video'])
@pytest.mark.parametrize('backend',['adversarial','real'])
def test_native_art_changes_during_cairo_search_without_owning_input(tmp_path,kind,backend):
    if backend=='real' and not shutil.which('chafa'):pytest.skip('Chafa unavailable')
    root=Path(__file__).resolve().parents[1]
    first=tmp_path/'one.png';second=tmp_path/'two.png';trace=tmp_path/'helpers.jsonl'
    png(first,(255,0,0));png(second,(0,0,255))
    binary=tmp_path/'chafa'
    binary.write_text('#!'+sys.executable+'\n'+r'''
import os,sys,json,termios
owned=False
try:
 fd=os.open('/dev/tty',os.O_RDWR)
 owned=True
 # Reproduce a terminal-probing helper restoring cooked mode while the UI runs.
 attrs=termios.tcgetattr(fd);attrs[3]|=termios.ICANON|termios.ECHO
 termios.tcsetattr(fd,termios.TCSANOW,attrs);os.close(fd)
except OSError:pass
with open(os.environ['PREVIEW_HELPER_TRACE'],'a') as out:
 out.write(json.dumps({'stdin_tty':os.isatty(0),'controlling_tty':owned,'args':sys.argv[1:]})+'\n')
print('+ . +')
''')
    binary.chmod(0o755)
    script=r'''
import os,sys,fcntl,termios,importlib.machinery,importlib.util
fcntl.ioctl(0,termios.TIOCSCTTY,0)
sys.path.insert(0,sys.argv[1]+'/look')
l=importlib.machinery.SourceFileLoader('art_input_tui',sys.argv[1]+'/look/lk');s=importlib.util.spec_from_loader(l.name,l);m=importlib.util.module_from_spec(s);l.exec_module(m)
kind=sys.argv[2]
rows=[{'node':'local','id':'one','path':sys.argv[3],'title':'Coda'}, {'node':'local','id':'two','path':sys.argv[4],'title':'Cairo'}]
for row in rows:row['media_type']='audio/mpeg' if kind=='audio' else 'video/matroska'
m._media_catalog_entries=lambda:(rows,{'nodes':[{'node':'local'}]})
m._media_visibility=lambda:{'hidden_paths':[]}
m.media_core._haystack=lambda row:row['title'].casefold()
m._media_session=lambda:None
m._media_status_snapshot=lambda **kw:None
m._media_remote_preview_state=lambda *a:('local','')
m.shutil.get_terminal_size=lambda *_:os.terminal_size((120,34))
class Durations:
 def __init__(self,*a):pass
 def value(self,row):return None
 def poll(self,*a):return False
 def close(self):pass
m.DurationPreview=Durations
m._media_player_library(media_kind=kind)
'''
    env=dict(os.environ,TERM='xterm-kitty',TERM_PROGRAM='kitty',KITTY_WINDOW_ID='1',LOOK_NATIVE_PREVIEW='1',PREVIEW_HELPER_TRACE=str(trace))
    if backend=='adversarial':env['PATH']=str(tmp_path)+os.pathsep+env.get('PATH','')
    master,slave=pty.openpty()
    process=subprocess.Popen([sys.executable,'-u','-c',script,str(root),kind,str(first),str(second)],stdin=slave,stdout=slave,stderr=slave,env=env,start_new_session=True)
    os.close(slave);output=b''
    def until(needle,timeout=3):
        nonlocal output
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            plain=re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]',b'',output)
            if needle in plain or needle in output:return True
            if select.select([master],[],[],.02)[0]:
                try:data=os.read(master,65536)
                except OSError:break
                if not data:break
                output+=data
        return False
    try:
        assert until(b'FILTER',5),output[-1500:]
        assert until(base64.b64encode(str(first.resolve()).encode())),output[-1500:]
        output=b'';os.write(master,b'/C')
        assert until(b'SEARCH /C'),output[-1500:]
        os.write(master,b'a')
        assert until(base64.b64encode(str(second.resolve()).encode())),output[-1500:]
        os.write(master,b'iro')
        assert until(b'SEARCH /Cairo'),output[-1500:]
        assert process.poll() is None
        attrs=termios.tcgetattr(master)
        assert not attrs[3]&(termios.ICANON|termios.ECHO)
        if backend=='adversarial':
            records=[json.loads(line) for line in trace.read_text().splitlines()]
            assert records and all(not row['stdin_tty'] and not row['controlling_tty'] for row in records)
            assert all('--probe=off' in row['args'] and '--polite=on' in row['args'] for row in records)
    finally:
        if process.poll() is None:
            attrs=termios.tcgetattr(master);attrs[3]&=~(termios.ICANON|termios.ISIG)
            termios.tcsetattr(master,termios.TCSANOW,attrs);os.write(master,b'\x03')
            end=time.monotonic()+1
            while process.poll() is None and time.monotonic()<end:
                if select.select([master],[],[],.01)[0]:
                    try:
                        if not os.read(master,65536):break
                    except OSError:break
            if process.poll() is None:process.kill()
            process.wait(timeout=1)
        os.close(master)
