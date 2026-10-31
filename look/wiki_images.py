"""Optional article images, reusing LOOK's asynchronous ASCII/native rendering."""
from pathlib import Path
import base64
import hashlib
import os
import tempfile
import urllib.parse
import media_art
import look_renderer
from media_ui_work import LatestWork
from notebook_markdown import safe_text


def image(row,*,live=False,archive='',owner='local'):
    import wiki,wiki_online
    key=hashlib.sha256(str((live,owner,archive,row.get('url') or row.get('path'))).encode()).hexdigest()
    folder=Path.home()/'.cache/look/wiki-images';folder.mkdir(parents=True,exist_ok=True)
    for suffix in ('.jpg','.png','.webp'):
        path=folder/(key+suffix)
        if path.is_file():return path
    if live:data,mime=wiki_online.read(row['url'],wiki_online.MAX_IMAGE_BYTES)
    else:
        result=wiki.request('image',node=owner,archive=archive,query=row['path'])
        mime=result['mime'];data=base64.b64decode(result['data'],validate=True)
    suffix={'image/jpeg':'.jpg','image/png':'.png','image/webp':'.webp'}.get(mime)
    if not suffix or len(data)>8*1024*1024:raise ValueError('Unsupported article image or image too large')
    path=folder/(key+suffix);fd,temp=tempfile.mkstemp(dir=folder)
    try:
        with os.fdopen(fd,'wb') as out:out.write(data)
        os.replace(temp,path)
    finally:Path(temp).unlink(missing_ok=True)
    files=sorted(folder.glob('*.*'),key=lambda p:p.stat().st_mtime,reverse=True)
    for old in files[128:]:old.unlink(missing_ok=True)
    return path


def prepare(row,width,height,**source):
    try:
        path=image(row,**source)
        return media_art.symbol_lines(path,width,height),path,''
    except Exception as exc:return [],None,str(exc)


def gallery(ui,fd,article,*,live=False,archive='',owner='local'):
    rows=article.get('images',[])
    if not rows:return 'No pictures in this article. The no-pictures archive cannot supply photos; v selects live Wikipedia.'
    work=LatestWork();native=look_renderer.NativePreviewController();index=0;native_images=True;last=None
    try:
        while True:
            width,height=ui.shutil.get_terminal_size((100,30));width=max(20,width)
            controls=ui._media_hints('←→ image · Shift-←/→ first/last · M image/ASCII · y copy image source · Esc article',width).splitlines()
            art_h=max(2,height-len(controls)-6);art_w=min(90,width-1)
            row=rows[index]
            art,path,error=work.get((index,art_w,art_h),lambda row=dict(row),w=art_w,h=art_h:prepare(row,w,h,live=live,archive=archive,owner=owner),([],None,'Preparing image…'),ttl=60) or ([],None,'Image unavailable')
            frame=[ui._c('ARTICLE IMAGES','1;36')+f' · {index+1}/{len(rows)} · '+('LIVE / CACHED' if live else 'SAVED ARCHIVE'),safe_text(row['title']),*art[:art_h]]
            frame+=['']*max(0,art_h+2-len(frame))
            frame += [ui._c(safe_text(error or ('Auto image' if native_images and native.enabled else 'ASCII')),'2'),ui._c(safe_text(row.get('source') or row.get('path','')),'2'),*controls]
            rendered=ui._terminal_frame_payload('\n'.join(ui._ansi_clip(line,width) for line in frame))
            if rendered!=last:native.frame_cleared();syswrite(rendered);last=rendered
            if path and native_images:native.request(path,3,1,art_h,art_w)
            native.paint_ready()
            key=ui._read_tty_key(fd,.2)
            if key in {'esc','q','\x03'}:return 'Returned from images'
            if key in {'left','up'}:index=max(0,index-1)
            elif key in {'right','down'}:index=min(len(rows)-1,index+1)
            elif key in {'shiftleft','home'}:index=0
            elif key in {'shiftright','end'}:index=len(rows)-1
            elif key=='M':native_images=not native_images;native.frame_cleared();last=None
            elif key=='y':look_renderer.copy_text(row.get('source') or row.get('path',''))
    finally:work.close();native.frame_cleared()


def syswrite(text):
    import sys
    sys.stdout.write(text);sys.stdout.flush()
