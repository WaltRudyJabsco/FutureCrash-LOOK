"""Six bounded terminal ambient animations; these do not measure audio PCM."""
from __future__ import annotations
import math
import hashlib
import json

NAMES = ('Bars', 'Waves', 'Orbit', 'Tunnel', 'Stars', 'Plasma', 'Album Art')


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
    else:
        ramp=' .:-=+*#%@'
        for y in range(height):
            for x in range(width):
                value=(math.sin(x*.10+t)+math.sin(y*.25-t*.8)+math.sin(math.hypot(x-width/2,(y-height/2)*2)*.12-t))/6+.5
                point(x,y,ramp[max(0,min(len(ramp)-1,int(value*len(ramp))))])
    return [''.join(row) for row in canvas]


# Muted foreground accents; no background changes or animation.
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
