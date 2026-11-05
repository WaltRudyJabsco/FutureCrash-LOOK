"""MXW01 receipt transport: explicit LE, negotiated MTU, bounded single attempt."""
import fcntl
import hashlib
import os
from pathlib import Path
import pty
import re
import select
import shutil
import subprocess
import textwrap
import time

WIDTH=384
ROW_BYTES=WIDTH//8
MAX_ROWS=512
FEED_ROWS=16
CHUNK_BYTES=24
WRITE_DELAY=.03
SESSION_SECONDS=55
CONTROL_UUID='0000ae01-0000-1000-8000-00805f9b34fb'
DATA_UUID='0000ae03-0000-1000-8000-00805f9b34fb'
ANSI=re.compile(rb'\x1b\[[0-9;]*[A-Za-z]')


def validate(profile):
    if not re.fullmatch(r'(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}',str(profile.get('address',''))):
        raise ValueError('Use the observed Bluetooth printer address')
    if not re.fullmatch(r'hci[0-9]{1,3}',str(profile.get('adapter',''))):
        raise ValueError('Choose an observed Bluetooth adapter such as hci0')
    if profile.get('width')!=WIDTH:raise ValueError('MXW01 uses a 384-dot image width')


def command(code,data):
    crc=0
    for byte in data:
        crc^=byte
        for _ in range(8):crc=((crc<<1)^7)&255 if crc&128 else (crc<<1)&255
    return bytes([0x22,0x21,code,0])+len(data).to_bytes(2,'little')+data+bytes([crc,255])


def encode(image):
    from PIL import Image
    if image.width>WIDTH or image.height+FEED_ROWS>MAX_ROWS:
        raise ValueError('Tiny Bluetooth receipt is too tall; use a shorter selection or smaller image (6.4 cm limit)')
    canvas=Image.new('1',(WIDTH,image.height+FEED_ROWS),1);canvas.paste(image,(0,0))
    # MXW01 puts the leftmost black pixel in the low bit, unlike ESC/POS.
    reverse=bytes(int(f'{value^255:08b}'[::-1],2) for value in range(256))
    return canvas.tobytes().translate(reverse),canvas.height


def text_image(text):
    from PIL import Image,ImageDraw,ImageFont
    if any(ord(c)<32 and c not in '\n\t\r' or ord(c)==127 for c in text):raise ValueError('Control characters are not printable')
    candidates=('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/usr/share/fonts/TTF/DejaVuSansMono.ttf')
    font=next((ImageFont.truetype(p,20) for p in candidates if Path(p).is_file()),None)
    if font is None:font=ImageFont.load_default(size=20)
    columns=max(1,int((WIDTH-16)/font.getlength('M')))
    lines=[]
    for line in text.expandtabs(4).splitlines():lines.extend(textwrap.wrap(line,columns,replace_whitespace=False) or [''])
    height=16+26*max(1,len(lines))
    if height+FEED_ROWS>MAX_ROWS:raise ValueError('Tiny Bluetooth receipt is too long; shorten the text (6.4 cm limit)')
    image=Image.new('1',(WIDTH,height),1);draw=ImageDraw.Draw(image)
    for index,line in enumerate(lines):draw.text((8,8+index*26),line,font=font,fill=0)
    return image


class Session:
    def __init__(self,profile):
        validate(profile)
        tool=shutil.which('gatttool')
        if not tool:raise RuntimeError('Bluetooth printing needs Linux gatttool (BlueZ tools) on the printer owner')
        self.deadline=time.monotonic()+SESSION_SECONDS
        self.master,slave=pty.openpty()
        try:self.process=subprocess.Popen([tool,'-i',profile['adapter'],'-b',profile['address'],'-t','public','-I'],stdin=slave,stdout=slave,stderr=slave,start_new_session=True,env=dict(os.environ,LC_ALL='C'))
        except BaseException:os.close(self.master);raise
        finally:os.close(slave)
        self.mtu=23

    def wait(self,pattern,timeout=10):
        end=min(self.deadline,time.monotonic()+timeout);buf=b''
        while time.monotonic()<end:
            if select.select([self.master],[],[],.05)[0]:
                data=os.read(self.master,65536)
                if not data:break
                buf=(buf+data)[-65536:];clean=ANSI.sub(b'',buf)
                if re.search(rb'(?i)(error:|failed|disconnected)',clean):raise RuntimeError('Bluetooth transport failed; inspect the print receipt before retrying')
                match=re.search(pattern,clean)
                if match:return match
        raise RuntimeError('Bluetooth response timed out; no automatic retry')

    def send(self,text):os.write(self.master,text.encode('ascii')+b'\n')

    def connect(self):
        self.wait(rb'\[LE\]>');self.send('connect');self.wait(b'Connection successful',15)
        self.send('mtu 128');reply=self.wait(rb'MTU was exchanged successfully: ([0-9]+)')
        self.mtu=int(reply.group(1))
        if self.mtu<CHUNK_BYTES+3:raise RuntimeError('Printer negotiated too small a Bluetooth packet; nothing printed')
        self.send('characteristics')
        reply=self.wait(rb'([\s\S]*0000ae3c-0000-1000-8000-00805f9b34fb)')
        found=dict((uuid.decode(),handle.decode()) for handle,uuid in re.findall(rb'char value handle = (0x[0-9a-f]+), uuid = ([0-9a-f-]+)',reply.group(0)))
        if CONTROL_UUID not in found or DATA_UUID not in found:raise RuntimeError('Printer does not expose MXW01 control/data channels')
        return found[CONTROL_UUID],found[DATA_UUID]

    def write(self,handle,data):
        if len(data)>self.mtu-3:raise ValueError('Write exceeds negotiated Bluetooth packet size')
        if time.monotonic()>=self.deadline:raise RuntimeError('Bluetooth job deadline reached; inspect output before retrying')
        self.send('char-write-cmd '+handle+' '+data.hex())
        time.sleep(WRITE_DELAY)
        # Consume echo/prompts to keep the PTY from blocking; writes have no ACK.
        if select.select([self.master],[],[],0)[0]:
            out=os.read(self.master,65536)
            if re.search(rb'(?i)(failed|error:|disconnected)',out):raise RuntimeError('Bluetooth write failed; inspect output before retrying')

    def close(self):
        try:
            self.send('disconnect');self.send('exit');self.process.wait(timeout=2)
        except (OSError,subprocess.TimeoutExpired):
            self.process.kill();self.process.wait(timeout=2)
        finally:os.close(self.master)


def transmit(profile,payload):
    validate(profile)
    if not payload or len(payload)%ROW_BYTES or len(payload)//ROW_BYTES>MAX_ROWS:raise ValueError('Invalid bounded MXW01 raster')
    root=Path.home()/'.local/share/look/print';root.mkdir(parents=True,exist_ok=True)
    key=hashlib.sha256(profile['address'].upper().encode()).hexdigest()[:20]
    with (root/('bluetooth-'+key+'.lock')).open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Bluetooth printer is busy; this job was not sent')
        session=Session(profile)
        try:
            control,data=session.connect();rows=len(payload)//ROW_BYTES
            session.write(control,command(0xb1,b'\x00'))
            session.write(control,command(0xa9,rows.to_bytes(2,'little')+bytes([ROW_BYTES,0])))
            for offset in range(0,len(payload),CHUNK_BYTES):session.write(data,payload[offset:offset+CHUNK_BYTES])
            session.write(control,command(0xad,b'\x00'));time.sleep(3)
            return {'transport':'mxw01-ble','rows':rows,'mtu':session.mtu,'note':'Transmitted over Bluetooth; confirm physical output. This job will not be resent automatically.'}
        finally:session.close()
