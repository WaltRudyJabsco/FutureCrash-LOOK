#!/usr/bin/env python3
"""Capture a running terminal UI as a PNG using a private demo HOME.

Development-only dependencies: pyte and Pillow. Nothing is added to runtime
installations. Capture receipts record the command and terminal dimensions.
"""
import argparse
import codecs
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time


def capture(command,output,columns=110,rows=32,seconds=2,send=None,cwd=None,home=None):
    import pyte
    from PIL import Image,ImageDraw,ImageFont
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='look-screenshot-') as temporary:
        demo_home=Path(home or temporary);demo_home.mkdir(parents=True,exist_ok=True)
        env=dict(os.environ,HOME=str(demo_home),USER='demo',LOGNAME='demo',TERM='xterm-256color',
                 LOOK_TERMINAL_THEME='slate',NO_COLOR='',LC_ALL='en_US.UTF-8')
        master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',rows,columns,0,0))
        process=subprocess.Popen(command,stdin=slave,stdout=slave,stderr=slave,cwd=cwd or demo_home,env=env,start_new_session=True)
        os.close(slave);screen=pyte.Screen(columns,rows);stream=pyte.Stream(screen);raw=bytearray()
        deadline=time.monotonic()+seconds;sent=False;decoder=codecs.getincrementaldecoder('utf-8')('replace')
        try:
            while time.monotonic()<deadline:
                if select.select([master],[],[],.04)[0]:
                    try:chunk=os.read(master,65536)
                    except OSError:break
                    raw.extend(chunk);stream.feed(decoder.decode(chunk))
                if send and not sent and len(raw)>200:
                    os.write(master,send.encode().decode('unicode_escape').encode('latin1'));sent=True
                if process.poll() is not None:break
        finally:
            if process.poll() is None:
                os.killpg(process.pid,signal.SIGINT)
                try:process.wait(timeout=2)
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
            os.close(master)
        fonts=['/System/Library/Fonts/Menlo.ttc','/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf']
        font_path=next((path for path in fonts if Path(path).exists()),None)
        if not font_path:raise RuntimeError('Install a monospace font for screenshots')
        font=ImageFont.truetype(font_path,16);cell_width=round(font.getlength('M'));ascent,descent=font.getmetrics();cell_height=ascent+descent+2
        padding=14;image=Image.new('RGB',(columns*cell_width+padding*2,rows*cell_height+padding*2),'#151514');draw=ImageDraw.Draw(image)
        named={'default':'#dedbd3','black':'#151514','red':'#c47b76','green':'#91b38a','brown':'#d6b36a','blue':'#92aecb','magenta':'#b39abc','cyan':'#8bbabd','white':'#dedbd3',
               'brightblack':'#827f76','brightred':'#dc9690','brightgreen':'#adcba5','brightbrown':'#e4c88c','brightblue':'#b0c7df','brightmagenta':'#ccb4d4','brightcyan':'#aad2d5','brightwhite':'#f0eee7'}
        def color(value,background=False):
            if value=='default' and background:return '#151514'
            return named.get(value,'#'+value if len(value)==6 else '#dedbd3')
        for row in range(rows):
            for col in range(columns):
                char=screen.buffer[row][col];fg=color(char.fg);bg=color(char.bg,True)
                if char.reverse:fg,bg=bg,fg
                x=padding+col*cell_width;y=padding+row*cell_height
                draw.rectangle((x,y,x+cell_width-1,y+cell_height-1),fill=bg)
                if char.data and char.data!=' ':draw.text((x,y),char.data,font=font,fill=fg,stroke_width=0)
        image.save(output)
        receipt={'command':command,'columns':columns,'rows':rows,'demo_home':True,'capture':'running program through a PTY; ANSI rendered by pyte','exit_code':process.returncode}
        output.with_suffix('.json').write_text(json.dumps(receipt,indent=2)+'\n')
        return '\n'.join(screen.display)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True);parser.add_argument('--columns',type=int,default=110);parser.add_argument('--rows',type=int,default=32)
    parser.add_argument('--seconds',type=float,default=2);parser.add_argument('--send');parser.add_argument('--cwd');parser.add_argument('--home')
    parser.add_argument('command',nargs=argparse.REMAINDER);args=parser.parse_args()
    command=args.command[1:] if args.command[:1]==['--'] else args.command
    if not command:parser.error('Supply a program after --')
    print(capture(command,args.output,args.columns,args.rows,args.seconds,args.send,args.cwd,args.home))


if __name__=='__main__':main()
