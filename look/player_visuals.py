"""Bounded terminal ambient animations; these do not measure audio PCM."""
from __future__ import annotations
import math
import hashlib
import json

NAMES = ('Bars', 'Waves', 'Orbit', 'Tunnel', 'Stars', 'Plasma', 'Album Art', 'Black Hole', 'Cycle')
CYCLE_MODE = len(NAMES)
CYCLE_INTERVAL_SECONDS = 10.0


def active_mode(mode, elapsed):
    """Cycle only through visuals; normal player view is never a timed step."""
    if mode==CYCLE_MODE:
        return 1+int(max(0.0,elapsed)//CYCLE_INTERVAL_SECONDS)%(CYCLE_MODE-1)
    return mode


def frame(mode, width, height, phase, playing=True, seed=0):
    width=max(1,min(240,int(width))); height=max(1,min(80,int(height)))
    t=float(phase) if playing else 0.0
    mode=(int(mode)-1)%len(NAMES)
    canvas=[[' ']*width for _ in range(height)]

    def point(x,y,char='*'):
        x=int(x); y=int(y)
        if 0<=x<width and 0<=y<height: canvas[y][x]=char

    if mode==0:
        for x in range(width):
            amplitude=abs(math.sin(t*1.8+x*.13+seed)*math.cos(t*.7+x*.04)) if playing else .04
            level=int(amplitude*height)
            for y in range(height-level,height): point(x,y,'#' if x%3!=2 else ' ')
    elif mode==1:
        for x in range(width):
            for n in range(3):
                y=(height-1)/2 + math.sin(x/max(1,width)*math.tau*2+t+n*2.1)*(height-1)*.35
                point(x,y,'~+*'[n])
    elif mode==2:
        for i in range(240):
            a=i*math.tau/240
            point((width-1)/2+math.cos(a+t*.6)*width*.38*math.sin(a*3+t*.3),
                  (height-1)/2+math.sin(a+t*.6)*height*.4,'o*.'[i%3])
    elif mode==3:
        for y in range(height):
            for x in range(width):
                dx=(x-(width-1)/2)/max(1,width); dy=(y-(height-1)/2)/max(1,height)
                ring=(math.hypot(dx,dy)*24-t*2)%3
                if ring<.35: point(x,y,':+*'[int(math.hypot(dx,dy)*12)%3])
    elif mode==4:
        for i in range(min(180,max(8,width*height//18))):
            angle=(i*2.399963+seed)*1.0
            depth=(i*.618034+t*.18)%1
            point((width-1)/2+math.cos(angle)*depth*width*.65,
                  (height-1)/2+math.sin(angle)*depth*height*.65,'.+*'[min(2,int(depth*3))])
    elif mode==7:
        return black_hole_frame(width,height,t,seed)
    else:
        ramp=' .:-=+*#%@'
        for y in range(height):
            for x in range(width):
                value=(math.sin(x*.10+t)+math.sin(y*.25-t*.8)+math.sin(math.hypot(x-width/2,(y-height/2)*2)*.12-t))/6+.5
                point(x,y,ramp[max(0,min(len(ramp)-1,int(value*len(ramp))))])
    return [''.join(row) for row in canvas]


# Terminal cells are approximately twice as tall as they are wide.
BLACK_HOLE_RADIUS = .23
BLACK_HOLE_DISC_TILT = .30
BLACK_HOLE_COLOR = '38;5;180'
SHIMMER_PERIOD_SECONDS = 18.0
SHIMMER_DELAY_SECONDS = 5.0
SHIMMER_DURATION_SECONDS = 3.0
SHIMMER_BAND_WIDTH = .065


def black_hole_frame(width,height,phase,seed=0):
    """A dark horizon, tilted accretion disc and lensed light above it."""
    scale=max(1.0,min(width/2,height))
    ramp=' .:-=+*#%@'
    rows=[]
    for y in range(height):
        row=[]
        for x in range(width):
            dx=(x-(width-1)/2)/scale
            dy=(y-(height-1)/2)*2/scale
            radius=math.hypot(dx,dy)
            disc_radius=math.hypot(dx,dy/BLACK_HOLE_DISC_TILT)
            angle=math.atan2(dy/BLACK_HOLE_DISC_TILT,dx)
            swirl=.65+.35*math.sin(angle*5-disc_radius*11+phase*1.4+seed)
            disc=math.exp(-((disc_radius-.66)/.23)**2)*swirl
            # The upper arc suggests light bent around the horizon.
            lens=math.exp(-((radius-.34)/.045)**2)*(.85 if dy<0 else .22)
            light=max(disc,lens) if radius>BLACK_HOLE_RADIUS else 0
            row.append(ramp[min(len(ramp)-1,int(light*(len(ramp)-1)))])
        rows.append(''.join(row))
    return rows


def shimmer_spans(line,y,width,height,elapsed,playing=True):
    """Return plain text runs with a narrow diagonal foreground highlight."""
    age=max(0.0,float(elapsed))%SHIMMER_PERIOD_SECONDS-SHIMMER_DELAY_SECONDS
    if not playing or not 0<=age<SHIMMER_DURATION_SECONDS:
        return [(line,False)]
    progress=age/SHIMMER_DURATION_SECONDS
    runs=[];start=0;previous=None
    for x in range(len(line)):
        diagonal=(x/max(1,width-1)+y/max(1,height-1))/2
        highlight=abs(diagonal-progress)<SHIMMER_BAND_WIDTH
        if previous is not None and highlight!=previous:
            runs.append((line[start:x],previous));start=x
        previous=highlight
    if line:runs.append((line[start:],bool(previous)))
    return runs


# Muted per-track foreground accents; shimmer never changes the palette.
ALBUM_COLORS=('38;5;117','38;5;180','38;5;150','38;5;183','38;5;110','38;5;211')
_album_track=None
_album_color=0


def album_color(snapshot):
    """Deterministic transition choices, stable across pause/seek/redraw."""
    global _album_track,_album_color
    entry=snapshot['entry']
    identity=(snapshot.get('index'),tuple(str(entry.get(key) or '') for key in
              ('node','id','digest','path','artist','title','track')))
    if identity!=_album_track:
        choice=int.from_bytes(hashlib.sha256(json.dumps(identity).encode()).digest()[:4],'big')%len(ALBUM_COLORS)
        if _album_track is not None and choice==_album_color:
            choice=(choice+1)%len(ALBUM_COLORS)
        _album_track=identity; _album_color=choice
    return ALBUM_COLORS[_album_color]
