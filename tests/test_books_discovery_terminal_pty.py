"""Real keyboard/terminal search and favorite handoff with synthetic books only."""
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


def test_search_tab_download_favorite_and_restore_input(tmp_path):
    root=Path(__file__).resolve().parents[1]
    script=r'''
import sys,termios,importlib.machinery,importlib.util
from pathlib import Path
Path.home=staticmethod(lambda:Path(sys.argv[2]))
sys.path[:0]=[sys.argv[1]+'/look',sys.argv[1]+'/core']
l=importlib.machinery.SourceFileLoader('books_ui_test',sys.argv[1]+'/look/lk');s=importlib.util.spec_from_loader(l.name,l);ui=importlib.util.module_from_spec(s);sys.modules[l.name]=ui;l.exec_module(ui)
import books
rows=[{'id':'local','title':'Local Fixture','node':'fixture-owner'}];calls=[]
books.catalog=lambda:{'entries':list(rows)}
def discover(mode,subject='',**kw):
 assert mode=='search' and kw['query']=='Woolf'
 return {'entries':[{'title':'Gutenberg Fixture','author':'Virginia Woolf','url':'https://www.gutenberg.org/ebooks/123.opds'}],'next_index':None}
books.discover=discover
def request(action,**kw):
 calls.append((action,kw))
 if action=='fetch':
  assert kw['node']=='fixture-owner'
  row={'id':'new','title':'Gutenberg Fixture','gutenberg_id':'123','node':'fixture-owner'};rows.append(row)
  return {'book':row,'node':'fixture-owner'}
 assert action=='favorite' and kw=={'node':'fixture-owner','id':'new','selected':True}
 rows[-1]['favorite']=True;return {'ok':True}
books.request=request
before=termios.tcgetattr(0)
books.desk(ui,owner='fixture-owner')
after=termios.tcgetattr(0)
for attrs in (before,after):attrs[3]&=~getattr(termios,'PENDIN',0)
assert before==after and [c[0] for c in calls]==['fetch','favorite']
print('INPUT_RESTORED',flush=True)
assert input()=='hello'
print('DONE',flush=True)
'''
    master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',30,72,0,0))
    env=dict(os.environ,TERM='xterm-256color');env.pop('KITTY_WINDOW_ID',None)
    process=subprocess.Popen([sys.executable,'-u','-c',script,str(root),str(tmp_path)],stdin=slave,stdout=slave,stderr=slave,env=env,start_new_session=True)
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
        assert until(b'Local Fixture'),output[-1500:]
        assert b'Gutenberg' in output and b'discover' in output
        os.write(master,b'/');assert until(b'SEARCH Library'),output[-1500:]
        os.write(master,b'\t');assert until(b'SEARCH Gutenberg'),output[-1500:]
        output=b'';os.write(master,b'Woolf\r');assert until(b'Gutenberg Fixture'),output[-1500:]
        output=b'';os.write(master,b'f');assert until(b'and add to Favorites?'),output[-1500:]
        assert b'fixture-owner' in output
        assert until('› '.encode()),output[-1500:]
        os.write(master,b'y\r');assert until(b'Saved to Favorites'),output[-1500:]
        os.write(master,b'\x1b');assert until(b'INPUT_RESTORED'),output[-1500:]
        os.write(master,b'hello\n');assert until(b'DONE'),output[-1500:]
        process.wait(timeout=3);assert process.returncode==0
    finally:
        if process.poll() is None:process.kill();process.wait(timeout=3)
        os.close(master)
