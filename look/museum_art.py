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
    folder=Path.home()/'.local/share/future-crash-look'
    from museum_cache import folder as cache_folder
    catalogs=[(folder/'museum.json',folder/'museum/images'),(cache_folder()/'catalog.json',cache_folder())]
    if time.monotonic()-_checked>2:
        _checked=time.monotonic()
        stamp=tuple((str(c),c.stat().st_mtime_ns if c.is_file() else None) for c,_ in catalogs)
        if stamp!=_stamp:
            rows={}
            for catalog,images in catalogs:
                try:
                    for row in json.loads(catalog.read_text()).get('items',{}).values():
                        ident=row.get('id','')
                        if not re.fullmatch(r'(met|aic)-[1-9][0-9]{0,9}',ident):continue
                        path=images/(ident+'.jpg')
                        if path.is_file() and not path.is_symlink():rows.setdefault(ident,(row,path))
                except (OSError,ValueError):continue
            _rows=sorted(rows.values(),key=lambda x:x[0].get('title',''));_stamp=stamp
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
    else:lines=['LOOK MUSEUM','Preparing artwork from your Museum collection…','Cached artwork remains available offline.']
    return [re.sub(r'[\x00-\x1f\x7f-\x9f]',' ',str(line))[:width].ljust(width) for line in (lines+['']*height)[:height]]
