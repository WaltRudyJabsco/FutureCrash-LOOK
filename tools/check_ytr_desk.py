"""PTY smoke test and screenshot of the compact desk, with an isolated queue."""
from pathlib import Path
import os
import pty
import select
import subprocess
import sys
import tempfile
import time
import fcntl
import termios
import struct

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/youtube-radio';OUT.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='ytr-desk-') as temporary:
    driver=Path(temporary)/'desk.py'
    driver.write_text('''import runpy,sys,types
from pathlib import Path
sys.path.insert(0,sys.argv[1]+'/look')
import ytr
ui=types.SimpleNamespace(**runpy.run_path(sys.argv[1]+'/look/lk',run_name='radio_preview'))
client=ytr.Client('preview',Path(sys.argv[2]))
state={'node':'preview','items':[{'id':'a'*32,'bookmark_revision':0,'title':'A conversation worth keeping','url':'https://youtu.be/abcdefghijk','stage':'queued','position':0,'done':False},{'id':'b'*32,'bookmark_revision':0,'title':'The quiet science of deep space','url':'https://youtu.be/12345678901','stage':'queued','position':0,'done':False}]}
client.snapshot=lambda:state
client.sync=lambda:None
ytr.desk(client,ui)
''')
    master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',24,86,0,0))
    proc=subprocess.Popen([sys.executable,str(driver),str(ROOT),temporary],stdin=slave,stdout=slave,stderr=slave,env=dict(os.environ,TERM='xterm-256color'))
    os.close(slave);chunks=[]
    def read(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            if select.select([master],[],[],.1)[0]:
                try:chunks.append(os.read(master,65536))
                except OSError:break
    read(2);os.write(master,b'v');read(.5)
    capture=b''.join(chunks).decode(errors='replace')
    assert 'YOUTUBE RADIO' in capture and 'A conversation worth keeping' in capture,capture[-2000:]
    os.write(master,b'q');read(.5);proc.wait(timeout=5);os.close(master)
    assert proc.returncode==0
    import pyte
    from PIL import Image,ImageDraw,ImageFont
    screen=pyte.Screen(86,24);stream=pyte.Stream(screen);stream.feed(capture)
    font=ImageFont.truetype('/System/Library/Fonts/Menlo.ttc',15)
    image=Image.new('RGB',(810,500),'#101923');draw=ImageDraw.Draw(image)
    colors={'default':'#d7e5ec','black':'#101923','blue':'#83c9f4','cyan':'#9edacb','white':'#d7e5ec','green':'#a2dcc3','yellow':'#f0bf78'}
    for y in range(24):
        for x in range(86):
            cell=screen.buffer[y][x];color=colors.get(cell.fg,'#'+cell.fg if len(cell.fg)==6 else '#d7e5ec')
            draw.text((16+x*9.1,12+y*19),cell.data,font=font,fill=color)
    image.save(OUT/'radio-desk.png')
    print('PTY desk opens, renders queue/visual, handles quit and restores terminal')
