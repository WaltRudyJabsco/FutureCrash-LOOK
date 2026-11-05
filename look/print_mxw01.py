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
MAX_PAPER_MM=3048  # Explicit banner ceiling; not a measured hardware capability.
DOTS_PER_MM=8
MAX_ROWS=int(MAX_PAPER_MM*DOTS_PER_MM)
SYNC_ROWS=512
FEED_ROWS=16
CHUNK_BYTES=ROW_BYTES
WRITE_DELAY=.03
SESSION_SECONDS=1800
COMPLETION_SECONDS=60
MIN_PRINT_MM_PER_SECOND=5  # Generous completion allowance for a long physical feed.
CONTROL_UUID='0000ae01-0000-1000-8000-00805f9b34fb'
NOTIFY_UUID='0000ae02-0000-1000-8000-00805f9b34fb'
DATA_UUID='0000ae03-0000-1000-8000-00805f9b34fb'
ANSI=re.compile(rb'\x1b\[[0-9;]*[A-Za-z]')


def validate(profile):
    if not re.fullmatch(r'(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}',str(profile.get('address',''))):
        raise ValueError('Use the observed Bluetooth printer address')
    if not re.fullmatch(r'hci[0-9]{1,3}',str(profile.get('adapter',''))):
        raise ValueError('Choose an observed Bluetooth adapter such as hci0')
    if profile.get('width')!=WIDTH:raise ValueError('MXW01 uses a 384-dot image width')


def crc8(data):
    crc=0
    for byte in data:
        crc^=byte
        for _ in range(8):crc=((crc<<1)^7)&255 if crc&128 else (crc<<1)&255
    return crc


def command(code,data):
    return bytes([0x22,0x21,code,0])+len(data).to_bytes(2,'little')+data+bytes([crc8(data),255])


def encode(image):
    from PIL import Image
    if image.width>WIDTH or image.height+FEED_ROWS>MAX_ROWS:
        raise ValueError('Tiny Bluetooth receipt is too tall; use a shorter selection or smaller image (configured banner job limit)')
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
    if height+FEED_ROWS>MAX_ROWS:raise ValueError('Tiny Bluetooth receipt is too long; shorten the text (configured banner job limit)')
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
        self.notifications=[]
        self.notification_buffer=b''

    def capture(self,data):
        self.notification_buffer+=ANSI.sub(b'',data)
        while b'\n' in self.notification_buffer:
            line,self.notification_buffer=self.notification_buffer.split(b'\n',1)
            match=re.search(rb'Notification handle = 0x[0-9a-f]+ value: ([0-9a-f ]+)',line,re.I)
            if not match:continue
            frame=bytes.fromhex(match.group(1).decode())
            if len(frame)<7 or frame[:2]!=b'\x22\x21':continue
            size=int.from_bytes(frame[4:6],'little')
            if len(frame)<7+size:raise RuntimeError('Truncated printer notification; inspect output before retrying')
            self.notifications.append((frame[2],frame[6:6+size]))
        self.notification_buffer=self.notification_buffer[-65536:]

    def notification(self,code,timeout=10):
        end=min(self.deadline,time.monotonic()+timeout)
        while time.monotonic()<end:
            for index,(received,payload) in enumerate(self.notifications):
                if received==code:
                    self.notifications.pop(index);return payload
            if select.select([self.master],[],[],.05)[0]:
                data=os.read(self.master,65536)
                if not data:break
                self.capture(data)
                if re.search(rb'(?i)(failed|error:|disconnected)',data):break
        raise RuntimeError('Printer acknowledgment missing; output may be partial. No automatic retry')

    def wait(self,pattern,timeout=10):
        end=min(self.deadline,time.monotonic()+timeout);buf=b''
        while time.monotonic()<end:
            if select.select([self.master],[],[],.05)[0]:
                data=os.read(self.master,65536)
                if not data:break
                self.capture(data)
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
        found=dict((uuid.decode(),handle.decode()) for handle,uuid in re.findall(rb'char value handle\s*[:=]\s*(0x[0-9a-f]+), uuid\s*[:=]\s*([0-9a-f-]+)',reply.group(0)))
        if any(uuid not in found for uuid in (CONTROL_UUID,DATA_UUID,NOTIFY_UUID)):raise RuntimeError('Printer does not expose MXW01 control/data channels')
        # Discover the notification descriptor instead of assuming a device handle.
        start=int(found[NOTIFY_UUID],16)+1;end=int(found[DATA_UUID],16)-1
        self.send(f'char-desc 0x{start:04x} 0x{end:04x}')
        reply=self.wait(rb'handle\s*[:=]\s*(0x[0-9a-f]+), uuid\s*[:=]\s*00002902-0000-1000-8000-00805f9b34fb')
        self.send('char-write-req '+reply.group(1).decode()+' 0100')
        self.wait(b'Characteristic value was written successfully')
        return found[CONTROL_UUID],found[DATA_UUID]

    def write(self,handle,data):
        if len(data)>self.mtu-3:raise ValueError('Write exceeds negotiated Bluetooth packet size')
        if time.monotonic()>=self.deadline:raise RuntimeError('Bluetooth job deadline reached; inspect output before retrying')
        self.send('char-write-cmd '+handle+' '+data.hex())
        time.sleep(WRITE_DELAY)
        # Consume echo/prompts to keep the PTY from blocking; writes have no ACK.
        if select.select([self.master],[],[],0)[0]:
            out=os.read(self.master,65536)
            self.capture(out)
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
            accepted=session.notification(0xa9)
            if not accepted or accepted[0]!=0:raise RuntimeError('Printer rejected image; no image data sent')
            for offset in range(0,len(payload),CHUNK_BYTES):session.write(data,payload[offset:offset+CHUNK_BYTES])
            session.write(control,command(0xad,b'\x00'))
            completion_timeout=max(COMPLETION_SECONDS,rows/DOTS_PER_MM/MIN_PRINT_MM_PER_SECOND+15)
            completed=session.notification(0xaa,completion_timeout)
            if not completed or completed[0]!=0:raise RuntimeError('Printer reported incomplete output; no automatic retry')
            checksum_verified=False
            if len(completed)==3 and completed[1]==completed[2]:
                if completed[1]!=crc8(payload):raise RuntimeError('Printer image checksum mismatch; output may be partial. No automatic retry')
                checksum_verified=True
            return {'transport':'mxw01-ble','rows':rows,'mtu':session.mtu,'completion_acknowledged':True,'checksum_verified':checksum_verified,'note':'Printer acknowledged completion; confirm physical appearance. This job will not be resent automatically.'}
        finally:session.close()
