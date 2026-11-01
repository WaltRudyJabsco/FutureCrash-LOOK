"""Browser narration preparation. No speaker playback; cached bounded passages."""
from pathlib import Path
import hashlib
from functools import lru_cache
import json
import subprocess
import tempfile
import threading
import time
import zipfile
import book_speech

_LOCK = threading.Lock()
MAX_IMAGE_BYTES=8*1024*1024


def chapter_content(rows,chapter):
    row=rows[chapter]
    return {'paragraphs':row['paragraphs'],
            'images':[{'before':image['before'],'alt':image['alt'],'index':index}
                      for index,image in enumerate(row.get('images',[]))]}


def image(path,rows,chapter,index):
    if not 0<=chapter<len(rows) or not 0<=index<len(rows[chapter].get('images',[])):
        raise ValueError('Choose an illustration from this chapter')
    name=rows[chapter]['images'][index]['source']
    with zipfile.ZipFile(path) as archive:
        info=archive.getinfo(name)
        if info.file_size>MAX_IMAGE_BYTES:raise ValueError('Book illustration exceeds 8 MiB')
        data=archive.read(info)
    # Only inert raster bytes leave the owner. Never serve EPUB HTML or SVG.
    if data.startswith(b'\x89PNG\r\n\x1a\n'):mime='image/png'
    elif data.startswith(b'\xff\xd8\xff'):mime='image/jpeg'
    elif data.startswith((b'GIF87a',b'GIF89a')):mime='image/gif'
    elif data.startswith(b'RIFF') and data[8:12]==b'WEBP':mime='image/webp'
    else:raise ValueError('Unsupported book illustration format')
    return data,mime


@lru_cache(maxsize=4)
def _document(path,stamp):
    return book_speech.chapters(path)


def document(path):
    path=Path(path)
    return _document(str(path),path.stat().st_mtime_ns)


def passage(rows,chapter,paragraph):
    if not 0<=chapter<len(rows) or not 0<=paragraph<len(rows[chapter]['paragraphs']):
        raise ValueError('Choose a chapter and paragraph from this book')
    return rows[chapter]['paragraphs'][paragraph]


@lru_cache(maxsize=1)
def _voices(minute):
    return book_speech.voices()


def voice_options():
    rows=_voices(int(time.monotonic()//60))
    return {'voices':rows,'default':book_speech.preferred_voice(rows),'automatic':book_speech.default_voice(rows)}


def render(text,ident,chapter,paragraph,voice_id=''):
    rows=_voices(int(time.monotonic()//60))
    voice=next((row for row in rows if row['id']==voice_id),None) if voice_id else book_speech.preferred_voice(rows)
    if voice_id and not voice:raise ValueError('This voice is not installed on the book owner; choose an available voice')
    if not voice:raise ValueError('No narration voice installed on book owner; run lk books speech-setup there')
    ffmpeg=book_speech.book_reader.binary('ffmpeg')
    if not ffmpeg:raise ValueError('Browser narration needs ffmpeg on the book owner')
    key=hashlib.sha256(json.dumps([ident,chapter,paragraph,text,voice['id'],'aac-96-v1']).encode()).hexdigest()
    root=Path.home()/'.cache/look/book-audio';root.mkdir(parents=True,exist_ok=True)
    out=root/(key+'.m4a')
    if out.is_file():return out
    # Bound CPU work; simultaneous tabs requesting a passage share its result.
    if not _LOCK.acquire(timeout=1):raise ValueError('Narration is preparing another passage; try again shortly')
    try:
        if out.is_file():return out
        with tempfile.TemporaryDirectory(dir=root) as folder:
            folder=Path(folder);source=folder/'text.txt';source.write_text(text)
            wave=folder/'voice.wav'
            if voice['engine']=='say':args=[book_speech.book_reader.binary('say'),'-v',voice['name'],'-r',str(book_speech.DEFAULT_RATE),'-f',str(source),'-o',str(wave),'--file-format=WAVE','--data-format=LEI16@22050']
            elif voice['engine']=='espeak':args=[book_speech.book_reader.binary('espeak-ng'),'-v','en-gb','-s',str(book_speech.DEFAULT_RATE),'-f',str(source),'-w',str(wave)]
            else:
                base=Path.home()/'.local/share/look/book-speech'
                args=[str(base/'venv/bin/piper'),'-m',str(base/'en_GB-alan-medium.onnx'),'--input-file',str(source),'-f',str(wave)]
            subprocess.run(args,stdin=subprocess.DEVNULL,capture_output=True,timeout=120,check=True)
            target=folder/'audio.m4a'
            subprocess.run([ffmpeg,'-nostdin','-v','error','-i',str(wave),'-c:a','aac','-b:a','96k','-movflags','+faststart',str(target)],stdin=subprocess.DEVNULL,capture_output=True,timeout=30,check=True)
            target.replace(out)
        # A cache, not a permanent second audiobook library.
        files=sorted(root.glob('*.m4a'),key=lambda p:p.stat().st_mtime,reverse=True)
        for old in files[128:]:old.unlink(missing_ok=True)
        return out
    finally:_LOCK.release()
