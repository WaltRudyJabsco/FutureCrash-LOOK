"""Shared, bounded media artwork discovery for LOOK surfaces.

Artwork is presentation, never control flow: local embedded/external art is cached and
all failures simply return None. No network access is performed here.
"""
from __future__ import annotations
import hashlib, os, shutil, subprocess
from pathlib import Path

IMAGE_SUFFIXES={'.jpg','.jpeg','.png','.webp'}
AUDIO_SUFFIXES={'.m4a','.mp4a','.mp3','.flac','.ogg','.oga','.opus','.aac','.wav','.aiff','.aif','.alac'}
PREFERRED=('cover.jpg','cover.jpeg','cover.png','folder.jpg','folder.png','front.jpg','front.png','album.jpg','album.png')


def _external(path:Path)->Path|None:
    folder=path.parent if path.is_file() else path
    try: by_name={x.name.casefold():x for x in folder.iterdir() if x.is_file()}
    except OSError: return None
    for name in PREFERRED:
        if name in by_name: return by_name[name]
    for item in by_name.values():
        if item.suffix.casefold() in IMAGE_SUFFIXES and any(k in item.stem.casefold() for k in ('cover','folder','front','album')):
            return item
    return None


def _embedded(path:Path)->Path|None:
    """Extract attached audio cover art once. ffmpeg is optional and tightly bounded."""
    if not path.is_file() or path.suffix.casefold() not in AUDIO_SUFFIXES: return None
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg: return None
    try: stamp=path.stat().st_mtime_ns
    except OSError: return None
    cache=Path.home()/'.cache'/'look'/'media-art'; cache.mkdir(parents=True,exist_ok=True)
    token=hashlib.sha256(f'{path.resolve()}|{stamp}'.encode()).hexdigest()[:28]
    out=cache/f'{token}.jpg'
    if out.exists(): return out
    tmp=cache/f'.{token}.{os.getpid()}.jpg'
    try:
        proc=subprocess.run([ffmpeg,'-nostdin','-loglevel','error','-i',str(path),'-map','0:v:0','-frames:v','1','-q:v','3','-y',str(tmp)],
                            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=2.5)
        if proc.returncode==0 and tmp.exists() and tmp.stat().st_size>0:
            tmp.replace(out); return out
    except (OSError,subprocess.SubprocessError):
        pass
    finally:
        try: tmp.unlink(missing_ok=True)
        except OSError: pass
    return None


def artwork_for(pathlike:str|Path)->Path|None:
    """Embedded art wins; conventional sidecar artwork is the fallback."""
    path=Path(pathlike).expanduser()
    if not path.exists(): return None
    if path.is_file() and path.suffix.casefold() in IMAGE_SUFFIXES: return path
    return _embedded(path) or _external(path)


def symbol_lines(pathlike:str|Path,width:int,height:int)->list[str]:
    art=artwork_for(pathlike); chafa=shutil.which('chafa')
    if not art or not chafa or width<12 or height<3: return []
    try:
        proc=subprocess.run([chafa,'--format=symbols','--size',f'{width}x{height}',str(art)],capture_output=True,text=True,timeout=.4)
        if proc.returncode==0: return proc.stdout.rstrip('\n').splitlines()[:height]
    except (OSError,subprocess.SubprocessError): pass
    return []


def _ascii_via_ffmpeg(art:Path,width:int,height:int)->list[str]:
    """Portable dependency-light ASCII renderer. ffmpeg is already the cover extractor.

    Terminal cells are taller than they are wide, so sample about half the requested
    row count and duplicate nothing; this keeps album covers recognizably square.
    """
    ffmpeg=shutil.which('ffmpeg')
    if not ffmpeg or width<8 or height<2: return []
    sample_h=max(2,height)
    try:
        proc=subprocess.run([ffmpeg,'-nostdin','-loglevel','error','-i',str(art),
                             '-vf',f'scale={width}:{sample_h}:force_original_aspect_ratio=decrease',
                             '-f','rawvideo','-pix_fmt','gray','-'],
                            capture_output=True,timeout=1.0)
        if proc.returncode!=0 or not proc.stdout: return []
        raw=proc.stdout; pixels=len(raw)
        # ffmpeg may preserve a smaller dimension; infer a conservative row width.
        row_w=min(width,max(1,pixels//sample_h))
        rows=max(1,min(sample_h,pixels//row_w))
        ramp=' .:-=+*#%@'
        out=[]
        for y in range(rows):
            chunk=raw[y*row_w:(y+1)*row_w]
            if not chunk: break
            line=''.join(ramp[min(len(ramp)-1,(v*(len(ramp)-1))//255)] for v in chunk)
            out.append(line.ljust(width)[:width])
        return out[:height]
    except (OSError,subprocess.SubprocessError,ValueError):
        return []


def ascii_lines(pathlike:str|Path,width:int,height:int)->list[str]:
    """Portable player artwork: ASCII only, with no Chafa dependency required."""
    art=artwork_for(pathlike)
    if not art or width<10 or height<3: return []
    # Prefer our deterministic renderer. Chafa remains available to Media Find's
    # richer symbol path, but the player should render on every machine with ffmpeg.
    return _ascii_via_ffmpeg(art,width,height)

