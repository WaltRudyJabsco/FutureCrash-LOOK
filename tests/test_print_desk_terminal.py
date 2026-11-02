"""Real terminal regression: choose options and restore input, without printing."""
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


@pytest.mark.parametrize('picker',[False,True])
def test_print_desk_and_options_picker_restore_terminal(tmp_path,picker):
    root=Path(__file__).resolve().parents[1]
    script=r'''
import sys,termios,importlib.machinery,importlib.util
sys.path.insert(0,sys.argv[1]+'/look')
l=importlib.machinery.SourceFileLoader('print_ui_test',sys.argv[1]+'/look/lk');s=importlib.util.spec_from_loader(l.name,l);ui=importlib.util.module_from_spec(s);sys.modules[l.name]=ui;l.exec_module(ui)
import printing,print_destinations
rows=[{'name':'brother','node':'mac','device':{'keys':['uuid:one'],'label':'Brother'},'status':'idle'}, {'name':'brother','node':'tower','device':{'keys':['uuid:one'],'label':'Brother'},'status':'idle'}, {'name':'epson','node':'mac','device':{'keys':['uuid:two'],'label':'Epson'},'status':'idle'}]
value={'printers':print_destinations.consolidate(rows),'local_node':'mac'}
printing.destinations=lambda:value
printing.request=lambda action,*args,**kw:{'options':'media/Media: Letter A4\nsides/Sides: one-sided two-sided-long-edge','queue':'brother'}
before=termios.tcgetattr(0)
assert printing.main(['options'] if sys.argv[2]=='True' else [],ui)==0
after=termios.tcgetattr(0)
for attrs in (before,after):attrs[3]&=~getattr(termios,'PENDIN',0)
assert before==after
print('INPUT_RESTORED',flush=True)
assert input()=='hello'
print('DONE',flush=True)
'''
    master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',24,80,0,0))
    env=dict(os.environ,TERM='xterm-256color');env.pop('KITTY_WINDOW_ID',None)
    process=subprocess.Popen([sys.executable,'-u','-c',script,str(root),str(picker)],stdin=slave,stdout=slave,stderr=slave,env=env,start_new_session=True)
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
        assert until(b'Brother'),output[-1500:]
        assert b'Epson' in output and b'2 routes' in output
        os.write(master,b'\r')
        assert until(b'Current / default'),output[-1500:]
        if not picker:
            output=b'';os.write(master,b'q')
            assert until(b'Brother'),output[-1500:]
            os.write(master,b'q')
        assert until(b'INPUT_RESTORED'),output[-1500:]
        os.write(master,b'hello\n');assert until(b'DONE'),output[-1500:]
        process.wait(timeout=3);assert process.returncode==0
    finally:
        if process.poll() is None:process.kill();process.wait(timeout=3)
        os.close(master)
