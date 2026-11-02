"""Exercise LO's real terminal reader handoff without starting speech or a model."""
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

from test_book_speech import fixture


def test_reader_restores_lo_input_and_owner_progress(tmp_path):
    source=fixture(tmp_path/'book.epub');root=Path(__file__).resolve().parents[1]
    script=r'''
import sys,termios,importlib.machinery,importlib.util
from pathlib import Path
Path.home=staticmethod(lambda:Path(sys.argv[3]))
sys.path.insert(0,sys.argv[1]+'/look')
l=importlib.machinery.SourceFileLoader('lo_reader_test',sys.argv[1]+'/look/lk');s=importlib.util.spec_from_loader(l.name,l);ui=importlib.util.module_from_spec(s);sys.modules[l.name]=ui;l.exec_module(ui)
import books,book_speech
row={'id':'fixture','node':'owner','path':sys.argv[2],'title':'Alexandria Fixture','reading':{'chapter':0,'paragraph':2,'updated':1}}
books.catalog=lambda:{'entries':[row]}
books.local_copy=lambda row:Path(sys.argv[2])
receipts=[]
books.request=lambda action,**kwargs:receipts.append((action,kwargs))
book_speech.voices=lambda:[{'id':'say:Fixture','name':'Fixture','engine':'say'}]
book_speech.Speech.start=lambda *args:(_ for _ in ()).throw(AssertionError('Speech must wait for Enter'))
ui._save_recent_exchange=lambda *args:None
ui._ai_foreground=lambda *args:None
ui._ensure_ollama_server=lambda *args:(_ for _ in ()).throw(AssertionError('No model needed'))
before=termios.tcgetattr(0)
assert ui.ollama_chat(initial_prompt='lets read more alexandria book',one_shot=True)==0
after=termios.tcgetattr(0)
for attrs in (before,after):attrs[3]&=~getattr(termios,'PENDIN',0)
assert before==after
assert receipts[-1][0]=='progress' and receipts[-1][1]['node']=='owner'
assert receipts[-1][1]['fields']['paragraph']==2
print('LO_PROMPT_RESTORED',flush=True)
assert input()=='hello'
print('LO_INPUT_OK',flush=True)
'''
    master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',30,100,0,0))
    env=dict(os.environ,TERM='xterm-256color');env.pop('KITTY_WINDOW_ID',None)
    process=subprocess.Popen([sys.executable,'-u','-c',script,str(root),str(source),str(tmp_path)],stdin=slave,stdout=slave,stderr=slave,env=env,start_new_session=True)
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
        assert until(b'paragraph 3/3'),output[-2000:]
        assert b'Second passage.' in output
        os.write(master,b'q')
        assert until(b'LO_PROMPT_RESTORED'),output[-2000:]
        os.write(master,b'hello\n')
        assert until(b'LO_INPUT_OK'),output[-2000:]
        process.wait(timeout=3);assert process.returncode==0
    finally:
        if process.poll() is None:process.kill();process.wait(timeout=3)
        os.close(master)
