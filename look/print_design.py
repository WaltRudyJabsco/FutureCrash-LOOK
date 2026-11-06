"""Offline banner lettering and compact fortune slips; rendering never prints."""
import importlib
import io
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import textwrap

FONTS=('standard','small','slant','banner','big')
PACKAGES=('pyfiglet==1.0.4','Pillow>=10,<14')

def dependency_path():return Path.home()/'.local/share/look/lettering/python'

def dependencies():
    path=dependency_path()
    if path.is_dir() and str(path) not in sys.path:sys.path.append(str(path));importlib.invalidate_caches()
    try:
        import pyfiglet
        from PIL import Image
        return pyfiglet
    except ImportError as error:raise ValueError('Run lk print setup to install offline banner and fortune rendering for this account.') from error

def setup():
    try:dependencies();return {'ready':True}
    except ValueError:pass
    path=dependency_path();path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():raise ValueError('Lettering dependency directory already exists; inspect it before replacing it')
    with tempfile.TemporaryDirectory(prefix='.setup-',dir=path.parent) as temp:
        staged=Path(temp)/'python'
        subprocess.run([sys.executable,'-m','pip','--disable-pip-version-check','install','--target',str(staged),*PACKAGES],check=True)
        subprocess.run([sys.executable,'-I','-c','import sys;sys.path.insert(0,sys.argv[1]);import pyfiglet;from PIL import Image;assert pyfiglet.figlet_format("OK")',str(staged)],check=True)
        staged.rename(path)
    return {'ready':True,'path':str(path)}

def text(value,limit):
    if not isinstance(value,str) or not value.strip() or len(value)>limit:raise ValueError(f'Use 1–{limit} characters')
    if any(ord(c)<32 and c not in '\n\t' or ord(c)==127 for c in value):raise ValueError('Use plain text without terminal controls')
    return value

def banner(value,font='standard'):
    value=text(value,120)
    if font not in FONTS:raise ValueError('Choose a supported font: '+', '.join(FONTS))
    if any(ord(c)>126 for c in value):raise ValueError('Banner lettering currently supports printable ASCII text')
    result=dependencies().figlet_format(' '.join(value.split()),font=font,width=4000)
    if len(result)>40000:raise ValueError('Banner is too large; shorten the lettering')
    return result.rstrip('\n')

def font(size):
    from PIL import ImageFont
    candidates=('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/System/Library/Fonts/Menlo.ttc')
    path=next((Path(p) for p in candidates if Path(p).is_file()),None)
    return ImageFont.truetype(str(path),size) if path else ImageFont.load_default(size=size)

def render(value,kind='banner',font_name='standard',width=384,artwork=None):
    dependencies()
    from PIL import Image,ImageDraw
    if type(width) is not int or not 96<=width<=1200:raise ValueError('Unsupported print width')
    if kind=='banner':
        from print_core import receipt_banner
        lettering=banner(value,font_name)
        image=receipt_banner(lettering,1200,rotation=90)
        height=max(1,round(image.height*width/image.width))
        if height>24368:raise ValueError('Banner exceeds ten feet; shorten the text or choose a smaller font')
        image=image.resize((width,height),Image.Resampling.NEAREST)
        details={'kind':kind,'text':value,'font':font_name,'ascii_preview':lettering}
    elif kind=='fortune':
        value=' '.join(text(value,140).split());face=font(max(10,round(width/24)))
        columns=max(1,int((width-24)/face.getlength('M')))
        lines=textwrap.wrap(value,columns)
        if len(lines)>3:raise ValueError('Shorten the fortune to fit one to three lines on this printer')
        step=round(width/16);height=24+step*(len(lines)+2)
        image=Image.new('L',(width,height),255);draw=ImageDraw.Draw(image)
        for i,line in enumerate(lines):draw.text(((width-draw.textlength(line,font=face))/2,10+i*step),line,font=face,fill=0)
        y=12+len(lines)*step;draw.line((width//3,y,2*width//3,y),fill=128,width=1)
        numbers=sorted(secrets.SystemRandom().sample(range(1,50),6))
        lucky='Lucky: '+' '.join(f'{n:02d}' for n in numbers);small=font(max(9,round(width/32)))
        draw.text(((width-draw.textlength(lucky,font=small))/2,y+step//2),lucky,font=small,fill=0)
        details={'kind':kind,'text':value,'lines':lines,'lucky_numbers':numbers,'note':'Random numbers for fun, not a lottery prediction.'}
        if artwork is not None:
            from PIL import ImageOps
            raw,row=artwork
            with Image.open(io.BytesIO(raw)) as source:
                if source.width*source.height>16_000_000:raise ValueError('Museum artwork is too large')
                art=ImageOps.exif_transpose(source).convert('L')
            rotated=art.width>art.height
            if rotated:art=art.rotate(-90,expand=True)
            # Keep enough room for the fortune and credit within a normal receipt.
            art.thumbnail((width,1600))
            factor=min(width/art.width,1600/art.height)
            art=art.resize((max(1,round(art.width*factor)),max(1,round(art.height*factor))))
            caption_font=font(max(16,round(width/16)));caption=[]
            columns=max(1,int((width-16)/caption_font.getlength('M')))
            for key in ('title','artist','date','museum'):
                clean=' '.join(str(row.get(key) or '').split())[:250]
                if clean:caption.extend(textwrap.wrap(clean,columns)[:3])
            caption_step=caption_font.getbbox('Ag')[3]+4;canvas=Image.new('L',(width,image.height+art.height+24+len(caption)*caption_step),255)
            canvas.paste(image,(0,0));canvas.paste(art,((width-art.width)//2,image.height+8));draw=ImageDraw.Draw(canvas)
            for i,line in enumerate(caption):draw.text((8,image.height+art.height+16+i*caption_step),line,font=caption_font,fill=0)
            image=canvas;details['artwork']={key:row.get(key,'') for key in ('id','title','artist','date','museum')};details['artwork_rotation']=90 if rotated else 0
    else:raise ValueError('Choose banner or fortune')
    out=io.BytesIO();image.save(out,format='PNG')
    return out.getvalue(),details

def museum_artwork():
    from museum_desk import Client,preference
    client=Client(preference());snapshot=client.snapshot()
    rows=[r for r in snapshot.get('items',[]) if (r.get('downloaded') or r.get('available_offline')) and not r.get('removal_due')]
    secrets.SystemRandom().shuffle(rows)
    for row in rows[:3]:
        try:return client.image(row).read_bytes(),row
        except (OSError,ValueError):continue
    raise ValueError('No accessible saved Museum artwork. Open lk museum to cache artwork or reconnect to the collection owner; nothing printed.')


if __name__=='__main__':
    if sys.argv[1:]!=['--setup']:raise SystemExit('Use lk print setup')
    print(setup())
