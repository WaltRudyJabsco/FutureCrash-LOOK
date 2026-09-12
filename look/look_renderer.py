#!/usr/bin/env python3
"""LOOK — responsive terminal filesystem renderer.

Install manually:
    mkdir -p ~/.local/bin
    cp look.py ~/.local/bin/look.py
    chmod +x ~/.local/bin/look.py

Normally installed by the repository's ./install.sh.
"""
from __future__ import annotations
import json

import argparse
import os
import shutil
import stat
import select
import subprocess
import sys
import termios
import tty
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

RESET='\x1b[0m'; BOLD='\x1b[1m'; DIM='\x1b[2m'; ITALIC='\x1b[3m'; REVERSE='\x1b[7m'

# LOOK 3 presentation layer. The behavioral core stays deliberately boring;
# presentation scales up only when the terminal advertises truecolor.
_CLASSIC=os.environ.get('LOOK_CLASSIC','').lower() in {'1','true','yes','on'}
_TRUECOLOR=(not _CLASSIC and (
    os.environ.get('COLORTERM','').lower() in {'truecolor','24bit'}
    or os.environ.get('TERM_PROGRAM') in {'iTerm.app','Apple_Terminal','WezTerm','ghostty'}
))

def _rgb(r:int,g:int,b:int)->str:
    return f'\x1b[38;2;{r};{g};{b}m'

def _bg(r:int,g:int,b:int)->str:
    return f'\x1b[48;2;{r};{g};{b}m'

if _TRUECOLOR:
    # Quiet, cool palette: brighter state, softer metadata, no rainbow.
    BLUE=_rgb(113,170,255)
    CYAN=_rgb(103,214,238)
    GREEN=_rgb(139,214,145)
    YELLOW=_rgb(238,200,109)
    MAGENTA=_rgb(196,144,236)
    RED=_rgb(239,125,135)
    WHITE=_rgb(224,229,236)
    GRAY=_rgb(128,139,154)
    FAINT=_rgb(89,99,113)
    ACTIVE=_bg(72,188,214)+_rgb(8,18,24)+BOLD
else:
    BLUE='\x1b[38;5;75m'; CYAN='\x1b[38;5;81m'; GREEN='\x1b[38;5;114m'
    YELLOW='\x1b[38;5;221m'; MAGENTA='\x1b[38;5;176m'; RED='\x1b[38;5;203m'
    WHITE='\x1b[38;5;252m'; GRAY='\x1b[38;5;244m'; FAINT=DIM
    ACTIVE=REVERSE+BOLD

CLEAR='\x1b[2J\x1b[H'; HIDE='\x1b[?25l'; SHOW='\x1b[?25h'

@dataclass
class Entry:
    path: Path
    name: str
    is_dir: bool
    is_link: bool
    size: int
    mtime: float
    mode: int

    @property
    def executable(self) -> bool:
        return bool(self.mode & stat.S_IXUSR) and not self.is_dir


def human_size(n:int)->str:
    units=['B','K','M','G','T']
    v=float(n)
    for unit in units:
        if v < 1024 or unit == units[-1]:
            return f'{int(v)}{unit}' if unit=='B' or v>=10 else f'{v:.1f}{unit}'
        v/=1024
    return f'{n}B'


def age_text(ts:float)->str:
    dt=datetime.fromtimestamp(ts); now=datetime.now(); delta=now-dt
    if delta < timedelta(days=1) and dt.date()==now.date():
        return dt.strftime('%H:%M')
    if delta < timedelta(days=7):
        return dt.strftime('%a %H:%M')
    if dt.year==now.year:
        return dt.strftime('%b %d')
    return dt.strftime('%Y-%m-%d')


def read_entries(target:Path, hidden:bool=True, quiet:bool=False)->list[Entry]:
    out=[]
    try:
        items=list(target.iterdir())
    except OSError as e:
        if quiet:
            return []
        print(f'look: {e}', file=sys.stderr); raise SystemExit(1)
    for p in items:
        if not hidden and p.name.startswith('.'):
            continue
        try:
            s=p.lstat()
        except OSError:
            continue
        out.append(Entry(p,p.name,p.is_dir(),p.is_symlink(),s.st_size,s.st_mtime,s.st_mode))
    return out


def color_for(e:Entry)->str:
    if e.is_dir: return BLUE+BOLD
    if e.is_link: return CYAN
    if e.executable: return GREEN+BOLD
    ext=e.path.suffix.lower()
    if ext in {'.py','.js','.ts','.jsx','.tsx','.sh','.zsh','.rb','.go','.rs','.c','.cpp','.h'}: return GREEN
    if ext in {'.md','.txt','.rtf','.pdf','.doc','.docx'}: return WHITE
    if ext in {'.jpg','.jpeg','.png','.gif','.webp','.svg','.heic'}: return MAGENTA
    if ext in {'.mp3','.wav','.flac','.m4a','.aiff','.mp4','.mov','.mkv'}: return YELLOW
    if ext in {'.zip','.gz','.tar','.7z','.dmg','.pkg'}: return RED
    return WHITE


def marker(e:Entry)->str:
    # Deliberately use normal Unicode, never private-use Nerd Font codepoints.
    if e.is_dir: return '◆'
    if e.is_link: return '↗'
    if e.executable: return '▸'
    return '·'


def strip_ansi(s:str)->str:
    import re
    return re.sub(r'\x1b\[[0-9;?]*[ -/]*[@-~]', '', s)


def fit(s:str,width:int)->str:
    raw=strip_ansi(s)
    if len(raw)<=width: return s
    keep=max(1,width-1)
    # Most content lines have color only at the beginning and RESET at the end.
    if s.startswith('\x1b['):
        # crude but safe: preserve prefix through final m
        end=s.find('m')+1
        prefix=s[:end]; body=strip_ansi(s)
        return prefix+body[:keep]+'…'+RESET
    return raw[:keep]+'…'


def column_grid(entries:list[Entry], width:int, highlight_path:Path|None=None, marked:set[Path]|None=None)->list[str]:
    if not entries: return []
    labels=[]
    for e in entries:
        suffix='/' if e.is_dir else ''
        labels.append((e, f'{GREEN}✓{RESET} {marker(e)} {e.name}{suffix}' if marked and e.path.resolve() in marked else f'  {marker(e)} {e.name}{suffix}'))
    maxw=min(max(len(t) for _,t in labels)+3, 38)
    cols=max(1,width//maxw)
    cellw=max(1,width//cols)
    rows=[]
    for start in range(0,len(labels),cols):
        pieces=[]
        for e,text in labels[start:start+cols]:
            plain=text
            if len(plain)>cellw-2:
                plain=plain[:max(1,cellw-3)]+'…'
            padding=' ' * max(1,cellw-len(plain))
            style=ACTIVE if highlight_path is not None and e.path==highlight_path else color_for(e)
            pieces.append(style+plain+RESET+padding)
        rows.append(''.join(pieces).rstrip())
    return rows


def detail_rows(entries:list[Entry], width:int, highlight_path:Path|None=None, marked:set[Path]|None=None)->list[str]:
    rows=[]
    for e in entries:
        suffix='/' if e.is_dir else ''
        left=(f'{GREEN}✓{RESET} {marker(e)} {e.name}{suffix}' if marked and e.path.resolve() in marked else f'  {marker(e)} {e.name}{suffix}')
        size='—' if e.is_dir else human_size(e.size)
        when=age_text(e.mtime)
        right=f'{size:>7}  {when:>10}'
        avail=max(10,width-len(right)-3)
        if len(left)>avail: left=left[:max(1,avail-1)]+'…'
        style=ACTIVE if highlight_path is not None and e.path==highlight_path else color_for(e)
        rows.append(f'{style}{left:<{avail}}{RESET} {GRAY}{right}{RESET}')
    return rows


def query_matches(name:str, query:str)->bool:
    """AND-match whitespace-separated terms anywhere in a name."""
    terms=query.casefold().split()
    folded=name.casefold()
    return all(term in folded for term in terms)


def tree_rows(target:Path, depth:int, width:int, hidden:bool, query:str='', highlight_path:Path|None=None, marked:set[Path]|None=None)->list[str]:
    rows=[]

    def collect(path:Path,prefix:str,level:int)->tuple[list[str], bool]:
        # Protected macOS folders are normal. Tree views silently skip anything
        # the current user cannot inspect instead of flooding stderr.
        kids=sorted(read_entries(path,hidden,quiet=True),key=lambda e:(not e.is_dir,e.name.lower()))
        rendered=[]
        any_match=False
        for i,e in enumerate(kids):
            child_prefix=prefix+('   ' if i==len(kids)-1 else '│  ')
            descendants=[]
            descendant_match=False
            if e.is_dir and level<depth:
                descendants,descendant_match=collect(e.path,child_prefix,level+1)

            self_match=not query or query_matches(e.name,query)
            include=self_match or descendant_match
            if not include:
                continue

            branch='└─' if i==len(kids)-1 else '├─'
            mark=(f'{GREEN}✓{RESET} ' if marked and e.path.resolve() in marked else '  ')
            line=f'{prefix}{branch} {mark}{marker(e)} {e.name}{"/" if e.is_dir else ""}'
            style=ACTIVE if highlight_path is not None and e.path==highlight_path else color_for(e)
            rendered.append(style+fit(line,width)+RESET)
            rendered.extend(descendants)
            any_match=True
        return rendered,any_match

    rows,_=collect(target,'',1)
    return rows


def build_view(target:Path, mode:str, hidden:bool, width:int, tree_depth:int, query:str='', highlight_path:Path|None=None, marked:set[Path]|None=None)->list[str]:
    entries=read_entries(target,hidden)
    if query:
        entries=[e for e in entries if query_matches(e.name,query)]
    dirs=sorted((e for e in entries if e.is_dir),key=lambda e:e.name.lower())
    files=sorted((e for e in entries if not e.is_dir),key=lambda e:e.name.lower())

    # A filtered tree searches recursively. Its header should count the same
    # actual matches the user can select, not only matching top-level entries.
    if mode=='tree' and query:
        tree_matches=matching_paths(target,'tree',hidden,query,tree_depth)
        tree_dir_count=sum(1 for path in tree_matches if path.is_dir())
        tree_file_count=len(tree_matches)-tree_dir_count
    else:
        tree_dir_count=len(dirs)
        tree_file_count=len(files)
    if mode=='dirs': entries=dirs
    elif mode=='files': entries=files
    elif mode=='recent': entries=sorted(entries,key=lambda e:e.mtime,reverse=True)
    elif mode=='size': entries=sorted(entries,key=lambda e:(e.is_dir,-e.size,e.name.lower()))
    else: entries=dirs+files

    try: display=str(target.resolve().relative_to(Path.home()))
    except ValueError: display=str(target.resolve())
    if not display.startswith('/'): display='~/'+display if display!='.' else '~'
    mode_label='' if mode=='smart' else f' · {mode}'
    header=(f'{BOLD}{CYAN}LOOK{RESET}  {WHITE}{display}{RESET}'
            f'  {FAINT}{tree_dir_count} dirs · {tree_file_count} files{mode_label}{RESET}')
    rule=FAINT+('─'*min(width, max(24,len(strip_ansi(header)))))+RESET
    rows=[header,rule]
    if mode=='tree':
        rows+=tree_rows(target,tree_depth,width,hidden,query,highlight_path,marked)
    elif mode in {'detail','recent','size'}:
        rows+=detail_rows(entries,width,highlight_path,marked)
    else:
        # Smart mode: small sets get labeled sections; larger sets become one compact grouped grid.
        if mode=='smart' and len(entries)<=18:
            if dirs:
                rows += [f'{FAINT}{BOLD}FOLDERS{RESET}'] + column_grid(dirs,width,highlight_path,marked)
            if dirs and files: rows.append('')
            if files:
                rows += [f'{FAINT}{BOLD}FILES{RESET}'] + column_grid(files,width,highlight_path,marked)
        else:
            rows += column_grid(entries,width,highlight_path,marked)
    if len(rows)==2: rows.append(FAINT+'· empty'+RESET)
    return rows


def read_key(timeout:float|None=None)->str:
    fd=sys.stdin.fileno(); old=termios.tcgetattr(fd)
    try:
        # cbreak gives us immediate keystrokes without changing terminal output
        # processing. A short readiness check distinguishes bare Esc from an
        # arrow/PageUp/PageDown escape sequence.
        tty.setcbreak(fd)
        if timeout is not None:
            ready,_,_=select.select([fd],[],[],timeout)
            if not ready:
                return ''
        ch=os.read(fd,1)
        if ch==b'\x1b':
            seq=bytearray(ch)
            while len(seq)<6:
                ready,_,_=select.select([fd],[],[],0.025)
                if not ready:
                    break
                seq.extend(os.read(fd,1))
                if seq[-1:] in b'~ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz':
                    break
            return bytes(seq).decode('latin1')
        return ch.decode('utf-8','ignore')
    finally:
        termios.tcsetattr(fd,termios.TCSADRAIN,old)


def matching_paths(target:Path, mode:str, hidden:bool, query:str='', tree_depth:int=2)->list[Path]:

    if mode=='tree':
        matches=[]
        def walk(path:Path,level:int)->None:
            entries=sorted(read_entries(path,hidden,quiet=True),key=lambda e:(not e.is_dir,e.name.lower()))
            for e in entries:
                if not query or query_matches(e.name,query):
                    matches.append(e.path)
                if e.is_dir and level<tree_depth:
                    walk(e.path,level+1)
        walk(target,1)
        return matches

    entries=read_entries(target,hidden)
    if query:
        entries=[e for e in entries if query_matches(e.name,query)]
    dirs=sorted((e for e in entries if e.is_dir),key=lambda e:e.name.lower())
    files=sorted((e for e in entries if not e.is_dir),key=lambda e:e.name.lower())
    if mode=='dirs': entries=dirs
    elif mode=='files': entries=files
    elif mode=='recent': entries=sorted(entries,key=lambda e:e.mtime,reverse=True)
    elif mode=='size': entries=sorted(entries,key=lambda e:(e.is_dir,-e.size,e.name.lower()))
    else: entries=dirs+files
    return [e.path for e in entries]



def _chafa_render(path:Path, width:int, height:int)->list[str]:
    """Optional terminal-native image preview. LOOK remains fully functional without chafa."""
    chafa=shutil.which("chafa")
    if not chafa or height<4 or width<20:
        return []
    try:
        proc=subprocess.run(
            [chafa,"--format=symbols","--size",f"{max(8,width)}x{max(2,height)}",str(path)],
            capture_output=True,text=True,timeout=3
        )
        if proc.returncode==0 and proc.stdout.strip():
            return proc.stdout.rstrip("\n").splitlines()[:height]
    except (OSError,subprocess.SubprocessError):
        pass
    return []


def _pdf_image_preview(path:Path, width:int, height:int)->list[str]:
    """Render PDF page 1 through an available local rasterizer, then chafa."""
    if not shutil.which("chafa"):
        return []
    with tempfile.TemporaryDirectory(prefix="look-pdf-") as td:
        temp=Path(td)
        image=None
        pdftoppm=shutil.which("pdftoppm")
        if pdftoppm:
            out=temp/"page"
            try:
                proc=subprocess.run(
                    [pdftoppm,"-f","1","-singlefile","-png","-r","110",str(path),str(out)],
                    capture_output=True,text=True,timeout=5
                )
                candidate=temp/"page.png"
                if proc.returncode==0 and candidate.exists():
                    image=candidate
            except (OSError,subprocess.SubprocessError):
                pass
        elif sys.platform=="darwin" and shutil.which("qlmanage"):
            try:
                proc=subprocess.run(
                    ["qlmanage","-t","-s","800","-o",str(temp),str(path)],
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5
                )
                candidates=list(temp.glob("*.png"))
                if proc.returncode==0 and candidates:
                    image=candidates[0]
            except (OSError,subprocess.SubprocessError):
                pass
        return _chafa_render(image,width,height) if image else []


def preview_rows(path:Path, width:int, height:int)->list[str]:
    """Small, dependency-light preview for selection mode."""
    width=max(20,width)
    height=max(3,height)
    title=f'{BOLD}{CYAN}{path.name}{RESET}'
    rows=[fit(title,width)]

    try:
        st=path.stat()
    except OSError as exc:
        return rows+[fit(f'{DIM}{exc}{RESET}',width)]

    if path.is_dir():
        rows.append(f'{DIM}folder{RESET}')
        try:
            kids=sorted(path.iterdir(), key=lambda q:(not q.is_dir(),q.name.casefold()))
            for child in kids[:max(1,height-2)]:
                mark='◆' if child.is_dir() else '·'
                rows.append(fit(f'{mark} {child.name}{"/" if child.is_dir() else ""}',width))
            if len(kids)>height-2:
                rows.append(f'{DIM}… {len(kids)-(height-2)} more{RESET}')
        except OSError as exc:
            rows.append(f'{DIM}{exc}{RESET}')
        return rows[:height]

    suffix=path.suffix.casefold()
    image_suffixes={'.png','.jpg','.jpeg','.gif','.webp','.bmp','.tif','.tiff','.heic'}
    if suffix in image_suffixes:
        art=_chafa_render(path,max(20,width),max(2,height-2))
        if art:
            rows.append(f'{DIM}{human_size(st.st_size)} · image preview{RESET}')
            rows.extend(art)
            return rows[:height]

    if suffix=='.pdf':
        art=_pdf_image_preview(path,max(20,width),max(2,height-2))
        if art:
            rows.append(f'{DIM}{human_size(st.st_size)} · PDF · page 1{RESET}')
            rows.extend(art)
            return rows[:height]

    # Prefer actual text when the file looks textual. Avoid dumping binary bytes.
    try:
        sample=path.read_bytes()[:65536]
    except OSError as exc:
        return rows+[fit(f'{DIM}{exc}{RESET}',width)]

    textual=(b'\x00' not in sample)
    if textual:
        try:
            text=sample.decode('utf-8')
        except UnicodeDecodeError:
            try: text=sample.decode('latin1')
            except Exception: text=''
        if text:
            rows.append(f'{DIM}{human_size(st.st_size)} · text{RESET}')
            for line in text.expandtabs(4).splitlines():
                rows.append(fit(line,width))
                if len(rows)>=height: break
            return rows[:height]

    # For PDFs/images/other binaries, show useful type metadata without requiring
    # a terminal-specific image protocol. pdftotext is used opportunistically.
    if suffix=='.pdf' and shutil.which('pdftotext'):
        try:
            proc=subprocess.run(['pdftotext','-f','1','-l','1',str(path),'-'],
                                capture_output=True,text=True,timeout=2)
            text=proc.stdout.strip()
            if text:
                rows.append(f'{DIM}{human_size(st.st_size)} · PDF · page 1 text{RESET}')
                for line in text.splitlines():
                    rows.append(fit(line,width))
                    if len(rows)>=height: break
                return rows[:height]
        except (OSError,subprocess.SubprocessError):
            pass

    kind=suffix[1:].upper() if suffix else 'binary file'
    if shutil.which('file'):
        try:
            proc=subprocess.run(['file','-b',str(path)],capture_output=True,text=True,timeout=1)
            if proc.stdout.strip(): kind=proc.stdout.strip()
        except (OSError,subprocess.SubprocessError):
            pass
    rows.append(f'{DIM}{human_size(st.st_size)}{RESET}')
    for line in kind.splitlines(): rows.append(fit(line,width))
    return rows[:height]

def open_default(path:Path)->tuple[bool,str]:
    """Ask the OS to open a file, returning a short user-facing failure."""
    try:
        if sys.platform=='darwin':
            proc=subprocess.run(['open',str(path)],capture_output=True,text=True)
            if proc.returncode:
                ext=path.suffix or 'this file type'
                return False, f'no application is registered to open {ext}'
        elif os.name=='nt':
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            proc=subprocess.run(['xdg-open',str(path)],capture_output=True,text=True)
            if proc.returncode:
                return False, f'no application could open {path.suffix or "this file type"}'
        return True,''
    except (OSError,FileNotFoundError):
        return False,'system opener unavailable'


def edit_path(path:Path)->None:
    editor=os.environ.get('EDITOR') or ('nvim' if shutil.which('nvim') else 'vi')
    if Path(editor).name=='nvim':
        flag=Path.home()/'.local/share/look/nvim_intro'
        if not flag.exists():
            print("\nLOOK is opening Neovim.\nTo leave: Esc  :q  Enter\nYou'll only be told this once.\n")
            try:
                flag.parent.mkdir(parents=True,exist_ok=True)
                flag.touch()
            except OSError:
                pass
    try: subprocess.call([editor,str(path)])
    except OSError as e: print(f'look: cannot edit {path}: {e}',file=sys.stderr)


def open_with(path:Path)->tuple[bool,str]:
    """Choose an application for a file without changing the system default."""
    if path.is_dir():
        return False,'folders are browsed with Enter'
    if not shutil.which('fzf'):
        return False,'open-with requires fzf'
    try:
        if sys.platform=='darwin':
            roots=[Path('/Applications'),Path('/System/Applications'),Path.home()/'Applications']
            apps=[]
            seen=set()
            for root in roots:
                if not root.is_dir():
                    continue
                for app in sorted(root.glob('*.app')):
                    name=app.stem
                    if name.casefold() in seen:
                        continue
                    seen.add(name.casefold()); apps.append((name,app))
            if not apps:
                return False,'no applications found'
            proc=subprocess.run(
                ['fzf','--prompt','open with › ','--height','40%','--reverse','--border'],
                input='\n'.join(name for name,_ in apps),text=True,capture_output=True)
            choice=proc.stdout.strip()
            if proc.returncode or not choice:
                return False,'open-with cancelled'
            app_path=next((app for name,app in apps if name==choice),None)
            if not app_path:
                return False,'application not found'
            launch=subprocess.run(['open','-a',str(app_path),str(path)],capture_output=True,text=True)
            return (True,'') if launch.returncode==0 else (False,f'could not open with {choice}')

        # Linux: use desktop MIME handlers when gio is available.
        if shutil.which('xdg-mime') and shutil.which('gio'):
            mime=subprocess.run(['xdg-mime','query','filetype',str(path)],capture_output=True,text=True).stdout.strip()
            if not mime:
                return False,'file type is unknown'
            roots=[Path.home()/'.local/share/applications',Path('/usr/local/share/applications'),Path('/usr/share/applications')]
            handlers=[]
            seen=set()
            for root in roots:
                if not root.is_dir():
                    continue
                for desktop in root.glob('*.desktop'):
                    try:
                        text=desktop.read_text(errors='ignore')
                    except OSError:
                        continue
                    if f'{mime};' not in text and f'MimeType={mime}' not in text:
                        continue
                    name=desktop.stem
                    for line in text.splitlines():
                        if line.startswith('Name='):
                            name=line[5:].strip() or name; break
                    key=(name.casefold(),str(desktop))
                    if key in seen:
                        continue
                    seen.add(key); handlers.append((name,desktop))
            if not handlers:
                return False,'no alternate application found for this file type'
            proc=subprocess.run(
                ['fzf','--prompt','open with › ','--height','40%','--reverse','--border'],
                input='\n'.join(name for name,_ in handlers),text=True,capture_output=True)
            choice=proc.stdout.strip()
            if proc.returncode or not choice:
                return False,'open-with cancelled'
            desktop=next((d for name,d in handlers if name==choice),None)
            if not desktop:
                return False,'application not found'
            launch=subprocess.run(['gio','launch',str(desktop),str(path)],capture_output=True,text=True)
            return (True,'') if launch.returncode==0 else (False,f'could not open with {choice}')
        return False,'open-with is unavailable on this system'
    except (OSError,subprocess.SubprocessError):
        return False,'open-with failed'


def copy_text(value:str)->bool:
    try:
        if sys.platform=='darwin' and shutil.which('pbcopy'):
            subprocess.run(['pbcopy'],input=value,text=True,check=True); return True
        if shutil.which('wl-copy'):
            subprocess.run(['wl-copy'],input=value,text=True,check=True); return True
        if shutil.which('xclip'):
            subprocess.run(['xclip','-selection','clipboard'],input=value,text=True,check=True); return True
    except (OSError,subprocess.SubprocessError):
        pass
    return False

def copy_path(path:Path)->bool:
    value=str(path.resolve())
    try:
        if sys.platform=='darwin': subprocess.run(['pbcopy'],input=value,text=True,check=True)
        elif shutil.which('wl-copy'): subprocess.run(['wl-copy'],input=value,text=True,check=True)
        elif shutil.which('xclip'): subprocess.run(['xclip','-selection','clipboard'],input=value,text=True,check=True)
        else: return False
        return True
    except (OSError,subprocess.CalledProcessError): return False


def _complete_path_text(value:str)->str:
    """Shell-like, deterministic path completion for LOOK action prompts."""
    if not value:
        value="./"
    expanded=os.path.expanduser(value)
    p=Path(expanded)
    parent=p.parent if str(p.parent) else Path(".")
    prefix=p.name
    try:
        names=sorted(
            (x.name + ("/" if x.is_dir() else "") for x in parent.iterdir()),
            key=str.casefold
        )
    except OSError:
        return value

    matches=[n for n in names if n.casefold().startswith(prefix.casefold())]
    if not matches:
        return value

    # Extend to a unique/common prefix. A unique directory keeps its trailing slash.
    if len(matches)==1:
        completed=matches[0]
    else:
        common=os.path.commonprefix(matches)
        if len(common)<=len(prefix):
            return value
        completed=common

    # Preserve the user's spelling style (~, absolute, relative).
    raw_parent=str(Path(value).parent)
    if value.startswith("~"):
        base=value[:value.rfind(prefix)] if prefix else value
        return base+completed
    if raw_parent in {"",".","./"}:
        base="./" if value.startswith("./") else ""
        return base+completed
    sep="" if value[:value.rfind(prefix)].endswith(os.sep) else os.sep
    base=value[:value.rfind(prefix)] if prefix else value
    return base+completed


def prompt_line(prompt:str)->tuple[str,bool]:
    """Tiny line editor for LOOK action prompts. Esc cancels immediately."""
    fd=sys.stdin.fileno()
    old=termios.tcgetattr(fd)
    chars:list[str]=[]
    try:
        tty.setcbreak(fd)
        sys.stdout.write(prompt)
        sys.stdout.flush()
        while True:
            ch=os.read(fd,1)
            if ch==b'\x1b':
                sys.stdout.write('\n')
                sys.stdout.flush()
                return '',True
            if ch in {b'\r',b'\n'}:
                sys.stdout.write('\n')
                sys.stdout.flush()
                return ''.join(chars),False
            if ch in {b'\x7f',b'\b'}:
                if chars:
                    chars.pop()
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
                continue
            if ch==b'\t':
                before=''.join(chars)
                after=_complete_path_text(before)
                if after!=before:
                    # Redraw only the editable field after the prompt.
                    sys.stdout.write('\r\x1b[2K'+prompt+after)
                    sys.stdout.flush()
                    chars=list(after)
                else:
                    sys.stdout.write('\a'); sys.stdout.flush()
                continue
            if ch==b'\x03':
                raise KeyboardInterrupt
            text=ch.decode('utf-8','ignore')
            if text and text.isprintable():
                chars.append(text)
                sys.stdout.write(text)
                sys.stdout.flush()
    finally:
        termios.tcsetattr(fd,termios.TCSADRAIN,old)


def _mac_write_file_urls(paths:list[Path])->bool:
    """Publish real NSURL file objects on the macOS general pasteboard."""
    if not shutil.which('osascript'):
        return False
    resolved=[str(p.resolve()) for p in paths]
    script=f"""
ObjC.import('AppKit');
ObjC.import('Foundation');
const paths = {json.dumps(resolved)};
const pb = $.NSPasteboard.generalPasteboard;
pb.clearContents;
const urls = paths.map(p => $.NSURL.fileURLWithPath(p).js);
if (!pb.writeObjects(urls)) throw new Error('NSPasteboard writeObjects failed');
if ((pb.pasteboardItems.count * 1) < 1) throw new Error('clipboard verification failed');
"""
    try:
        subprocess.run(
            ['osascript','-l','JavaScript','-e',script],
            check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL
        )
        return True
    except (OSError,subprocess.SubprocessError):
        return False


def copy_files_to_clipboard(paths:list[Path])->bool:
    """Copy image pixels when useful; otherwise copy native filesystem objects."""
    resolved=[p.resolve() for p in paths]
    try:
        if sys.platform=='darwin':
            # A single common image should paste as image content in chat/mail/editors.
            if len(resolved)==1 and resolved[0].is_file() and shutil.which('osascript'):
                p=resolved[0]
                clipboard_class={
                    '.png':'PNGf',
                    '.jpg':'JPEG',
                    '.jpeg':'JPEG',
                    '.tif':'TIFF',
                    '.tiff':'TIFF',
                }.get(p.suffix.lower())
                if clipboard_class:
                    quoted=json.dumps(str(p))
                    script=(
                        f'set the clipboard to '
                        f'(read (POSIX file {quoted}) as «class {clipboard_class}»)'
                    )
                    subprocess.run(['osascript','-e',script],check=True,
                                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                    return True

            # PDFs, documents, folders, and other arbitrary objects use NSURL
            # pasteboard objects so Finder/Mail-style paste targets can consume them.
            return _mac_write_file_urls(resolved)

        uris='\r\n'.join(p.as_uri() for p in resolved)+'\r\n'
        if shutil.which('wl-copy'):
            subprocess.run(['wl-copy','--type','text/uri-list'],input=uris,text=True,check=True)
            return True
        if shutil.which('xclip'):
            subprocess.run(['xclip','-selection','clipboard','-t','text/uri-list'],
                           input=uris,text=True,check=True)
            return True
    except (OSError,subprocess.SubprocessError):
        pass
    return False


def action_footer(parts:list[str],width:int)->list[str]:
    """Wrap action hints at separators instead of truncating useful verbs."""
    prefix='  '
    lines=[]
    current=prefix
    for part in parts:
        piece=part if current==prefix else ' · '+part
        if len(strip_ansi(current+piece)) > width and current!=prefix:
            lines.append(f'{FAINT}{current}{RESET}')
            current=prefix+part
        else:
            current+=piece
    if current!=prefix:
        lines.append(f'{FAINT}{current}{RESET}')
    return lines


def pager(rows:list[str],height:int,width:int,rebuild=None,candidates=None,on_browse=None,on_back=None,on_parent=None,on_go=None,on_activate=None,force_interactive=False,initial_select:Path|None=None,marked_set:set[Path]|None=None)->None:
    # Interactive state machine: browse -> filter -> select.
    usable=max(3,height-5)
    if (len(rows)<=height-1 and not force_interactive) or not (sys.stdin.isatty() and sys.stdout.isatty()):
        print('\n'.join(rows)); return
    top=0; query=''; filtering=False; selecting=False; selected=0
    current=rows
    matches:list[Path]=[]
    notice=''
    pending=''
    marked:set[Path]=marked_set if marked_set is not None else set()

    if initial_select is not None and candidates:
        matches=candidates('')
        wanted=initial_select.resolve()
        for index,path in enumerate(matches):
            if path.resolve()==wanted:
                selected=index
                filtering=True
                selecting=True
                break

    def refresh_filter()->None:
        nonlocal current,top,matches,selected
        current=rebuild(query,None,None,marked) if rebuild else rows
        matches=candidates(query) if candidates else []
        selected=min(selected,max(0,len(matches)-1))
        top=0

    def selected_path()->Path|None:
        return matches[selected] if matches and 0<=selected<len(matches) else None

    def action_paths()->list[Path]:
        if marked:
            return sorted(marked,key=lambda p:str(p).casefold())
        picked=selected_path()
        return [picked.resolve()] if picked else []

    def selection_status()->str:
        if not marked:
            return ''
        here={p.resolve() for p in (candidates('') if candidates else [])}
        here_count=sum(1 for p in marked if p.resolve() in here)
        if here_count==len(marked):
            return f'{GREEN}{BOLD}SELECTED · {len(marked)}{RESET}'
        return f'{YELLOW}{BOLD}SELECTED · {len(marked)} / {here_count} HERE{RESET}'

    def run_lo_context()->None:
        nonlocal notice
        paths=action_paths()
        if not paths:
            notice='nothing selected'
            return
        lk=Path(__file__).resolve().parent/'lk'
        sys.stdout.write(SHOW+RESET+'\n')
        sys.stdout.flush()
        try:
            subprocess.call([sys.executable,str(lk),'_lo-context',*map(str,paths)])
        except (OSError,KeyboardInterrupt):
            pass
        sys.stdout.write(HIDE)
        sys.stdout.flush()
        notice=f'LO returned · {len(paths)} context path{"s" if len(paths)!=1 else ""}'

    def run_action(kind:str)->None:
        nonlocal notice
        paths=action_paths()
        if not paths:
            notice='nothing selected'
            return
        lk=Path(__file__).resolve().parent/'lk'
        if kind in {'copy','move'}:
            sys.stdout.write(SHOW+RESET+'\n'); sys.stdout.flush()
            try:
                dest,cancelled=prompt_line(
                    f"{kind.upper()} {len(paths)} item{'s' if len(paths)!=1 else ''} · to › "
                )
            except KeyboardInterrupt:
                dest=''; cancelled=True
            sys.stdout.write(HIDE); sys.stdout.flush()
            dest=dest.strip()
            if cancelled or not dest:
                notice='cancelled'; return
            proc=subprocess.run([sys.executable,str(lk),'_batch',kind,dest,*map(str,paths)])
        elif kind=='remove':
            sys.stdout.write(SHOW+RESET+'\n'); sys.stdout.flush()
            try:
                answer,cancelled=prompt_line(
                    f"REMOVE {len(paths)} item{'s' if len(paths)!=1 else ''}? [r confirms · Esc/Enter cancels] › "
                )
            except KeyboardInterrupt:
                answer=''; cancelled=True
            sys.stdout.write(HIDE); sys.stdout.flush()
            if cancelled or answer.strip().lower()!='r':
                notice='cancelled'; return
            proc=subprocess.run([sys.executable,str(lk),'_batch','remove','--',*map(str,paths)])
        marked.clear()
        notice='done · lk undo' if proc.returncode==0 else 'action failed'

    try:
        sys.stdout.write(HIDE)
        while True:
            picked=selected_path()
            if filtering and rebuild:
                # Side previews consume terminal width. Reflow the grid to the
                # visible list pane so highlighted matches cannot live beneath
                # the preview in an off-screen column.
                render_width=max(38,int(width*0.58)) if picked and width>=96 else width
                current=rebuild(query, picked, render_width, marked)
            page=current[top:top+usable]
            sys.stdout.write(CLEAR)
            if (selecting or filtering) and picked:
                if width>=96:
                    left_w=max(38,int(width*0.58))
                    right_w=max(28,width-left_w-3)
                    left=[fit(r,left_w) for r in page]
                    right=preview_rows(picked,right_w,usable)
                    rendered=[]
                    for i in range(max(len(left),len(right))):
                        l=left[i] if i<len(left) else ''
                        r=right[i] if i<len(right) else ''
                        pad=max(0,left_w-len(strip_ansi(l)))
                        rendered.append(l+' '*pad+FAINT+' │ '+RESET+r)
                    sys.stdout.write('\n'.join(rendered[:usable]))
                else:
                    preview_h=max(4,usable//3)
                    list_h=max(3,usable-preview_h-1)
                    rendered=[fit(r,width) for r in page[:list_h]]
                    rendered.append(FAINT+('─'*width)+RESET)
                    rendered.extend(preview_rows(picked,width,preview_h))
                    sys.stdout.write('\n'.join(rendered[:usable]))
            else:
                sys.stdout.write('\n'.join(fit(r,width) for r in page))
            last=min(len(current),top+usable)
            action_parts=[]
            if filtering:
                match_word='match' if len(matches)==1 else 'matches'
                sel=selection_status()
                status=(f'  {CYAN}{BOLD}FILTER{RESET} {WHITE}{query}█{RESET}'
                        f'  {GRAY}{len(matches)} {match_word}{RESET}'
                        + (f'  · {sel}' if sel else ''))
                action_parts=['J/K move','Tab mark','A all','Enter open',
                              'C copy→','B clipboard','M move','R remove',
                              'L LO context','X clear set','E edit','O open with','Y path','G go','Esc clear']
            elif selecting:
                name=picked.name if picked else '(no matches)'
                kind='folder' if picked and picked.is_dir() else 'file'
                sel=selection_status()
                status=(f'  {CYAN}{BOLD}SELECT{RESET} {WHITE}{name}{RESET} {GRAY}· {kind}{RESET}'
                        + (f'  · {sel}' if sel else ''))
                action_parts=['j/k move','Tab mark','Enter open',
                              'C copy→','B clipboard','M move','R remove',
                              'L LO context','X clear set','E edit','O open with','Y path','G go','Esc filter','q quit']
            elif query:
                status=(f'  {CYAN}{BOLD}FILTER{RESET} {WHITE}{query}{RESET}'
                        f'  {GRAY}{last}/{len(current)}{RESET}')
                action_parts=['Enter select','Esc clear','q quit']
            else:
                back_hint='Esc back' if on_back else 'Esc exit'
                status=f'  {FAINT}{last}/{len(current)}{RESET}'
                action_parts=['Enter filter','Space/PgDn next','b/PgUp back',
                              'g/G ends','< parent',back_hint,'q quit']
            if notice:
                status=f'{status}  {YELLOW}{notice}{RESET}'
                notice=''
            footer=action_footer(action_parts,width)
            sys.stdout.write('\n'+fit(status,width)+'\n'+'\n'.join(footer)); sys.stdout.flush()
            if pending:
                key,pending=pending,''
            else:
                key=read_key()

            if filtering:
                if key in {'q','Q','\x03'}: break
                if key in {'\r','\n'}:
                    picked=selected_path()
                    if picked:
                        if on_activate:
                            on_activate(picked); return
                        if picked.is_dir() and on_browse:
                            on_browse(picked); return
                        opened,message=open_default(picked)
                        if opened:
                            break
                        notice=message
                    continue
                elif key in {'\x1b[B','J'} and matches:
                    selected=min(len(matches)-1,selected+1)
                    top=min(max(0,len(current)-usable),top+1)
                elif key in {'\x1b[A','K'} and matches:
                    selected=max(0,selected-1)
                    top=max(0,top-1)
                elif key=='\x1b[6~' and matches:
                    selected=min(len(matches)-1,selected+usable)
                    top=min(max(0,len(current)-usable),top+usable)
                elif key=='\x1b[5~' and matches:
                    selected=max(0,selected-usable)
                    top=max(0,top-usable)
                elif key=='\x1b':
                    query=''; filtering=False; selecting=False; refresh_filter()
                elif key.startswith('\x1b['):
                    # Ignore other terminal escape sequences without leaving filter mode.
                    pass
                elif key=='A' and matches:
                    resolved={path.resolve() for path in matches}
                    if resolved.issubset(marked):
                        marked.difference_update(resolved)
                        notice=f'{len(matches)} unmarked'
                    else:
                        marked.update(resolved)
                        notice=f'{len(matches)} marked'
                    current=rebuild(query,selected_path(),None,marked) if rebuild else current
                elif key=='\t' and matches:
                    picked=selected_path()
                    if picked:
                        rp=picked.resolve()
                        if rp in marked: marked.remove(rp)
                        else: marked.add(rp)
                        current=rebuild(query,picked,None,marked) if rebuild else current
                elif key in {'C','M','R'} and matches:
                    run_action({'C':'copy','M':'move','R':'remove'}[key])
                    refresh_filter()
                elif key=='B' and matches:
                    paths=action_paths()
                    if paths:
                        notice='copied file to clipboard' if copy_files_to_clipboard(paths) else 'file clipboard unavailable'
                elif key=='Y' and matches:
                    paths=action_paths()
                    if paths:
                        value='\n'.join(str(x) for x in paths)
                        notice='copied paths' if copy_text(value) else 'clipboard unavailable'
                elif key=='G' and matches:
                    picked=selected_path()
                    if picked and on_go:
                        on_go(picked if picked.is_dir() else picked.parent); return
                elif key=='L' and matches:
                    run_lo_context()
                    refresh_filter()
                elif key=='X':
                    marked.clear()
                    notice='selection cleared'
                    refresh_filter()
                elif key=='E' and matches:
                    picked=selected_path()
                    if picked and not picked.is_dir():
                        sys.stdout.write(SHOW+RESET+'\n'); sys.stdout.flush(); edit_path(picked); return
                    notice='folders are browsed with Enter'
                elif key=='O' and matches:
                    picked=selected_path()
                    if picked:
                        sys.stdout.write(SHOW+RESET+'\n'); sys.stdout.flush()
                        opened,message=open_with(picked)
                        sys.stdout.write(HIDE); sys.stdout.flush()
                        if not opened and message!='open-with cancelled': notice=message
                elif key=='P' and matches:
                    picked=selected_path()
                    if picked:
                        sys.stdout.write(SHOW+RESET+'\n'+str(picked.resolve())+'\n'); sys.stdout.flush(); return
                elif key in {'\x7f','\b'}:
                    if query: query=query[:-1]; refresh_filter()
                elif key=='\x03': break
                elif len(key)==1 and key.isprintable():
                    # Capture the typing burst before rendering. Input stays ahead of redraws;
                    # rebuild only after a tiny idle gap.
                    query+=key
                    while True:
                        nxt=read_key(0.012)
                        if not nxt:
                            break
                        if nxt in {'\x7f','\b'}:
                            if query: query=query[:-1]
                            continue
                        if len(nxt)==1 and nxt.isprintable():
                            query+=nxt
                            continue
                        # Preserve a non-text key for the next input cycle.
                        pending=nxt
                        break
                    refresh_filter()
                continue

            if selecting:
                if key in {'q','Q','\x03'}: break
                if key=='\x1b': selecting=False; filtering=True; continue
                if key in {'j','J','\x1b[B'} and matches: selected=(selected+1)%len(matches); continue
                if key in {'k','K','\x1b[A'} and matches: selected=(selected-1)%len(matches); continue
                if key=='\x1b[6~' and matches: selected=min(len(matches)-1,selected+usable); continue
                if key=='\x1b[5~' and matches: selected=max(0,selected-usable); continue
                if key.startswith('\x1b['): continue
                picked=selected_path()
                if not picked: continue
                if key in {'\r','\n'}:
                    if on_activate:
                        on_activate(picked); return
                    if picked.is_dir() and on_browse:
                        on_browse(picked); return
                    opened,message=open_default(picked)
                    if opened:
                        break
                    notice=message
                    continue
                if key=='\t':
                    rp=picked.resolve()
                    if rp in marked: marked.remove(rp)
                    else: marked.add(rp)
                    continue
                if key in {'c','C','m','M','r','R'}:
                    run_action({'c':'copy','C':'copy','m':'move','M':'move','r':'remove','R':'remove'}[key])
                    refresh_filter(); continue
                if key=='B':
                    paths=action_paths()
                    notice='copied file to clipboard' if paths and copy_files_to_clipboard(paths) else 'file clipboard unavailable'
                    continue
                if key in {'y','Y'}:
                    paths=action_paths()
                    value='\n'.join(str(x) for x in paths)
                    notice='copied paths' if value and copy_text(value) else 'clipboard unavailable'
                    continue
                if key in {'g','G'} and on_go:
                    on_go(picked if picked.is_dir() else picked.parent); return
                if key=='L':
                    run_lo_context()
                    refresh_filter(); continue
                if key=='X':
                    marked.clear()
                    notice='selection cleared'
                    refresh_filter(); continue
                if key in {'e','E'}:
                    if picked.is_dir(): notice='folders are browsed with Enter'; continue
                    sys.stdout.write(SHOW+RESET+'\n'); sys.stdout.flush(); edit_path(picked); return
                if key in {'o','O'}:
                    sys.stdout.write(SHOW+RESET+'\n'); sys.stdout.flush()
                    opened,message=open_with(picked)
                    sys.stdout.write(HIDE); sys.stdout.flush()
                    if not opened and message!='open-with cancelled': notice=message
                    continue
                if key in {'p','P'}:
                    sys.stdout.write(SHOW+RESET+'\n'+str(picked.resolve())+'\n'); sys.stdout.flush(); return
                continue

            if key in {'q','Q','\x03'}: break
            if key in {'\r','\n','/'}:
                filtering=True
                refresh_filter()
            elif key=='\x1b':
                if query:
                    query=''; selecting=False; refresh_filter()
                elif on_back:
                    on_back()
                    return
                else:
                    break
            elif key in {' ','\x1b[6~'}:
                if last>=len(current): break
                top=min(max(0,len(current)-usable),top+usable)
            elif key in {'b','\x1b[5~'}: top=max(0,top-usable)
            elif key in {'j','\x1b[B'}: top=min(max(0,len(current)-usable),top+1)
            elif key in {'k','\x1b[A'}: top=max(0,top-1)
            elif key=='g': top=0
            elif key=='G': top=max(0,len(current)-usable)
            elif key=='<' and on_parent:
                on_parent()
                return
    finally:
        sys.stdout.write(SHOW+RESET+'\n'); sys.stdout.flush()

def _global_catalog(root:Path)->list[Path]:
    """Fast home-scoped catalog; fd when available, find as portable fallback."""
    root=root.expanduser().resolve()
    out=[]
    if shutil.which("fd"):
        try:
            proc=subprocess.run(
                ["fd","--hidden","--follow","--absolute-path",
                 "--exclude",".git","--exclude","node_modules","--exclude",".Trash",
                 "--exclude","Library/Caches","--exclude",".cache",".",str(root)],
                capture_output=True,text=True,timeout=12
            )
            if proc.returncode==0:
                out=[Path(line) for line in proc.stdout.splitlines() if line.strip()]
        except (OSError,subprocess.SubprocessError):
            out=[]
    if not out:
        try:
            for base,dirs,files in os.walk(root):
                dirs[:]=[d for d in dirs if d not in {".git","node_modules",".Trash",".cache"}]
                b=Path(base)
                out.extend(b/d for d in dirs)
                out.extend(b/f for f in files)
                if len(out)>=20000:
                    break
        except OSError:
            pass
    return out[:20000]

def _catalog_matches(paths:list[Path],query:str)->list[Path]:
    if not query:
        return paths[:]
    return [p for p in paths if query_matches(p.name,query)]

def _catalog_view(paths:list[Path],root:Path,width:int,query:str='',highlight_path:Path|None=None,marked:set[Path]|None=None)->list[str]:
    matches=_catalog_matches(paths,query)
    shown=matches[:800]
    header=(f'{BOLD}{CYAN}LOOK FIND{RESET}  {WHITE}{root}{RESET}'
            f'  {FAINT}{len(matches)} matches{RESET}')
    rows=[header,FAINT+('─'*min(width,max(24,len(strip_ansi(header)))))+RESET]
    for p in shown:
        try:
            rel=p.relative_to(root)
        except ValueError:
            rel=p
        mark=(f'{GREEN}✓{RESET} ' if marked and p.resolve() in marked else '  ')
        if highlight_path is not None and p.resolve()==highlight_path.resolve():
            style=ACTIVE
        elif p.is_dir():
            style=BLUE+BOLD
        else:
            try:
                st=p.lstat()
                style=color_for(Entry(p,p.name,False,p.is_symlink(),st.st_size,st.st_mtime,st.st_mode))
            except OSError:
                style=WHITE
        suffix='/' if p.is_dir() else ''
        rows.append(style+fit(f'{mark}{rel}{suffix}',width)+RESET)
    if not shown:
        rows.append(FAINT+'· no matches'+RESET)
    return rows


def main():
    ap=argparse.ArgumentParser(add_help=False)
    ap.add_argument('path',nargs='?',default='.')
    ap.add_argument('--mode',choices=['smart','detail','dirs','files','tree','recent','size'],default='smart')
    ap.add_argument('--depth',type=int,default=2)
    ap.add_argument('--no-hidden',action='store_true')
    ap.add_argument('--interactive',action='store_true')
    ap.add_argument('--select',default=None,help=argparse.SUPPRESS)
    ap.add_argument('--global-find',action='store_true',help=argparse.SUPPRESS)
    ap.add_argument('--nvim-result',action='store_true',help=argparse.SUPPRESS)
    ap.add_argument('-h','--help',action='help')
    args=ap.parse_args()
    target=Path(os.path.expanduser(args.path))
    hidden=not args.no_hidden

    if args.global_find:
        root=target.expanduser().resolve()
        catalog=_global_catalog(root)
        selected_result:Path|None=None
        def choose_global(path:Path)->None:
            nonlocal selected_result
            selected_result=path
        pager(
            _catalog_view(catalog,root,shutil.get_terminal_size((100,30)).columns),
            shutil.get_terminal_size((100,30)).lines,
            shutil.get_terminal_size((100,30)).columns,
            rebuild=lambda q,h=None,w=None,m=None: _catalog_view(catalog,root,w or 100,q,h,m),
            candidates=lambda q: _catalog_matches(catalog,q),
            on_browse=choose_global,
            on_go=choose_global,
            on_activate=choose_global,
            force_interactive=True,
        )
        if selected_result is not None:
            if args.nvim_result and not selected_result.is_dir():
                editor=shutil.which("nvim")
                if editor:
                    return subprocess.call([editor,"--",str(selected_result)])
            # Re-enter ordinary LOOK at the result's containing directory, selected.
            parent=selected_result if selected_result.is_dir() else selected_result.parent
            return subprocess.call([
                sys.executable,str(Path(__file__).resolve()),str(parent),
                "--mode","smart","--interactive","--select",str(selected_result)
            ])
        return 0

    browsed_once=False
    initial_select=Path(os.path.expanduser(args.select)).resolve() if args.select else None
    history:list[Path]=[]
    working_set:set[Path]=set()
    while True:
        if not target.is_dir():
            print(f'look: not a directory: {target}',file=sys.stderr); return 1
        sz=shutil.get_terminal_size((100,30))
        rows=build_view(target,args.mode,hidden,sz.columns,args.depth)
        browsed:Path|None=None
        went_back=False
        went_parent=False
        go_to:Path|None=None
        def choose_dir(path:Path)->None:
            nonlocal browsed
            browsed=path
        def choose_back()->None:
            nonlocal went_back
            went_back=True
        def choose_parent()->None:
            nonlocal went_parent
            went_parent=True
        def choose_go(path:Path)->None:
            nonlocal go_to
            go_to=path.resolve()
        pager(rows,sz.lines,sz.columns,
              rebuild=lambda q,h=None,w=None,m=None: build_view(target,args.mode,hidden,w or sz.columns,args.depth,q,h,m),
              candidates=lambda q: matching_paths(target,args.mode,hidden,q,args.depth),
              on_browse=choose_dir,
              on_back=choose_back if history else None,
              on_parent=choose_parent if target.resolve()!=target.resolve().parent else None,
              on_go=choose_go,
              force_interactive=(args.interactive or browsed_once),
              initial_select=initial_select if not browsed_once else None,
              marked_set=working_set)
        if go_to is not None:
            request=Path.home()/'.local'/'share'/'look'/'cd_request'
            request.parent.mkdir(parents=True,exist_ok=True)
            request.write_text(str(go_to),encoding='utf-8')
            return 0
        if went_back:
            target=history.pop()
            browsed_once=True
            continue
        if went_parent:
            parent=target.resolve().parent
            if parent!=target.resolve():
                history.append(target)
                target=parent
            browsed_once=True
            continue
        if browsed is None: return 0
        history.append(target)
        target=browsed
        browsed_once=True

if __name__=='__main__': raise SystemExit(main())
