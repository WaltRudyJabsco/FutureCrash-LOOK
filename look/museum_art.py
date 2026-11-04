"""One local artwork collection for terminal visuals and graphical savers."""
import functools
import json
from pathlib import Path
import re
import time

INTERVAL=20
_rows=[]
_checked=0.0
_stamp=None

def artwork(phase):
    global _rows,_checked,_stamp
    folder=Path.home()/'.local/share/future-crash-look';catalog=folder/'museum.json'
    if time.monotonic()-_checked>5:
        _checked=time.monotonic()
        try:
            stamp=(str(catalog),catalog.stat().st_mtime_ns)
            if stamp!=_stamp:
                data=json.loads(catalog.read_text());_rows=[]
                for row in data.get('items',{}).values():
                    ident=row.get('id','')
                    if not re.fullmatch(r'(met|aic)-[1-9][0-9]{0,9}',ident):continue
                    path=folder/'museum/images'/(ident+'.jpg')
                    if path.is_file() and not path.is_symlink():_rows.append((row,path))
                _rows.sort(key=lambda x:x[0].get('title',''));_stamp=stamp
        except (OSError,ValueError):_rows=[]
    return _rows[int(max(0,phase)//INTERVAL)%len(_rows)] if _rows else (None,None)

@functools.lru_cache(maxsize=16)
def colored_symbols(path,width,height):
    import media_art
    return media_art.symbol_lines(Path(path),width,height)

@functools.lru_cache(maxsize=16)
def symbols(path,width,height):
    try:
        from PIL import Image,ImageOps
        with Image.open(path) as source:
            image=ImageOps.autocontrast(source.convert('L'),cutoff=1)
            image.thumbnail((width,height*2))
            image=image.resize((image.width,max(1,image.height//2)))
            ramp=' .:-=+*#%@'
            pixels=list(image.getdata());left=max(0,(width-image.width)//2)
            return [(' '*left+''.join(ramp[value*(len(ramp)-1)//255] for value in pixels[y*image.width:(y+1)*image.width])).ljust(width) for y in range(image.height)]
    except ImportError:
        import media_art
        return media_art._ascii_via_ffmpeg(Path(path),width,height)


def frame(width,height,phase):
    row,path=artwork(phase)
    if row:
        try:lines=symbols(str(path),width,max(1,height-2))
        except Exception:lines=[]
        lines=(list(lines)+[' '*width]*height)[:max(0,height-2)]
        lines += [row.get('title',''),row.get('artist','')+' · '+row.get('museum','')]
    else:lines=['LOOK MUSEUM','Download art with lk museum','Local artwork appears here offline.']
    return [re.sub(r'[\x00-\x1f\x7f-\x9f]',' ',str(line))[:width].ljust(width) for line in (lines+['']*height)[:height]]
