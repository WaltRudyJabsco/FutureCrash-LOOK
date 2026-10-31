"""A real Bookokrat handoff returns to the shelf without losing terminal modes."""
import os
from pathlib import Path
import pty
import re
import select
import shutil
import struct
import subprocess
import sys
import termios
import time
import fcntl
import zipfile

import pytest


def test_real_reader_returns_to_books_shelf(tmp_path):
    tool=shutil.which('bookokrat')
    if not tool:pytest.skip('optional Bookokrat binary unavailable')
    source=tmp_path/'fixture.epub'
    with zipfile.ZipFile(source,'w') as archive:
        archive.writestr('mimetype','application/epub+zip')
        archive.writestr('META-INF/container.xml','<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="book.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        archive.writestr('book.opf','<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">test-book</dc:identifier><dc:title>Reader Fixture</dc:title><dc:language>en</dc:language></metadata><manifest><item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="chapter"/></spine></package>')
        archive.writestr('chapter.xhtml','<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Test</title></head><body><h1>TERMINAL READER FIXTURE</h1><p>A quiet chapter inside the terminal.</p></body></html>')
    root=Path(__file__).resolve().parents[1]
    script=r'''
import os,sys,termios,importlib.machinery,importlib.util
from pathlib import Path
Path.home=staticmethod(lambda:Path(sys.argv[3]))
sys.path.insert(0,sys.argv[1]+'/look')
l=importlib.machinery.SourceFileLoader('reader_ui_test',sys.argv[1]+'/look/lk');s=importlib.util.spec_from_loader(l.name,l);ui=importlib.util.module_from_spec(s);l.exec_module(ui)
import books,book_reader
row={'id':'fixture','node':'local','path':sys.argv[2],'title':'Reader Fixture','author':'Test','format':'EPUB','status':'To Read'}
books.catalog=lambda:{'entries':[row]}
books.local_copy=lambda row:Path(sys.argv[2])
book_reader.binary=lambda name:sys.argv[4] if name=='bookokrat' else None
original=book_reader.command
book_reader.command=lambda path,mode=None:original(path,mode)+['--test-mode']
previous=termios.tcgetattr(0)
books.desk(ui,owner='local')
after=termios.tcgetattr(0)
# macOS may set the transient retype-pending bit when canonical input resumes.
for attrs in (previous,after):attrs[3]&=~getattr(termios,'PENDIN',0)
assert after==previous, [(i,a,b) for i,(a,b) in enumerate(zip(previous,after)) if a!=b]
print('TERMINAL_RESTORED')
'''
    master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',34,120,0,0))
    env=dict(os.environ,TERM='xterm-256color',XDG_CONFIG_HOME=str(tmp_path/'config'),XDG_DATA_HOME=str(tmp_path/'data'),XDG_CACHE_HOME=str(tmp_path/'cache'),XDG_STATE_HOME=str(tmp_path/'state'))
    env.pop('KITTY_WINDOW_ID',None)
    process=subprocess.Popen([sys.executable,'-u','-c',script,str(root),str(source),str(tmp_path),tool],stdin=slave,stdout=slave,stderr=slave,env=env,start_new_session=True)
    os.close(slave);output=b''
    def until(needle,timeout=8):
        nonlocal output
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            plain=re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]',b'',output)
            if needle in plain:return True
            if select.select([master],[],[],.02)[0]:
                try:chunk=os.read(master,65536)
                except OSError:break
                if not chunk:break
                output+=chunk
        return False
    try:
        assert until(b'FILTER'),output[-2000:]
        output=b'';os.write(master,b'\r')
        assert until(b'TERMINAL READER FIXTURE'),output[-2000:]
        output=b'';os.write(master,b'q')
        assert until(b'Returned from Bookokrat'),output[-2000:]
        output=b'';os.write(master,b'\x1b')
        assert until(b'TERMINAL_RESTORED'),output[-2000:]
        process.wait(timeout=3);assert process.returncode==0
    finally:
        if process.poll() is None:process.kill();process.wait(timeout=3)
        os.close(master)
