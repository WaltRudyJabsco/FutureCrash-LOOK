"""Original ASCII Pacific Tech diversions: no files, network or player state."""
from __future__ import annotations
import math
import shutil
import sys
import time
import textwrap
try:
    from .games import terminal, read_key
except ImportError:
    from games import terminal, read_key

SCENES=('genius','popcorn','lazlo','kent','laser')
TITLES={'genius':'PACIFIC TECH / AFTER HOURS','popcorn':'HATHAWAY HOME IMPROVEMENT',
        'lazlo':'HOLLYFELD / SWEEPSTAKES DIVISION','kent':'KENT / COMPACT PARKING',
        'laser':'PACIFIC TECH / OPTICAL PARTY FINDER'}
FRAME_SECONDS=1/15
TOUR_SECONDS=14
COLORS={'genius':'96','popcorn':'93','lazlo':'92','kent':'95','laser':'96'}


def frame(scene,width,height,elapsed):
    """Time-based scenes stay deterministic and bounded at every terminal size."""
    width=max(1,min(240,int(width)));height=max(1,min(80,int(height)))
    canvas=[[' ']*width for _ in range(height)]
    age=max(0,float(elapsed))
    def text(x,y,value):
        y=int(y);x=int(x)
        if 0<=y<height:
            for i,char in enumerate(value):
                if 0<=x+i<width:canvas[y][x+i]=char
    def center(y,value):text((width-len(value))//2,y,value)
    def sprite(x,y,rows):
        for offset,line in enumerate(rows):text(x,y+offset,line)
    if scene=='genius':
        center(1,'P A C I F I C   T E C H')
        center(2,'Applied irresponsibility laboratory')
        doors=['1 POPCORN','2 LAZLO','3 KENT','4 LASER']
        for i,label in enumerate(doors):
            x=int((i+.5)*width/4)-6;y=max(4,height//2-3)
            sprite(x,y,['  ________',' |        |',' |  '+str(i+1)+'     |',' |     o  |',' |________|'])
            text(x-1,y+6,label)
        center(height-2,'T tour / choose a door / no exams tonight')
    elif scene=='popcorn':
        stage=age%24
        house_w=min(32,max(10,width//2));left=(width-house_w)//2;bottom=height-2
        roof_y=max(1,bottom-min(8,height-3))
        for row in range(4):
            text(left+house_w//2-row*2,roof_y+row,'/'+'_'*(row*4)+'\\')
        for y in range(roof_y+4,bottom):text(left,y,'|'+' '*(house_w-2)+'|')
        text(left,bottom,'+'+'-'*(house_w-2)+'+')
        fill=int(min(1,stage/12)*max(1,bottom-roof_y-3))
        for y in range(bottom-fill,bottom):
            text(left+1,y,''.join('o*.'[(x*7+y*3)%3] for x in range(house_w-2)))
        if stage<12:
            text(0,1,'LASER '+'='*max(0,left+house_w//2-6)+'>')
            center(0,'A very unconventional kitchen appliance')
        else:
            # Each kernel follows a reproducible ballistic arc from the house.
            for kernel in range(min(180,width*height//4)):
                flight=(stage-12+kernel*.11)%5
                velocity=((kernel*37)%101-50)*.18
                x=width/2+velocity*flight
                y=bottom-(3+(kernel%9))*flight+2.8*flight*flight
                text(x,y,'o*.'[kernel%3])
            center(0,'RENOVATION COMPLETE / extra butter')
    elif scene=='lazlo':
        left=max(1,width//5-7);top=max(2,height//2-4)
        sprite(left,top,[' ______________','|  THE CLOSET  |','|   ________   |','|  |  o  o  |  |','|  |   __   |  |','|  |________|  |','|____|__|______|'])
        printer=min(width-21,left+23)
        sprite(printer,top,['  _____________',' / ENTRIES    /|','|____________| |','| [________] |/','+------------+'])
        count=int(age*23)+1048576
        text(printer,top-1,f'ENTRY {count:08d}')
        for n in range(max(1,height-top-6)):
            text(printer+2,top+5+n,f'| {count-n:08d} |')
        center(0,'FICTIONAL SWEEPSTAKES / nothing submitted')
        center(height-1,'Expected prizes: 32.6% / closet occupancy: 1')
    elif scene=='kent':
        stage=age%20;room_x=max(1,width//2-15);room_y=max(2,height//2-3)
        sprite(room_x,room_y,['+----------------------------+','| KENT / DORMITORY           |',
                                   '|                            |','|                            |',
                                   '|                            |','|                            |',
                                   '+----------------------------+'])
        car=['    _________',' __/___|_____\\__','|_______________|','   O         O']
        progress=min(1,stage/10)
        for i,row in enumerate(car):
            start=-len(row)-i*5
            x=start+(room_x+6-start)*progress
            y=(height-1-i)+(room_y+2+i-(height-1-i))*progress
            text(x,y,row)
        center(0,'Some assembly required. Absolutely no parking.')
        if stage>11:center(height-1,'Your car has been upgraded to an indoor model.')
    elif scene=='laser':
        center(0,'OPTICAL PARTY FINDER / alignment in progress')
        points=[(1,height-2),(width//4,height-2),(width//4,height//3),
                (width*3//4,height//3),(width*3//4,height*2//3),(width-3,height*2//3)]
        budget=int((age%12)/8*(width*2+height*2))
        for (x0,y0),(x1,y1) in zip(points,points[1:]):
            length=abs(x1-x0)+abs(y1-y0)
            for step in range(min(length,max(0,budget))):
                x=x0+(step if x1>x0 else -step if x1<x0 else 0)
                y=y0+(step if y1>y0 else -step if y1<y0 else 0)
                text(x,y,'-' if y0==y1 else '|')
            budget-=length
            text(x1,y1,'/' if y0==y1 else '\\')
        text(0,height-2,'[*]')
        text(max(0,width-17),height-2,'[POOL / PARTY]')
        if age%12>8:
            for i in range(8):
                text(width-10+math.sin(age+i)*6, height//2+math.cos(age*2+i)*height*.25,'*')
            center(1,'Destination acquired. Bring the slippers.')
    else:raise ValueError('Unknown Pacific Tech scene')
    return [''.join(row) for row in canvas]


def run(scene,args=()):
    if args and list(args)!=['--tour']:
        print('usage: lk genius [--tour] / lk popcorn / lk lazlo / lk kent / lk laser')
        return 2
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print(TITLES[scene]);print('\n'.join(frame(scene,76,20,13)))
        return 0
    start=time.monotonic();paused=False;pause_at=0;tour='--tour' in args
    current=scene;last=current;scene_start=start
    try:
        with terminal() as fd:
            while True:
                now=pause_at if paused else time.monotonic()
                elapsed=now-start
                if tour:current=SCENES[1+int(elapsed//TOUR_SECONDS)%4]
                if current!=last:scene_start=now;last=current
                size=shutil.get_terminal_size((80,24));width=max(1,size.columns-1)
                footer=('PAUSED / ' if paused else '')+'1-4 scenes / G lab / T tour / Space pause / Q/Esc exit'
                hints=textwrap.wrap(footer,width)
                height=max(1,size.lines-len(hints)-2)
                rows=frame(current,width,height,now-scene_start)
                sys.stdout.write('\033[H\033['+COLORS[current]+'m'+TITLES[current][:width]+'\033[0m\033[K\n'+
                    '\n'.join('\033['+COLORS[current]+'m'+row+'\033[0m\033[K' for row in rows)+
                    '\n'+'\n'.join(hints)+'\033[J')
                sys.stdout.flush()
                key=read_key(fd,FRAME_SECONDS)
                if key in {'q','esc','\x03'}:return 0
                if key==' ':
                    if paused:
                        delta=time.monotonic()-pause_at;start+=delta;scene_start+=delta
                    else:pause_at=time.monotonic()
                    paused=not paused
                elif key in {'1','2','3','4','g'}:
                    current='genius' if key=='g' else SCENES[int(key)]
                    tour=False;scene_start=now;last=current
                elif key=='t':tour=not tour;start=now
    except (RuntimeError,KeyboardInterrupt):return 0
