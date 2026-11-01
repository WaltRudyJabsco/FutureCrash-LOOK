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
MIN_SPEED=.5
MAX_SPEED=2.0
SPEED_STEP=.1
PIPER_MODELS={'piper:alan':'en_GB-alan-medium','piper:alba':'en_GB-alba-medium'}
MAX_NATIVE_TEXT_CHARS=128000
MAX_NATIVE_REQUEST_BYTES=MAX_NATIVE_TEXT_CHARS*6+4096
MAX_PASSAGE_CHARS=6000
IMAGE_TYPES={'image/png','image/jpeg','image/gif','image/webp'}
MAX_CHAPTER_IMAGES=128


class PassageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.parts=[];self.current=[];self.skip=0;self.title='';self.images=[]
    def flush(self):
        text=' '.join(''.join(self.current).split());self.current=[]
        if text:self.parts.append(text)
    def handle_starttag(self,tag,attrs):
        if tag in {'script','style','head'}:self.skip+=1
        if self.skip:return
        if tag in {'img','image'} and len(self.images)<MAX_CHAPTER_IMAGES:
            fields=dict(attrs)
            # Images never split narration paragraphs or move existing bookmarks.
            self.images.append({'before':len(self.parts)+bool(''.join(self.current).strip()),
                'source':fields.get('src') or fields.get('href') or fields.get('xlink:href') or '',
                'alt':(fields.get('alt') or '')[:500]})
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
            image_names=set()
            for entry in opf.iter():
                if entry.get('media-type') not in IMAGE_TYPES:continue
                url=urlsplit(entry.get('href',''))
                if url.scheme or url.netloc:continue
                image_names.add(posixpath.normpath(posixpath.join(posixpath.dirname(package),unquote(url.path))))
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
                images=[]
                for image in parser.images:
                    url=urlsplit(image['source'])
                    if url.scheme or url.netloc:continue
                    source=posixpath.normpath(posixpath.join(posixpath.dirname(name),unquote(url.path)))
                    if source.startswith(('../','/')) or source not in image_names:continue
                    images.append(dict(image,source=source))
                rows.append({'title':parser.title or 'Chapter '+str(len(rows)+1),'paragraphs':parser.parts,'images':images})
    # Keep image-only spine pages without introducing new narration chapter IDs.
    readable=[];leading_images=[]
    for row in rows:
        if row['paragraphs']:
            row['images']=(leading_images+row.get('images',[]))[:MAX_CHAPTER_IMAGES]
            leading_images=[];readable.append(row)
        elif readable:
            prior=readable[-1]
            prior['images']=(prior.get('images',[])+[dict(image,before=len(prior['paragraphs']))
                for image in row.get('images',[])])[:MAX_CHAPTER_IMAGES]
        else:
            leading_images=(leading_images+[dict(image,before=0) for image in row.get('images',[])])[:MAX_CHAPTER_IMAGES]
    rows=readable
    for row in rows:
        offsets=[0]
        for text in row['paragraphs']:offsets.append(offsets[-1]+(len(text)+MAX_PASSAGE_CHARS-1)//MAX_PASSAGE_CHARS)
        for image in row.get('images',[]):image['before']=offsets[image['before']]
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
    root=Path.home()/'.local/share/look/book-speech'
    piper=root/'venv/bin/piper'
    for ident,stem in PIPER_MODELS.items():
        model=root/(stem+'.onnx')
        if piper.is_file() and model.is_file() and model.with_suffix('.onnx.json').is_file():
            name='Alan' if ident=='piper:alan' else 'Alba'
            rows.append({'id':ident,'name':name+' (neural, offline)','locale':'en_GB','engine':'piper'})
    if book_reader.binary('espeak-ng'):
        rows.extend([{'id':'espeak:en-gb','name':'English UK (basic male fallback)','locale':'en_GB','engine':'espeak'},
                     {'id':'espeak:en-gb+f3','name':'English UK (basic female fallback)','locale':'en_GB','engine':'espeak'}])
    # Repeated macOS IDs made index() jump back rather than wrap at the end.
    rows=list({row['id']:row for row in rows}.values())
    standard=[row for row in standard_voices(rows).values() if row]
    return standard+[row for row in rows if row['id'] not in {voice['id'] for voice in standard}]


def preferred_voice(rows):
    saved=preferences().get('voice')
    return next((r for r in rows if r['id']==saved),None) or default_voice(rows)


def standard_voices(rows):
    """Choose installed narrators explicitly; never infer gender from a locale."""
    def choose(ids):return next((row for ident in ids for row in rows if row['id']==ident),None)
    return {'male':choose(('say:Jamie (Premium)','say:Jamie (Enhanced)','piper:alan','say:Daniel (Premium)','say:Daniel (Enhanced)','say:Daniel','say:Daniel (English (UK))','espeak:en-gb')),
            'female':choose(('say:Serena (Premium)','say:Serena (Enhanced)','say:Kate (Premium)','say:Kate (Enhanced)','piper:alba','say:Serena','say:Kate','say:Shelley (English (UK))','say:Flo (English (UK))','espeak:en-gb+f3'))}


def default_voice(rows):
    return standard_voices(rows)['male'] or next((r for r in rows if r.get('locale')=='en_GB'),None) or next(iter(rows),None)


def voice_label(voice,rows):
    kind=next((kind for kind,row in standard_voices(rows).items() if row and row['id']==voice['id']),None)
    return ('British '+kind+' — ' if kind else '')+voice['name']


def piper_model(voice):
    # Model filenames come from our registry, never from request parameters.
    stem=PIPER_MODELS.get(voice['id'])
    if not stem:raise ValueError('Unknown Piper narration voice')
    return Path.home()/'.local/share/look/book-speech'/(stem+'.onnx')


def espeak_voice(voice):
    return 'en-gb+f3' if voice['id']=='espeak:en-gb+f3' else 'en-gb'


def reading_speed(value=1):
    import math
    try:value=float(value)
    except (TypeError,ValueError):return 1.0
    return min(MAX_SPEED,max(MIN_SPEED,value)) if math.isfinite(value) else 1.0


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
            self.launch([book_reader.binary('espeak-ng'),'-v',espeak_voice(self.voice),'-s',str(self.rate),'-f',str(source)]);self.phase='reading'
        else:
            root=Path.home()/'.local/share/look/book-speech'
            self.launch([str(root/'venv/bin/piper'),'-m',str(piper_model(self.voice)),'--input-file',str(source),'-f',str(folder/'passage.wav')]);self.phase='preparing'
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
            self.launch([tool,'--no-config','--no-video','--audio-display=no','--terminal=no',f'--speed={self.rate/DEFAULT_RATE:.3f}','--audio-pitch-correction=yes',str(Path(self.folder.name)/'passage.wav')]);self.phase='reading';return False
        self.stop();return True
    def close(self):self.stop();self.folder.cleanup()


def desk(ui,path,title='',chapter=None,paragraph=None,reading=None,save_reading=None):
    import clipboard_shelf
    rows=chapters(path);available=voices();voice=preferred_voice(available)
    if not voice:raise ValueError('No local voice. Install a macOS voice or run lk books speech-setup for offline British male/female neural voices')
    ident=book_core.digest(path);state_path=Path.home()/'.local/share/look/book-speech/positions.json'
    try:positions=json.loads(state_path.read_text());saved=positions.get(ident,{})
    except (OSError,ValueError):positions={};saved={}
    if reading:saved=reading
    ci=max(0,min(len(rows)-1,(chapter-1) if chapter else saved.get('chapter',0)))
    pi=max(0,min(len(rows[ci]['paragraphs'])-1,(paragraph-1) if paragraph else saved.get('paragraph',0)))
    speed=reading_speed(preferences().get('speed',1))
    speech=Speech(voice,round(DEFAULT_RATE*speed));notice='Enter reads from selected paragraph · speech stays on this computer';scroll=None
    layout_key=None;lines=[];starts=[]
    if os.environ.get('KITTY_WINDOW_ID') or os.environ.get('TERM')=='xterm-kitty':sys.stdout.write('\x1b_Ga=d,d=a,q=2\x1b\\')
    sys.stdout.write('\x1b[0m\x1b[2J\x1b[H');sys.stdout.flush()
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
                if pi+1<len(rows[ci]['paragraphs']):pi+=1;scroll=None;save();speech.start(rows[ci]['paragraphs'][pi])
                else:notice='Chapter finished'
            if speech.error:notice=speech.error
            frame=[ui._c('READ ALOUD','1;36')+' · '+safe_text(title or Path(path).stem),
                   safe_text(rows[ci]['title'])+f' · chapter {ci+1}/{len(rows)} · paragraph {pi+1}/{len(rows[ci]["paragraphs"])}',
                   safe_text(voice_label(voice,available))+f' · voice {available.index(voice)+1}/{len(available)} · {speed:.1f}× · '+('paused' if speech.paused else speech.phase)]
            colors=ui.terminal_style.list_colors()
            footer=clipboard_shelf.command_rows([('↑↓','paragraph'),('←→','chapter'),('PgUp/PgDn','scroll'),('Shift-←/→','ends'),('Enter','read'),('Space','pause/resume'),('s','stop'),('v','next voice'),('V','default voice'),('−/+','speed'),('P','clipboard'),('W','shell pane'),('q/Esc','return')],width,colors)
            notes=clipboard_shelf.wrap_cells(safe_text(notice),width)[:2]
            page=max(1,height-len(frame)-len(footer)-len(notes))
            # Wrapping a long chapter belongs to navigation/reflow, not idle ticks.
            if layout_key!=(ci,width):
                lines=[];starts=[];layout_key=(ci,width)
                for index,text in enumerate(rows[ci]['paragraphs']):
                    starts.append(len(lines));prefix='  '+str(index+1)+' ';size=max(1,width-len(prefix))
                    wrapped=[part for line in textwrap.wrap(safe_text(text),size) or [''] for part in clipboard_shelf.wrap_cells(line,size)]
                    for number,line in enumerate(wrapped):lines.append((index,(prefix if number==0 else ' '*len(prefix))+line))
                    lines.append((index,''))
            if scroll is None:scroll=max(0,starts[pi]-page//3)
            scroll=max(0,min(scroll,max(0,len(lines)-page)))
            frame += [ui.terminal_style.list_row(('› '+text[2:] if index==pi and line==starts[index] else text),width,index,index==pi,colors) for line,(index,text) in enumerate(lines[scroll:scroll+page],scroll)]
            frame+=['']*max(0,height-len(footer)-len(notes)-len(frame))
            frame+=footer+notes
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
            if key in {'v','V','-','+','='}:
                playing=speech.phase!='stopped';paused=speech.paused
                if key in {'v','V'}:
                    voice=default_voice(available) if key=='V' else available[(available.index(voice)+1)%len(available)]
                    preferences(voice='' if key=='V' else voice['id'])
                else:
                    chosen_speed=round(reading_speed(speed+(-SPEED_STEP if key=='-' else SPEED_STEP)),1)
                    if chosen_speed==speed:notice=f'Speed limit: {speed:.1f}×';continue
                    speed=chosen_speed;preferences(speed=speed)
                speech.close();speech=Speech(voice,round(DEFAULT_RATE*speed))
                if playing:
                    speech.start(rows[ci]['paragraphs'][pi])
                    if paused:speech.pause()
                notice='Voice / speed updated'+('; current paragraph restarted' if playing else '')
                continue
            if key in {'shiftup','pageup','shiftdown','pagedown'}:
                scroll+=(-page if key in {'shiftup','pageup'} else page);continue
            old=(ci,pi)
            if key=='left':ci=max(0,ci-1);pi=0
            elif key=='right':ci=min(len(rows)-1,ci+1);pi=0
            elif key=='up':pi-=1
            elif key=='down':pi+=1
            elif key in {'shiftleft','home'}:pi=0
            elif key in {'shiftright','end'}:pi=len(rows[ci]['paragraphs'])-1
            pi=max(0,min(len(rows[ci]['paragraphs'])-1,pi))
            if old!=(ci,pi):
                speech.stop();scroll=None;save();notice='Enter reads from this paragraph'
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
    if confirmed is not True:raise PermissionError('Confirm the optional Piper package and two British voice downloads (Alan and Alba, about 130 MB of models)')
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
        subprocess.run([str(python),'-m','piper.download_voices','--data-dir',str(root),*PIPER_MODELS.values()],check=True,timeout=600,stdin=subprocess.DEVNULL)
        for stem in PIPER_MODELS.values():
            if not (root/(stem+'.onnx')).is_file() or not (root/(stem+'.onnx.json')).is_file():raise RuntimeError('British voice download is incomplete: '+stem)
        value={'state':'ready','finished':time.time()}
    except Exception as exc:value={'state':'failed','error':str(exc),'log':str(root/'setup.log'),'finished':time.time()}
    book_reader.write_json(root/'setup.json',value)


def native_worker():
    """Private JSON-line bridge for Bookokrat; owns only its speech processes."""
    import selectors
    available=voices();voice=preferred_voice(available)
    if not voice:
        print(json.dumps({'state':'error','message':'No local narration voice installed; run lk books speech-setup'}),flush=True);return
    speed=reading_speed(preferences().get('speed',1));player=Speech(voice,round(DEFAULT_RATE*speed))
    token=0;chunks=[];part=0;pending=b''
    def emit(state,**fields):
        print(json.dumps(dict(state=state,id=token,voice=voice_label(voice,available),speed=speed,**fields)),flush=True)
    selector=selectors.DefaultSelector();selector.register(sys.stdin,selectors.EVENT_READ)
    emit('ready')
    try:
        while True:
            if player.poll() and chunks:
                part+=1
                if part<len(chunks):player.start(chunks[part])
                else:chunks=[];emit('done')
            if player.error:emit('error',message=player.error);player.error='';chunks=[]
            if not selector.select(.05):continue
            block=os.read(sys.stdin.fileno(),4096)
            if not block:break
            pending+=block
            if len(pending)>MAX_NATIVE_REQUEST_BYTES:raise ValueError('Narration request exceeds limit')
            while b'\n' in pending:
                line,pending=pending.split(b'\n',1)
                try:
                    value=json.loads(line)
                    if not isinstance(value,dict):raise ValueError('Narration request must be an object')
                    action=value.get('action');token=value.get('id',token)
                    if action=='quit':return
                    if action=='speak':
                        text=str(value.get('text',''))
                        if len(text)>MAX_NATIVE_TEXT_CHARS:raise ValueError('Narration paragraph exceeds limit')
                        chunks=[text[i:i+MAX_PASSAGE_CHARS] for i in range(0,len(text),MAX_PASSAGE_CHARS)];part=0
                        if chunks:player.start(chunks[0])
                    elif action=='pause':player.pause()
                    elif action=='stop':player.stop();chunks=[]
                    elif action in {'voice','default','slower','faster'}:
                        playing=player.phase!='stopped';paused=player.paused
                        if action in {'voice','default'}:
                            voice=default_voice(available) if action=='default' else available[(available.index(voice)+1)%len(available)]
                            preferences(voice='' if action=='default' else voice['id'])
                        else:
                            chosen_speed=round(reading_speed(speed+(-SPEED_STEP if action=='slower' else SPEED_STEP)),1)
                            if chosen_speed==speed:
                                emit('paused' if player.paused else player.phase if player.phase!='stopped' else 'ready');continue
                            speed=chosen_speed;preferences(speed=speed)
                        player.close();player=Speech(voice,round(DEFAULT_RATE*speed))
                        if playing and chunks:
                            player.start(chunks[part])
                            if paused:player.pause()
                    else:raise ValueError('Unknown narration action')
                    emit('paused' if player.paused else player.phase if player.phase!='stopped' else 'ready')
                except (OSError,ValueError,KeyError,TypeError) as error:
                    player.stop();chunks=[];emit('error',message=str(error))
    except (OSError,ValueError) as error:emit('error',message=str(error))
    finally:
        selector.close();player.close()


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['--setup-worker']:setup_worker()
    elif sys.argv[1:]==['--native-worker']:native_worker()
