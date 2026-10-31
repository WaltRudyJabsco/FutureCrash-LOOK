"""Local, paragraph-addressed book speech. Processes belong only to this reader."""
from __future__ import annotations
import json
import os
from pathlib import Path
import posixpath
import re
import signal
import sys
import subprocess
import tempfile
import textwrap
import zipfile
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit
import book_core
import book_reader
import terminal_style
from notebook_markdown import safe_text

MAX_TEXT_BYTES=16*1024*1024
MAX_CHAPTER_BYTES=2*1024*1024
DEFAULT_RATE=155
MAX_PASSAGE_CHARS=6000


class PassageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.parts=[];self.current=[];self.skip=0;self.title=''
    def flush(self):
        text=' '.join(''.join(self.current).split());self.current=[]
        if text:self.parts.append(text)
    def handle_starttag(self,tag,attrs):
        if tag in {'script','style','head'}:self.skip+=1
        if self.skip:return
        if tag in {'p','div','li','br','h1','h2','h3','blockquote','pre'}:self.flush()
    def handle_endtag(self,tag):
        if tag in {'script','style','head'}:self.skip=max(0,self.skip-1);return
        if self.skip:return
        if tag in {'h1','h2'}:
            if not self.title:self.title=' '.join(''.join(self.current).split())
        if tag in {'p','div','li','h1','h2','h3','blockquote','pre'}:self.flush()
    def handle_data(self,data):
        if not self.skip:self.current.append(data)


def chapters(path):
    path=Path(path)
    if path.suffix.casefold()=='.pdf':
        tool=book_reader.binary('pdftotext')
        if not tool:raise ValueError('PDF speech needs pdftotext (Poppler)')
        with tempfile.TemporaryDirectory(prefix='look-book-text-') as folder:
            out=Path(folder)/'pages.txt'
            subprocess.run([tool,'-layout',str(path),str(out)],stdin=subprocess.DEVNULL,capture_output=True,timeout=60,check=True)
            if out.stat().st_size>MAX_TEXT_BYTES:raise ValueError('Extracted book text exceeds 16 MiB')
            pages=out.read_text(errors='replace').split('\f')
        rows=[{'title':'Page '+str(i+1),'paragraphs':[' '.join(p.split()) for p in re.split(r'\n\s*\n',page) if p.strip()]} for i,page in enumerate(pages)]
    else:
        with zipfile.ZipFile(path) as archive:
            def read(name):
                info=archive.getinfo(name)
                if info.file_size>MAX_CHAPTER_BYTES:raise ValueError('EPUB chapter exceeds 2 MiB')
                return archive.read(info)
            container=book_core.xml(read('META-INF/container.xml'))
            package=next(n.get('full-path') for n in container.iter() if n.tag.endswith('rootfile'))
            opf=book_core.xml(read(package))
            manifest={n.get('id'):n.get('href') for n in opf.iter() if n.tag.endswith('}item') or n.tag=='item'}
            rows=[];total=0
            for item in opf.iter():
                if not (item.tag.endswith('}itemref') or item.tag=='itemref') or item.get('linear')=='no':continue
                href=manifest.get(item.get('idref'))
                if not href:continue
                url=urlsplit(href)
                if url.scheme or url.netloc:continue
                name=posixpath.normpath(posixpath.join(posixpath.dirname(package),unquote(url.path)))
                if name.startswith('../') or name.startswith('/'):raise ValueError('Invalid EPUB chapter path')
                data=read(name);total+=len(data)
                if total>MAX_TEXT_BYTES:raise ValueError('Extracted book text exceeds 16 MiB')
                parser=PassageParser();parser.feed(data.decode('utf-8',errors='replace'));parser.flush()
                rows.append({'title':parser.title or 'Chapter '+str(len(rows)+1),'paragraphs':parser.parts})
    rows=[r for r in rows if r['paragraphs']]
    for row in rows:
        row['paragraphs']=[text[i:i+MAX_PASSAGE_CHARS] for text in row['paragraphs'] for i in range(0,len(text),MAX_PASSAGE_CHARS)]
    if not rows:raise ValueError('No readable text found; scanned PDFs need OCR first')
    return rows


def preferences(**fields):
    path=Path.home()/'.config/look/book-speech.json'
    try:value=json.loads(path.read_text())
    except (OSError,ValueError):value={}
    if fields:value.update(fields);book_reader.write_json(path,value)
    return value


def voices():
    rows=[]
    if book_reader.binary('say'):
        result=subprocess.run([book_reader.binary('say'),'-v','?'],stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=5)
        for line in result.stdout.splitlines():
            match=re.match(r'(.+?)\s+(en_[A-Z]+)\s+#',line)
            if match:rows.append({'id':'say:'+match[1].strip(),'name':match[1].strip(),'locale':match[2],'engine':'say'})
    model=Path.home()/'.local/share/look/book-speech/en_GB-alan-medium.onnx'
    piper=Path.home()/'.local/share/look/book-speech/venv/bin/piper'
    if piper.is_file() and model.is_file() and model.with_suffix('.onnx.json').is_file():
        rows.append({'id':'piper:alan','name':'Alan (neural, offline)','locale':'en_GB','engine':'piper'})
    if book_reader.binary('espeak-ng'):rows.append({'id':'espeak:en-gb','name':'English UK (basic fallback)','locale':'en_GB','engine':'espeak'})
    return rows


def preferred_voice(rows):
    saved=preferences().get('voice')
    return next((r for r in rows if r['id']==saved),None) or next((r for r in rows if r['id']=='say:Jamie (Premium)'),None) or next((r for r in rows if r['engine']=='piper'),None) or next((r for r in rows if r['id']=='say:Daniel'),None) or next((r for r in rows if r['locale']=='en_GB'),None) or next(iter(rows),None)


class Speech:
    def __init__(self,voice,rate=DEFAULT_RATE):
        self.voice=voice;self.rate=rate;self.proc=None;self.phase='stopped';self.paused=False
        self.folder=tempfile.TemporaryDirectory(prefix='look-book-speech-');self.error=''
    def stop(self):
        if self.proc and self.proc.poll() is None:
            try:os.killpg(self.proc.pid,signal.SIGCONT);os.killpg(self.proc.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            try:self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:os.killpg(self.proc.pid,signal.SIGKILL);self.proc.wait(timeout=2)
        self.proc=None;self.paused=False;self.phase='stopped'
    def launch(self,args,**kwargs):
        self.proc=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True,**kwargs)
    def start(self,text):
        self.stop();self.error='';folder=Path(self.folder.name)
        source=folder/'passage.txt';source.write_text(text)
        if self.voice['engine']=='say':
            self.launch([book_reader.binary('say'),'-v',self.voice['name'],'-r',str(self.rate),'-f',str(source)])
            self.phase='reading'
        elif self.voice['engine']=='espeak':
            self.launch([book_reader.binary('espeak-ng'),'-v','en-gb','-s',str(self.rate),'-f',str(source)]);self.phase='reading'
        else:
            root=Path.home()/'.local/share/look/book-speech'
            self.launch([str(root/'venv/bin/piper'),'-m',str(root/'en_GB-alan-medium.onnx'),'--input-file',str(source),'-f',str(folder/'passage.wav')]);self.phase='preparing'
    def pause(self):
        if self.proc and self.proc.poll() is None:
            os.killpg(self.proc.pid,signal.SIGCONT if self.paused else signal.SIGSTOP);self.paused=not self.paused
    def poll(self):
        if not self.proc or self.paused:return False
        result=self.proc.poll()
        if result is None:return False
        if result:self.error='Speech process failed (status '+str(result)+')';self.stop();return False
        if self.phase=='preparing':
            tool=book_reader.binary('mpv')
            if not tool:self.error='Piper playback needs mpv';self.stop();return False
            self.launch([tool,'--no-config','--no-video','--audio-display=no','--terminal=no',str(Path(self.folder.name)/'passage.wav')]);self.phase='reading';return False
        self.stop();return True
    def close(self):self.stop();self.folder.cleanup()


def desk(ui,path,title='',chapter=None,paragraph=None,reading=None,save_reading=None):
    rows=chapters(path);available=voices();voice=preferred_voice(available)
    if not voice:raise ValueError('No local voice. Install a macOS voice or run lk books speech-setup for the offline British neural voice')
    ident=book_core.digest(path);state_path=Path.home()/'.local/share/look/book-speech/positions.json'
    try:positions=json.loads(state_path.read_text());saved=positions.get(ident,{})
    except (OSError,ValueError):positions={};saved={}
    if reading:saved=reading
    ci=max(0,min(len(rows)-1,(chapter-1) if chapter else saved.get('chapter',0)))
    pi=max(0,min(len(rows[ci]['paragraphs'])-1,(paragraph-1) if paragraph else saved.get('paragraph',0)))
    speech=Speech(voice);notice='Enter reads from selected paragraph · speech stays on this computer'
    def save():
        nonlocal notice
        positions[ident]={'chapter':ci,'paragraph':pi};book_reader.write_json(state_path,positions)
        if save_reading:
            try:save_reading(dict(positions[ident],offset=0,finished=False))
            except (OSError,ValueError,RuntimeError):notice='Position saved locally; book owner unavailable'
    try:
        while True:
            width,height=ui.shutil.get_terminal_size((100,30));width=max(20,width);height=max(12,height)
            if speech.poll():
                if pi+1<len(rows[ci]['paragraphs']):pi+=1;save();speech.start(rows[ci]['paragraphs'][pi])
                else:notice='Chapter finished'
            if speech.error:notice=speech.error
            page=max(1,height-10);top=max(0,pi-page//2)
            frame=[ui._c('READ ALOUD','1;36')+' · '+safe_text(title or Path(path).stem),
                   safe_text(rows[ci]['title'])+f' · chapter {ci+1}/{len(rows)} · paragraph {pi+1}/{len(rows[ci]["paragraphs"])}',
                   safe_text(voice['name'])+' · '+('paused' if speech.paused else speech.phase)]
            colors=ui.terminal_style.list_colors()
            for index,text in enumerate(rows[ci]['paragraphs'][top:top+page],top):
                frame.append(ui.terminal_style.list_row(('› ' if index==pi else '  ')+str(index+1)+' '+safe_text(text),width,index,index==pi,colors))
            frame+=['']*max(0,height-7-len(frame))
            frame+=textwrap.wrap(safe_text(rows[ci]['paragraphs'][pi]),width)[:3]
            frame += [ui._media_hints('↑↓ paragraph · ←→ chapter · Shift-arrows page/ends · Enter read · Space pause/resume · s stop · v voice · W shell pane · P clipboard · Esc return',width),safe_text(notice)]
            sysout='\n'.join(ui._ansi_clip(line,width) for line in frame)
            sys.stdout.write(ui._terminal_frame_payload(sysout));sys.stdout.flush()
            key=ui._read_tty_key(sys.stdin.fileno(),.15)
            if not key:continue
            if key in {'esc','q','\x03'}:break
            if key in {'enter','\r','\n'}:speech.start(rows[ci]['paragraphs'][pi]);save();continue
            if key==' ':speech.pause();continue
            if key=='s':speech.stop();save();continue
            if key=='W':notice=terminal_style.open_pane(Path.cwd());continue
            if key=='P':
                import clipboard_shelf
                clipboard_shelf.show(fd=sys.stdin.fileno());continue
            if key=='v':
                voice=available[(available.index(voice)+1)%len(available)];preferences(voice=voice['id']);speech.close();speech=Speech(voice);continue
            old=(ci,pi)
            if key=='left':ci=max(0,ci-1);pi=0
            elif key=='right':ci=min(len(rows)-1,ci+1);pi=0
            elif key=='up':pi-=1
            elif key=='down':pi+=1
            elif key in {'shiftup','pageup'}:pi-=page
            elif key in {'shiftdown','pagedown'}:pi+=page
            elif key in {'shiftleft','home'}:pi=0
            elif key in {'shiftright','end'}:pi=len(rows[ci]['paragraphs'])-1
            pi=max(0,min(len(rows[ci]['paragraphs'])-1,pi))
            if old!=(ci,pi):
                speech.stop();save();notice='Enter reads from this paragraph'
        save()
    finally:speech.close()
    return 'Reading position saved'


def setup_status():
    root=Path.home()/'.local/share/look/book-speech'
    try:value=json.loads((root/'setup.json').read_text())
    except (OSError,ValueError):return {'state':'idle'}
    if value.get('state')=='installing' and value.get('pid'):
        try:os.kill(int(value['pid']),0)
        except (OSError,ValueError):return dict(value,state='failed',error='Voice setup stopped; retry setup')
    return value


def setup(confirmed=False):
    if confirmed is not True:raise PermissionError('Confirm the optional Piper package and British voice download')
    root=Path.home()/'.local/share/look/book-speech';root.mkdir(parents=True,exist_ok=True)
    import fcntl,sys,time
    with (root/'setup.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if setup_status().get('state')=='installing':return setup_status()
        with (root/'setup.log').open('ab') as log:
            proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--setup-worker'],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
        value={'state':'installing','pid':proc.pid,'created':time.time()}
        book_reader.write_json(root/'setup.json',value)
        return value


def setup_worker():
    import sys,time,fcntl
    root=Path.home()/'.local/share/look/book-speech'
    # The parent records the worker before it can finish and publish a result.
    with (root/'setup.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
    try:
        python=root/'venv/bin/python'
        subprocess.run([sys.executable,'-m','venv',str(root/'venv')],check=True,timeout=60,stdin=subprocess.DEVNULL)
        subprocess.run([str(python),'-m','pip','install','piper-tts'],check=True,timeout=600,stdin=subprocess.DEVNULL)
        subprocess.run([str(python),'-m','piper.download_voices','--data-dir',str(root),'en_GB-alan-medium'],check=True,timeout=600,stdin=subprocess.DEVNULL)
        if not (root/'en_GB-alan-medium.onnx').is_file() or not (root/'en_GB-alan-medium.onnx.json').is_file():raise RuntimeError('British voice download is incomplete')
        value={'state':'ready','finished':time.time()}
    except Exception as exc:value={'state':'failed','error':str(exc),'log':str(root/'setup.log'),'finished':time.time()}
    book_reader.write_json(root/'setup.json',value)


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['--setup-worker']:setup_worker()
