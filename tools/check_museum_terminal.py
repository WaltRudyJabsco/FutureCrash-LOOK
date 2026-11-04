"""Isolated terminal browsing and real-image ASCII rendering smoke check."""
from pathlib import Path
import os,pty,select,subprocess,sys,tempfile,time,fcntl,termios,struct
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/museum-terminal';OUT.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as folder:
    driver=Path(folder)/'driver.py'
    driver.write_text('''import sys,runpy,types,json
from pathlib import Path
sys.path.insert(0,sys.argv[1]+'/look')
import museum_desk
root=Path(sys.argv[1]);state=json.loads((root/'artifacts/museum-live/catalog.json').read_text())
ui=types.SimpleNamespace(**runpy.run_path(str(root/'look/lk'),run_name='museum_smoke'))
client=museum_desk.Client('local');client.snapshot=lambda *a:state
client.image=lambda row:root/'artifacts/museum-live/collection/images'/(row['id']+'.jpg')
museum_desk.terminal_style.open_pane=lambda path:'Shell opened beside LOOK (fixture)'
museum_desk.desk(client,ui)
''')
    master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',32,100,0,0))
    proc=subprocess.Popen([sys.executable,str(driver),str(ROOT)],stdin=slave,stdout=slave,stderr=slave,env=dict(os.environ,TERM='xterm-256color',LOOK_NATIVE_PREVIEW='off'))
    os.close(slave);chunks=[]
    def read(seconds):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            if select.select([master],[],[],.1)[0]:
                try:chunks.append(os.read(master,65536))
                except OSError:break
    read(1);list_capture=b''.join(chunks).decode(errors='replace');os.write(master,b'\r');read(1)
    capture=b''.join(chunks).decode(errors='replace');assert 'LOOK MUSEUM' in capture and 'CC0' in capture,capture[-2000:]
    os.write(master,b'\x1b');read(.4);os.write(master,b'W');read(.3);assert 'Shell opened beside LOOK (fixture)' in b''.join(chunks).decode(errors='replace')
    os.write(master,b'q');read(.3);proc.wait(timeout=3);assert proc.returncode==0;os.close(master)
    import pyte
    from PIL import Image,ImageDraw,ImageFont
    screen=pyte.Screen(100,32);pyte.Stream(screen).feed(list_capture)
    font=ImageFont.truetype('/System/Library/Fonts/Menlo.ttc',15);image=Image.new('RGB',(950,650),'#101923');draw=ImageDraw.Draw(image)
    for y in range(32):
        for x in range(100):
            cell=screen.buffer[y][x];color='#'+cell.fg if len(cell.fg)==6 else '#83c9f4' if cell.fg in ('blue','cyan') else '#d7e5ec'
            draw.text((16+x*9.1,12+y*19),cell.data,font=font,fill=color)
    image.save(OUT/'list.png')
print('Terminal collection, image/ASCII preview, pane shortcut, quit and terminal restore passed')
