"""Real Shift+N foreground handoff and return; the child uses a fake spooler."""
import fcntl
import os
from pathlib import Path
import pty
import select
import struct
import subprocess
import sys
import termios
import time
import pytest


@pytest.mark.parametrize('confirm',[False,True])
def test_filer_print_review_and_return(tmp_path,confirm):
    root=Path(__file__).resolve().parents[1];source=tmp_path/'chapter.txt';source.write_text('A chapter')
    child=tmp_path/'print_child.py'
    child.write_text(r'''
import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]+'/look')
import printing,print_desk
print_desk.pick=lambda ui:{'id':'document'}
plan={'id':'a'*32,'node':'owner','queue':'desk','destination':'Document printer','title':'chapter.txt','kind':'document','bytes':9,'options':{'copies':1},'state':'prepared','note':'Not sent'}
printing.prepare_file=lambda *a,**kw:dict(plan)
calls=[]
def request(action,*args,**kwargs):
    calls.append(action)
    if action=='send':return dict(plan,state='queued',receipt={'job':'desk-1','note':'Accepted by fake spooler'})
    assert action=='discard'
    return dict(plan,state='discarded')
printing.request=request
assert printing.selected_file(sys.argv[2],object())==0
assert calls==['send' if sys.argv[3]=='True' else 'discard'],calls
print('CHILD_REVIEW_DONE',flush=True)
''')
    parent=r'''
import sys,termios,subprocess
from pathlib import Path
sys.path.insert(0,sys.argv[1]+'/look')
import look_renderer as renderer
source=Path(sys.argv[2])
original=subprocess.run
def launch(args,**kwargs):
    assert args[-2:]==['_print-file',str(source)],args
    return original([sys.executable,sys.argv[3],sys.argv[1],str(source),sys.argv[4]])
renderer.subprocess.run=launch
renderer.preview_rows=lambda *args,**kwargs:[]
setcbreak=renderer.tty.setcbreak
def ready(*args,**kwargs):
    result=setcbreak(*args,**kwargs);print('FILER_KEY_READY',flush=True);return result
renderer.tty.setcbreak=ready
before=termios.tcgetattr(0)
renderer.pager(['chapter.txt'],24,80,rebuild=lambda *args:['chapter.txt'],browse_rebuild=lambda *args:['chapter.txt'],candidates=lambda query:[source],initial_query='chapter',current_dir=source.parent,force_interactive=True)
after=termios.tcgetattr(0)
for attrs in (before,after):attrs[3]&=~getattr(termios,'PENDIN',0)
assert before==after
print('FILER_RESTORED',flush=True)
assert input()=='hello'
print('DONE',flush=True)
'''
    master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',24,80,0,0))
    env=dict(os.environ,HOME=str(tmp_path),TERM='xterm-256color',TERM_PROGRAM='');env.pop('KITTY_WINDOW_ID',None)
    process=subprocess.Popen([sys.executable,'-u','-c',parent,str(root),str(source),str(child),str(confirm)],stdin=slave,stdout=slave,stderr=slave,env=env,start_new_session=True)
    os.close(slave);output=b''
    def until(needle):
        nonlocal output
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            if needle in output:return True
            if select.select([master],[],[],.03)[0]:
                try:chunk=os.read(master,65536)
                except OSError:break
                if not chunk:break
                output+=chunk
        return False
    try:
        assert until(b'FILER_KEY_READY'),output[-1500:]
        output=b''
        os.write(master,b'N');assert until('› '.encode()),output[-1500:]
        os.write(master,b'p\r' if confirm else b'\r')
        if confirm:
            assert until(b'Enter returns to LOOK'),output[-1500:]
            os.write(master,b'\r')
        assert until(b'CHILD_REVIEW_DONE'),output[-1500:]
        assert until(b'print review closed'),output[-1500:]
        assert until(b'FILER_KEY_READY'),output[-1500:]
        os.write(master,b'Q');assert until(b'FILER_RESTORED'),output[-1500:]
        os.write(master,b'hello\n');assert until(b'DONE'),output[-1500:]
        process.wait(timeout=3);assert process.returncode==0
    finally:
        if process.poll() is None:process.kill();process.wait(timeout=3)
        os.close(master)
