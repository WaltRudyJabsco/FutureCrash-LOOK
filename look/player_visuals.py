"""Bounded terminal ambient animations; these do not measure audio PCM."""
from __future__ import annotations
import math
import hashlib
import json

NAMES = ('Bars', 'Waves', 'Orbit', 'Tunnel', 'Stars', 'Plasma', 'Album Art', 'Black Hole', 'Rooftops', 'Spectrum', 'Moon Jelly', 'Firefly Garden', 'Clockwork Garden', 'Rain on Glass', 'Neon Reef', 'Aurora Loom', 'Paper Lanterns', 'Magnetic Field', 'Comet Trails', 'Orrery', 'Phosphor Rain', 'Cycle')
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
    elif mode==20:
        return phosphor_rain_frame(width,height,t,seed)
    elif mode==19:
        return orrery_frame(width,height,t,seed)
    elif mode==18:
        return comet_trails_frame(width,height,t,seed)
    elif mode==17:
        return magnetic_field_frame(width,height,t,seed)
    elif mode==16:
        return paper_lanterns_frame(width,height,t,seed)
    elif mode==15:
        return aurora_loom_frame(width,height,t,seed)
    elif mode==14:
        return neon_reef_frame(width,height,t,seed)
    elif mode==13:
        return rain_on_glass_frame(width,height,t,seed)
    elif mode==12:
        return clockwork_garden_frame(width,height,t,seed)
    elif mode==11:
        return firefly_garden_frame(width,height,t,seed)
    elif mode==10:
        return moon_jelly_frame(width,height,t,seed)
    elif mode==9:
        return spectrum_frame(width,height,t,seed)
    elif mode==8:
        return rooftop_frame(width,height,t,seed)
    elif mode==7:
        return black_hole_frame(width,height,t,seed)
    else:
        ramp=' .:-=+*#%@'
        for y in range(height):
            for x in range(width):
                value=(math.sin(x*.10+t)+math.sin(y*.25-t*.8)+math.sin(math.hypot(x-width/2,(y-height/2)*2)*.12-t))/6+.5
                point(x,y,ramp[max(0,min(len(ramp)-1,int(value*len(ramp))))])
    return [''.join(row) for row in canvas]


SPECTRUM_BAR_SPACING = 4
SPECTRUM_SPARK_INTERVAL_SECONDS = .9
SPECTRUM_SPARK_LIFETIME_SECONDS = 1.8
# Warm tips grading into green at the base, without changing terminal backgrounds.
SPECTRUM_COLORS = ('38;5;203','38;5;209','38;5;215','38;5;221','38;5;150','38;5;114','38;5;78')
UFO_PERIOD_SECONDS = 47.0
UFO_DELAY_SECONDS = 12.0
UFO_FLIGHT_SECONDS = 6.0
UFO_SPRITE = (' _===_ ', '(o---o)')


def spectrum_frame(width,height,phase,seed=0):
    """Ambient EQ columns with deterministic, fading particles above their tips."""
    canvas=[[' ']*width for _ in range(height)]
    def level(bar,t):
        pulse=(math.sin(t*1.7+bar*.63+seed)+math.sin(t*.8-bar*.37))/4+.5
        return max(1,int((.12+.8*pulse)*height))
    for bar,x in enumerate(range(0,width,SPECTRUM_BAR_SPACING)):
        top=height-level(bar,phase)
        for y in range(top,height):
            for dx in range(min(2,width-x)):canvas[y][x+dx]='=' if y==top else '|'
        # Birth times, rather than redraw counts, keep particles independent of
        # frame rate and allow pause to render the same frame without state.
        interval=SPECTRUM_SPARK_INTERVAL_SECONDS
        birth=math.floor((phase-bar*.17)/interval)*interval+bar*.17
        for previous in range(2):
            emitted=birth-previous*interval
            age=phase-emitted
            if emitted<0 or not 0<=age<SPECTRUM_SPARK_LIFETIME_SECONDS:continue
            y=height-level(bar,emitted)-1-int(age*3)
            px=x+int(math.sin(bar+seed+age*2)*age)
            if 0<=px<width and 0<=y<height and canvas[y][px]==' ':
                canvas[y][px]='*:. '[min(3,int(age/SPECTRUM_SPARK_LIFETIME_SECONDS*4))]
    return [''.join(row) for row in canvas]


def spectrum_color(y,height):
    return SPECTRUM_COLORS[min(len(SPECTRUM_COLORS)-1,y*len(SPECTRUM_COLORS)//max(1,height))]


# Slow skyline, middle-distance towers, then the runner's faster rooftops.
ROOFTOP_LAYERS = ((1.2,14,.42,':'),(4.0,22,.62,'|'))
ROOFTOP_SPEED = 12.0
ROOFTOP_JUMP_LEAD = 4
ROOFTOP_RUN_FRAMES = ((' o ', '/|>', '/ >'),(' o ', '<|\\', ' >\\'))
ROOFTOP_COLOR = '38;5;110'


def rooftop_frame(width,height,phase,seed=0,*,runners=None,span=None):
    """A looping city run; world-space gaps also drive the runner's jumps."""
    canvas=[[' ']*width for _ in range(height)]
    def put(x,y,char):
        if 0<=x<width and 0<=y<height:canvas[y][x]=char
    def shape(tile,layer):
        # Integer mixing keeps buildings stable as they scroll through the view.
        return ((tile*1103515245+seed*12345+layer*2654435761)&0xffffffff)
    for x in range(width):
        if (x+seed)%23==0:put(x,1,'.')
    for layer,(speed,layer_span,baseline,edge) in enumerate(ROOFTOP_LAYERS):
        offset=int(phase*speed)
        floor=min(height-1,int(height*baseline))
        for x in range(width):
            tile,column=divmod(x+offset,layer_span)
            pattern=shape(tile,layer)
            building_width=layer_span-3-pattern%3
            if column>=building_width:continue
            roof=max(2,floor-2-pattern%max(1,height//3))
            for y in range(roof,height):
                char=edge if y==roof or column in (0,building_width-1) else ' '
                if roof<y and column%4==2 and y%3==0:char='.' if layer==0 else '+'
                put(x,y,char)
            if pattern%3==0 and column==building_width//2:put(x,roof-1,'!')
    span=span or max(16,min(36,width//3))
    gap=max(3,min(6,span//5))
    roof=max(0,height-3)
    offset=phase*ROOFTOP_SPEED
    for x in range(width):
        tile,column=divmod(x+int(offset),span)
        if column>=span-gap:continue
        for y in range(roof,height):
            char='=' if y==roof else '|' if column in (0,span-gap-1) else ' '
            if y>roof and column%6 in (2,3):char=':'
            put(x,y,char)
    runner_x=max(0,min(width-3,int(width*.28)))
    # Start before the edge and land beyond the next edge; no independent
    # animation clock that could make the runner jump into a gap.
    jump_start=span-gap-ROOFTOP_JUMP_LEAD
    distance=(runner_x+1+int(offset)-jump_start)%span
    jump_distance=gap+2*ROOFTOP_JUMP_LEAD
    jumping=distance<jump_distance
    progress=distance/jump_distance
    lift=round(4*progress*(1-progress)*min(5,max(1,height//4))) if jumping else 0
    sprite=(' o ','/|>', ' /\\') if jumping else ROOFTOP_RUN_FRAMES[int(phase*8)%len(ROOFTOP_RUN_FRAMES)]
    poses=[(runner_x,lift,sprite)] if runners is None else runners
    for runner_x,lift,sprite in poses:
        for dy,row in enumerate(sprite):
            for dx,char in enumerate(row):put(runner_x+dx,roof-3-lift+dy,char)
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
    age=max(0.0,phase)%UFO_PERIOD_SECONDS-UFO_DELAY_SECONDS
    if width>=len(UFO_SPRITE[0]) and height>=8 and 0<=age<UFO_FLIGHT_SECONDS:
        left=round(-len(UFO_SPRITE[0])+(width+len(UFO_SPRITE[0]))*age/UFO_FLIGHT_SECONDS)
        top=max(0,height//6-1)
        for dy,sprite in enumerate(UFO_SPRITE):
            row=list(rows[top+dy])
            for dx,char in enumerate(sprite):
                if 0<=left+dx<width and char!=' ':row[left+dx]=char
            rows[top+dy]=''.join(row)
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


def moon_jelly_frame(width,height,phase,seed=0):
    """A small nocturnal aquarium: pulsing bells, drifting tendrils and bubbles."""
    canvas=[[' ']*width for _ in range(height)]
    def dot(x,y,char):
        x=round(x);y=round(y)
        if 0<=x<width and 0<=y<height:canvas[y][x]=char
    count=max(1,min(5,width//22))
    for fish in range(count):
        offset=fish*2.3+seed*.01
        cx=(fish+.5)*width/count+math.sin(phase*.27+offset)*width/count*.14
        cy=height*.3+math.sin(phase*.35+offset)*height*.12
        radius=max(2,min(width/count*.3,height*.36))*(.86+.14*math.sin(phase*1.8+offset))
        for i in range(48):
            angle=math.pi+i*math.pi/47
            dot(cx+math.cos(angle)*radius,cy+math.sin(angle)*radius*.45,'.:-'[i%3])
        for strand in range(5):
            anchor=cx+(strand-2)*radius*.35
            for depth in range(max(1,int(height*.48))):
                dot(anchor+math.sin(depth*.55-phase*1.3+offset+strand)*depth*.12,cy+depth,'|' if depth%3==0 else ':')
    for bubble in range(max(2,width//12)):
        dot((bubble*19+seed)%width+math.sin(phase*.4+bubble),height-1-(phase*.8+bubble*7)%height,'o' if bubble%3==0 else '.')
    return [''.join(row) for row in canvas]


FIREFLY_BLINK_SECONDS=4.8
FIREFLY_COLOR='32'  # Follow the terminal's green ink, including Paper palettes.


def firefly_garden_frame(width,height,phase,seed=0):
    """Slow firefly trails above a breeze through a midnight meadow."""
    canvas=[[' ']*width for _ in range(height)]
    def dot(x,y,char):
        x=round(x);y=round(y)
        if 0<=x<width and 0<=y<height:canvas[y][x]=char
    for blade in range(0,width,3):
        length=1+(blade//3*13+seed*3)%max(1,height//4)
        sway=math.sin(phase*.7+blade*.3)
        for stem in range(length):dot(blade+sway*stem*.3,height-1-stem,'/' if sway>0 else '\\')
    for fly in range(max(3,min(36,width*height//65))):
        offset=fly*2.399963+seed*.17
        light=(phase/FIREFLY_BLINK_SECONDS+fly*.381)%1
        if light>.58:continue
        def position(age):
            return ((fly*17+seed+age*(1+fly%3)*.8)%width,
                    height*.38+math.sin(age*.4+offset)*height*.28)
        x,y=position(phase)
        if light<.32:
            tx,ty=position(phase-.8);dot(tx,ty,'.')
        dot(x,y,'*' if .12<light<.3 else '+' if light<.42 else '.')
    return [''.join(row) for row in canvas]


CLOCKWORK_PETALS=7
CLOCKWORK_TURN_RATE=.22
CLOCKWORK_COLOR='33'


def clockwork_garden_frame(width,height,phase,seed=0):
    """Slow counter-rotating rosettes on mechanical stems; purely ambient."""
    canvas=[[' ']*width for _ in range(height)]
    def dot(x,y,char):
        x=round(x);y=round(y)
        if 0<=x<width and 0<=y<height:canvas[y][x]=char
    count=max(1,min(4,width//24))
    for flower in range(count):
        cx=(flower+.5)*width/count;cy=height*(.32+.10*(flower%2))
        radius=max(1,min(width/count*.4,height*.38))
        turn=phase*CLOCKWORK_TURN_RATE*(1 if flower%2 else -1)+flower+seed*.03
        for y in range(round(cy)+1,height):
            dot(cx+math.sin(y*.22+turn)*1.5,y,'|' if y%3 else '+')
        for sample in range(160):
            angle=sample*math.tau/160
            r=radius*(.72+.28*math.cos(CLOCKWORK_PETALS*(angle-turn)))
            dot(cx+math.cos(angle)*r*1.6,cy+math.sin(angle)*r,'.o+'[sample%3])
        for tooth in range(12):
            angle=tooth*math.tau/12-turn
            dot(cx+math.cos(angle)*radius*.35*1.6,cy+math.sin(angle)*radius*.35,':')
        dot(cx,cy,'@')
    return [''.join(row) for row in canvas]


RAIN_COLOR='34'
RAIN_TRAIL_LENGTH=4
REEF_COLOR='36'
REEF_FISH=('><>','<><')


def rain_on_glass_frame(width,height,phase,seed=0):
    """Windowpane droplets leave soft trails above reflected city lights."""
    canvas=[[' ']*width for _ in range(height)]
    reflection=max(0,height-3)
    for x in range(width):
        if (x*7+seed)%13<3:
            for y in range(reflection,height):
                if math.sin(x*.4+y+phase*.7)>.1:canvas[y][x]='.:+'[(x+y)%3]
    for drop in range(max(1,min(72,width//2))):
        x=(drop*17+seed*11)%width
        speed=1.5+(drop%5)*.45
        y=int((phase*speed+drop*7)%(height+RAIN_TRAIL_LENGTH))
        for tail in range(RAIN_TRAIL_LENGTH):
            row=y-tail
            if 0<=row<height:canvas[row][x]='o|:.'[tail]
    return [''.join(row) for row in canvas]


def neon_reef_frame(width,height,phase,seed=0):
    """A quiet ASCII fish tank with swaying seaweed and ascending bubbles."""
    canvas=[[' ']*width for _ in range(height)]
    def put(x,y,char):
        x=round(x);y=round(y)
        if 0<=x<width and 0<=y<height:canvas[y][x]=char
    for plant in range(0,width,9):
        length=1+(plant+seed)%max(1,height//3)
        for stem in range(length):
            sway=math.sin(phase*.6+stem*.4+plant)*stem*.22
            put(plant+sway,height-1-stem,'/' if sway>=0 else '\\')
    for bubble in range(max(1,width//16)):
        put((bubble*19+seed)%width+math.sin(phase*.5+bubble),
            height-1-(phase*.8+bubble*5)%height,'o' if bubble%3==0 else '.')
    for fish in range(max(1,min(8,width//15))):
        direction=1 if fish%2==0 else -1
        x=(fish*23+seed+phase*(2+fish%3)*direction)%(width+6)-3
        y=height*(.2+.13*(fish%4))+math.sin(phase*.55+fish)*height*.07
        for dx,char in enumerate(REEF_FISH[fish%2]):put(x+dx,y,char)
    return [''.join(row) for row in canvas]


AURORA_COLOR = '36'
LANTERN_COLOR = '33'
AURORA_RIBBONS = 4
LANTERN_SPACING = 17


def aurora_loom_frame(width,height,phase,seed=0):
    """Slow ribbons of light weave above a stationary mountain silhouette."""
    canvas=[[' ']*width for _ in range(height)]
    def put(x,y,c):
        y=round(y)
        if 0<=x<width and 0<=y<height:canvas[y][x]=c
    for x in range(width):
        for ribbon in range(AURORA_RIBBONS):
            crest=height*(.18+ribbon*.105)+math.sin(x*.075+phase*.27+ribbon*.8+seed)*height*.13
            depth=1+int((math.sin(x*.09-phase*.38+ribbon)+1)*height*.06)
            for tail in range(depth):put(x,crest+tail,':|.'[(tail+ribbon)%3])
        ridge=height*.83+math.sin(x*.12+seed)*height*.06+math.sin(x*.031)*height*.05
        put(x,ridge,'/\\'[int(math.cos(x*.12+seed)>0)])
    return [''.join(row) for row in canvas]


def paper_lanterns_frame(width,height,phase,seed=0):
    """Tiny lanterns drift into a night sky; their reflections ripple below."""
    canvas=[[' ']*width for _ in range(height)]
    def put(x,y,c):
        x=round(x);y=round(y)
        if 0<=x<width and 0<=y<height:canvas[y][x]=c
    horizon=max(0,int(height*.78))
    for i in range(max(2,width//LANTERN_SPACING)):
        x=(i*LANTERN_SPACING+seed+math.sin(phase*.3+i)*3)%width
        y=horizon-(phase*(.35+i%3*.12)+i*5)%(max(1,horizon)+4)
        sprite=('._.','|o|',"'-'")
        for dy,line in enumerate(sprite):
            for dx,c in enumerate(line):put(x+dx,y+dy,c)
        if height-horizon>1:
            put(x+1+math.sin(phase+i)*2,horizon+1+(i%(height-horizon-1)),'~')
    for x in range(width):
        if (x+int(phase*2))%11<4:put(x,horizon,'~')
    return [''.join(row) for row in canvas]


MAGNETIC_COLOR = '36'
COMET_COLOR = '35'
FIELD_LINES = 16
FIELD_STEPS = 100
FIELD_STEP_SIZE = .055
COMET_COUNT = 5


def magnetic_field_frame(width,height,phase,seed=0):
    """Particles follow bounded dipole streamlines between two moving poles."""
    canvas=[[' ']*width for _ in range(height)]
    def put(x,y,char):
        x=round((x/4+.5)*(width-1));y=round((y/2+.5)*(height-1))
        if 0<=x<width and 0<=y<height:canvas[y][x]=char
    drift=math.sin(phase*.22+seed)*.12
    for line in range(FIELD_LINES):
        angle=(line+.5)*math.tau/FIELD_LINES
        x=-.8+math.cos(angle)*.1;y=drift+math.sin(angle)*.1
        for step in range(FIELD_STEPS):
            left=max(.035,math.hypot(x+.8,y-drift))
            right=max(.035,math.hypot(x-.8,y+drift))
            if right<.08:break
            dx=(x+.8)/left**3-(x-.8)/right**3
            dy=(y-drift)/left**3-(y+drift)/right**3
            norm=max(.001,math.hypot(dx,dy))
            x+=FIELD_STEP_SIZE*dx/norm;y+=FIELD_STEP_SIZE*dy/norm
            if (step-int(phase*9)-line)%15<3:put(x,y,'+' if step%15==0 else '.')
    put(-.8,drift,'+');put(.8,-drift,'o')
    return [''.join(row) for row in canvas]


def comet_trails_frame(width,height,phase,seed=0):
    """Small comets sweep a quiet star field, with gently curving dotted tails."""
    canvas=[[' ']*width for _ in range(height)]
    def put(x,y,char):
        x=round(x);y=round(y)
        if 0<=x<width and 0<=y<height:canvas[y][x]=char
    for i in range(max(1,width*height//85)):
        put((i*37+seed*11)%width,(i*17+seed*3)%height,'.')
    tail=max(3,min(16,width//8));span=width+tail*2
    for i in range(COMET_COUNT):
        head=(phase*(3+i*.65)+i*span/COMET_COUNT+seed)%span-tail
        base=(i*7+seed)%height
        for age in range(tail,0,-1):
            put(head-age,base+math.sin((head-age)*.035+i)*height*.12,'..:--'[min(4,(tail-age)*5//tail)])
        put(head,base+math.sin(head*.035+i)*height*.12,'*')
    return [''.join(row) for row in canvas]


ORRERY_ORBITS=4
ORRERY_COLOR='33'
PHOSPHOR_STREAMS=14
PHOSPHOR_COLOR='36'


def orrery_frame(width,height,phase,seed=0):
    """An inclined clockwork solar system; small planets cross dotted orbits."""
    canvas=[[' ']*width for _ in range(height)]
    def put(x,y,char):
        x=round(x);y=round(y)
        if 0<=x<width and 0<=y<height:canvas[y][x]=char
    cx=(width-1)/2;cy=(height-1)/2
    for orbit in range(1,ORRERY_ORBITS+1):
        rx=width*.45*orbit/ORRERY_ORBITS;ry=height*.4*orbit/ORRERY_ORBITS
        for step in range(max(12,width)):
            angle=step*math.tau/max(12,width)
            put(cx+rx*math.cos(angle),cy+ry*math.sin(angle),'.')
        angle=phase*(1.2/orbit**.8)+seed+orbit
        put(cx+rx*math.cos(angle),cy+ry*math.sin(angle),'oO*@'[orbit-1])
    put(cx,cy,'*')
    return [''.join(row) for row in canvas]


def phosphor_rain_frame(width,height,phase,seed=0):
    """Fine falling phosphor trails land in a pool of expanding ripples."""
    canvas=[[' ']*width for _ in range(height)]
    floor=max(1,height-3)
    def put(x,y,char):
        x=int(x);y=int(y)
        if 0<=x<width and 0<=y<height:canvas[y][x]=char
    for stream in range(PHOSPHOR_STREAMS):
        x=(stream*37+seed*11)%width
        age=(phase*(2+stream%3)+stream*3.7)%(floor+5)
        if age<floor:
            for tail in range(4):put(x,age-tail,'|:..'[tail])
        else:
            radius=int((age-floor)*1.8)
            for side in (-1,1):put(x+side*radius,floor+(radius%2),'~' if radius%2 else '-')
    return [''.join(row) for row in canvas]
