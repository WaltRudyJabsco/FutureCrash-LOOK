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

def banner_preview(value,font_name):
    if font_name=='solid':return ' '.join(text(value,120).split())
    return banner(value,font_name)

def render(value,kind='banner',font_name='solid',width=384,artwork=None):
    dependencies()
    from PIL import Image,ImageDraw
    if type(width) is not int or not 96<=width<=1200:raise ValueError('Unsupported print width')
    if kind=='banner' and font_name=='solid':
        from PIL import ImageFont
        lettering=banner_preview(value,font_name)
        size=round(width*0.85)
        try:face=ImageFont.truetype('DejaVuSans-Bold.ttf',size)
        except OSError:face=font(size)
        left,top,right,bottom=face.getbbox(lettering)
        margin=max(4,width//24)
        length=right-left+2*margin
        if length>24368:raise ValueError('Banner exceeds ten feet; shorten the text')
        canvas=Image.new('L',(length,width),255)
        ImageDraw.Draw(canvas).text((margin-left,(width-(bottom-top))//2-top),lettering,font=face,fill=0)
        image=canvas.transpose(Image.Transpose.ROTATE_270)
        details={'kind':kind,'text':value,'font':font_name,'ascii_preview':lettering}
    elif kind=='banner':
        from print_core import receipt_banner
        lettering=banner(value,font_name)
        image=receipt_banner(lettering,1200,rotation=90)
        height=max(1,round(image.height*width/image.width))
        if height>24368:raise ValueError('Banner exceeds ten feet; shorten the text or choose a smaller font')
        image=image.resize((width,height),Image.Resampling.NEAREST)
        details={'kind':kind,'text':value,'font':font_name,'ascii_preview':lettering}
    elif kind in ('fortune','fortune-cookie'):
        value=' '.join(text(value,140).split())
        face=font(max(8,round(width/14)))
        inset=max(4,round(width/40))
        columns=max(1,int((width-2*inset)/face.getlength('M')))
        lines=textwrap.wrap(value,columns)
        # Preserve the existing content limit while letting larger type use more rows.
        original_face=font(max(10,round(width/24)))
        original_columns=max(1,int((width-24)/original_face.getlength('M')))
        if len(value)>90 and len(textwrap.wrap(value,original_columns))>3:
            raise ValueError('Shorten the fortune to fit this printer')
        numbers=sorted(secrets.SystemRandom().sample(range(1,50),6))
        lucky='Lucky: '+' '.join(f'{n:02d}' for n in numbers)
        # Keep the pocket slip compact while preserving the illustrated card layout.
        scale=0.75 if kind=='fortune-cookie' else 1.0
        image=markdown_bitmap('### '+value+'\n<center>'+lucky+'</center>',width,2438,type_scale=scale)
        details={'kind':kind,'text':value,'lines':lines,'lucky_numbers':numbers,'note':'Random numbers for fun, not a lottery prediction.'}
        if kind=='fortune' and artwork is not None:
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
            credit=credit_bitmap([row.get(key) for key in ('title','artist','date','museum')],width)
            image=stack_receipt(width,image,art,credit)
            details['artwork']={key:row.get(key,'') for key in ('id','title','artist','date','museum')};details['artwork_rotation']=90 if rotated else 0
    else:raise ValueError('Choose banner, fortune or fortune-cookie')
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


def is_receipt_markdown(body):
    import re
    return bool(re.search(r'^(?:#{1,6}\s|<center>|- |\* )|\*\*[^*\n]+\*\*|(?<!\w)[*_][^*_\s\n][^*_\n]*[*_](?!\w)',body,re.M|re.I))


def markdown_bitmap(body,width,max_height,*,type_scale=1.0):
    """Lay out local text only. Links and embedded HTML never execute."""
    import re
    from functools import lru_cache
    from PIL import Image,ImageDraw,ImageFont
    if not body.strip() or len(body)>32000 or any(ord(c)<32 and c not in '\r\n\t' for c in body):
        raise ValueError('Choose up to 32,000 characters of plain Markdown text.')
    margin=max(4,width//48)
    usable=width-2*margin
    y=margin
    rows=[]
    @lru_cache(None)
    def face(size,bold,italic):
        suffix={(False,False):'',(True,False):'-Bold',(False,True):'-Oblique',(True,True):'-BoldOblique'}[bold,italic]
        try:return ImageFont.truetype('DejaVuSans'+suffix+'.ttf',size)
        except OSError:return font(size)
    for line in body.splitlines():
        line=line.strip()
        centered=line.lower().startswith('<center>') and line.lower().endswith('</center>')
        if centered:line=line[8:-9].strip()
        heading=re.match(r'^(#{1,6})\s+(.*)',line)
        level=len(heading[1]) if heading else 0
        if heading:line=heading[2]
        elif line.startswith(('- ','* ')):line='• '+line[2:]
        size=max(10,round(width*([24,42,36,32,29,27,25][level])*type_scale/384))
        advance=round(size*1.36)
        if not line:
            y+=advance//2
            continue
        row=[];x=0
        for chunk in re.split(r'(\*\*[^*]+\*\*|__[^_]+__|(?<!\w)\*[^*]+\*(?!\w)|(?<!\w)_[^_]+_(?!\w))',line):
            bold=chunk.startswith(('**','__')) and len(chunk)>4
            italic=not bold and len(chunk)>2 and chunk[0] in '*_' and chunk[-1]==chunk[0]
            chunk=chunk[2:-2] if bold else chunk[1:-1] if italic else chunk
            style=face(size,bool(heading or bold),italic)
            for word in re.findall(r'\s+|\S+',chunk):
                if word.isspace():word=' '
                if x and x+style.getlength(word)>usable:
                    rows.append((row,x,y,centered or level==1));row=[];x=0;y+=advance
                if not x and word==' ':continue
                for ch in word:
                    w=style.getlength(ch)
                    if x+w>usable:
                        rows.append((row,x,y,centered or level==1));row=[];x=0;y+=advance
                    row.append((x,ch,style));x+=w
        if row:rows.append((row,x,y,centered or level==1));y+=advance
        if y+margin>max_height:raise ValueError('Formatted receipt exceeds the paper allowance; choose a shorter passage.')
    if y+margin>max_height:raise ValueError('Formatted receipt exceeds the paper allowance.')
    image=Image.new('L',(width,y+margin),255);draw=ImageDraw.Draw(image)
    for row,length,top,center in rows:
        left=(width-length)/2 if center else margin
        for offset,ch,style in row:draw.text((left+offset,top),ch,font=style,fill=0)
    return image


def stack_receipt(width,*parts):
    from PIL import Image
    parts=[part for part in parts if part is not None]
    canvas=Image.new('L',(width,sum(part.height for part in parts)),255)
    y=0
    for part in parts:
        canvas.paste(part,((width-part.width)//2,y))
        y+=part.height
    return canvas


def credit_bitmap(fields,width):
    lines=[' '.join(str(value).split())[:250] for value in fields if value and str(value).strip()]
    if not lines:return None
    lines[0]='### '+lines[0]
    return markdown_bitmap('\n'.join(lines),width,8192)


def song_bitmap(entry,cover,width):
    from PIL import Image,ImageOps
    def field(key):return ' '.join(str(entry.get(key) or '').split())[:250]
    lines=['# '+(field('title') or 'Untitled track')]
    if field('artist'):lines.append('**'+field('artist')+'**')
    if field('album'):lines.append('*'+field('album')+'*')
    info=markdown_bitmap('\n'.join(lines),width,8192)
    art=None
    if cover:
        with Image.open(cover) as source:
            if source.width*source.height>16_000_000:raise ValueError('Album cover is too large')
            art=ImageOps.exif_transpose(source).convert('L')
            art.thumbnail((width,width))
    return stack_receipt(width,info,art)
