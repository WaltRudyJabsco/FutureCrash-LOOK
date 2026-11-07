"""Ten text, image and file slots. Local capture and per-node Fabric publication are opt-in."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import os
from pathlib import Path
import re
import select
import signal
import shutil
import sqlite3
import subprocess
import sys
import termios
import time
import tty

try:
    from . import terminal_style
    from .notebook_markdown import safe_text, cell_width
except ImportError:
    import terminal_style
    from notebook_markdown import safe_text, cell_width

try:
    from . import clipboard_items as items
except ImportError:
    import clipboard_items as items

SLOTS = '1234567890'
SHIFT_SLOTS = '!@#$%^&*()'
HISTORY_LIMIT = 10
TEXT_LIMIT = 256_000
POLL_SECONDS = 1.0
CLIPBOARD_TIMEOUT = 1.0
FAILED_POLLS_LIMIT = 60


def directory():
    return Path.home()/'.local/share/look/clipboard'


class Shelf:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else directory()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root.chmod(0o700)
        self.db = sqlite3.connect(self.root/'history.sqlite3', timeout=2)
        (self.root/'history.sqlite3').chmod(0o600)
        # No WAL: all durable text stays in the private database and its journal.
        self.db.executescript('''
            PRAGMA secure_delete=ON;
            CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS clips (
                id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS clip_stamp (id INTEGER PRIMARY KEY, stamp REAL, published INTEGER);
            CREATE TRIGGER IF NOT EXISTS stamp_clip AFTER INSERT ON clips BEGIN
              INSERT INTO clip_stamp VALUES (NEW.id,(julianday('now')-2440587.5)*86400,
                COALESCE((SELECT value='1' FROM settings WHERE name='auto_share'),0)
                AND NOT EXISTS (SELECT 1 FROM settings WHERE name='recalling' AND value=(SELECT value FROM settings WHERE name='observed')));
            END;
            CREATE TRIGGER IF NOT EXISTS forget_stamp AFTER DELETE ON clips BEGIN
              DELETE FROM clip_stamp WHERE id=OLD.id;
            END;
        ''')

    def close(self):
        self.db.close()

    def setting(self, name, default=''):
        row = self.db.execute('SELECT value FROM settings WHERE name=?', (name,)).fetchone()
        return row[0] if row else default

    def set(self, name, value):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (name, str(value)))

    @property
    def enabled(self):
        return self.setting('enabled') == '1'

    def rows(self):
        return self.db.execute('SELECT id,text FROM clips ORDER BY id DESC LIMIT ?', (HISTORY_LIMIT,)).fetchall()

    def observe(self, text):
        if text is None or len(text) > (items.MAX_ENCODED if text.startswith(items.PREFIX) else TEXT_LIMIT):
            return False
        if text.startswith(items.PREFIX):
            try:items.unpack(text)
            except ValueError:return False
        digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
        with self.db:
            previous = self.setting('observed')
            self.db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', ('observed', digest))
            if not text or digest == previous:
                return False
            newest = self.db.execute('SELECT text FROM clips ORDER BY id DESC LIMIT 1').fetchone()
            if newest and newest[0] == text:
                return False
            self.db.execute('INSERT INTO clips(text) VALUES (?)', (text,))
            self.db.execute('DELETE FROM clips WHERE id NOT IN (SELECT id FROM clips ORDER BY id DESC LIMIT ?)', (HISTORY_LIMIT,))
        return True

    def auto_share(self,on):
        with self.db:
            if not on:self.db.execute('UPDATE clip_stamp SET published=0')
            self.db.execute("INSERT OR REPLACE INTO settings VALUES ('auto_share',?)",('1' if on else '0',))

    def timed_rows(self):
        return self.db.execute('SELECT c.id,c.text,COALESCE(s.stamp,0) FROM clips c LEFT JOIN clip_stamp s ON c.id=s.id ORDER BY c.id DESC LIMIT ?', (HISTORY_LIMIT,)).fetchall()

    def remove(self, identity):
        # Keep the observed digest so deleting the current clipboard does not
        # immediately put it back on the next polling tick.
        with self.db:
            self.db.execute('DELETE FROM clips WHERE id=?', (identity,))

    def clear(self):
        with self.db:
            self.db.execute('DELETE FROM clips')


def backend():
    if sys.platform == 'darwin' and shutil.which('pbpaste') and shutil.which('pbcopy'):
        return ['pbpaste'], ['pbcopy']
    if os.environ.get('WAYLAND_DISPLAY') and shutil.which('wl-paste') and shutil.which('wl-copy'):
        return ['wl-paste', '--no-newline', '--type', 'text'], ['wl-copy', '--type', 'text/plain;charset=utf-8']
    if os.environ.get('DISPLAY') and shutil.which('xclip'):
        return ['xclip', '-selection', 'clipboard', '-o'], ['xclip', '-selection', 'clipboard']
    return None


def read_clipboard():
    commands = backend()
    if commands is None:
        return None
    try:
        result = subprocess.run(commands[0], capture_output=True, timeout=CLIPBOARD_TIMEOUT,
                                check=True, text=True, encoding='utf-8', errors='replace')
        return result.stdout if len(result.stdout) <= TEXT_LIMIT else None
    except (OSError, subprocess.SubprocessError):
        return None


def read_item():
    try:return items.capture(read_clipboard)
    except (OSError,subprocess.SubprocessError):return read_clipboard()


def copy_clipboard(text):
    commands = backend()
    if commands is None:
        return False
    try:
        subprocess.run(commands[1], input=text, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=CLIPBOARD_TIMEOUT, check=True, text=True, encoding='utf-8')
        return True
    except (OSError, subprocess.SubprocessError):
        return False



def wayland_session():
    return sys.platform != 'darwin' and bool(
        os.environ.get('WAYLAND_DISPLAY') or os.environ.get('XDG_SESSION_TYPE') == 'wayland')


def wayland_token():
    keys = ('WAYLAND_DISPLAY', 'XDG_SESSION_ID', 'XDG_RUNTIME_DIR', 'XDG_CURRENT_DESKTOP')
    return hashlib.sha256('|'.join(os.environ.get(key, '') for key in keys).encode()).hexdigest()


def sample_automatic(shelf):
    # A wl-paste read can map a focus-stealing surface on GNOME. Never poll it.
    if not wayland_session() and shelf.enabled:
        try:shelf.observe(read_item())
        except ValueError:pass


def capture_stdin():
    if os.environ.get('CLIPBOARD_STATE', 'data') != 'data':
        return
    if not (directory()/'history.sqlite3').is_file():
        return
    text = sys.stdin.read(TEXT_LIMIT+1)
    if len(text) > TEXT_LIMIT:
        return
    shelf = Shelf()
    try:
        if shelf.enabled:
            shelf.observe(text)
    finally:
        shelf.close()


def watch_wayland(shelf):
    tool = shutil.which('wl-paste')
    if not tool:
        shelf.set('blocked_wayland', wayland_token())
        return
    # --watch requires data-control. Unsupported compositors fail once instead
    # of falling back to wl-paste's temporary focus-stealing window.
    try:
        proc = subprocess.Popen(
            [tool, '--type', 'text', '--watch', sys.executable,
             str(Path(__file__).resolve()), '--capture-stdin'],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        shelf.set('blocked_wayland', wayland_token())
        return
    try:
        while shelf.enabled and proc.poll() is None:
            time.sleep(POLL_SECONDS)  # Check opt-out without reading the clipboard.
        if shelf.enabled:
            shelf.set('blocked_wayland', wayland_token())
    finally:
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait(timeout=2)


def capture_description(shelf):
    if not shelf.enabled:
        return 'off'
    if wayland_session():
        if shelf.setting('blocked_wayland') == wayland_token():
            return 'unavailable on this Wayland desktop · use lk clip add'
        return 'requested · Wayland events'
    return 'on'


def watch():
    shelf = Shelf()
    try:
        with (shelf.root/'watch.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return
            if wayland_session():
                if shelf.enabled and shelf.setting('blocked_wayland')!=wayland_token():watch_wayland(shelf)
                return
            failures = 0
            while shelf.enabled:
                try:text = read_item()
                except ValueError:text = None
                failures = failures+1 if text is None else 0
                if failures >= FAILED_POLLS_LIMIT:
                    return  # A departed desktop session must not leave a busy helper.
                if text is not None and shelf.enabled:
                    shelf.observe(text)
                time.sleep(POLL_SECONDS)
    finally:
        shelf.close()


def ensure_watcher():
    # Ordinary commands do not create clipboard state or read any clipboard
    # until the owner explicitly enables capture.
    if not (directory()/'history.sqlite3').is_file():
        return
    shelf = Shelf()
    try:
        if not shelf.enabled or backend() is None:
            return
        if wayland_session() and shelf.setting('blocked_wayland')==wayland_token():return
        with (shelf.root/'watch.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--watch'],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True, close_fds=True)
    finally:
        shelf.close()


def removal_slot(key):
    if key in SHIFT_SLOTS and len(key) == 1:
        return SHIFT_SLOTS.index(key)
    match = re.fullmatch(r'\x1b\[(\d+);2u', key)
    if match and int(match[1]) in range(ord('0'),ord('9')+1):
        return SLOTS.index(chr(int(match[1])))
    return None


def read_key(fd, timeout=1):
    if not select.select([fd], [], [], timeout)[0]:
        return ''
    value = os.read(fd, 1)
    if not value:
        return 'esc'
    if value != b'\x1b':
        return value.decode('ascii', 'ignore')
    sequence = bytearray(value)
    while len(sequence) < 32 and select.select([fd], [], [], .035)[0]:
        sequence.extend(os.read(fd, 1))
        if sequence[-1:] in b'~ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz':
            break
    if sequence == b'\x1b[200~':
        # A pasted command/number is text, never a clipboard UI action.
        tail = b''
        while select.select([fd], [], [], 2)[0]:
            chunk = os.read(fd, 1)
            if not chunk:
                break
            tail = (tail+chunk)[-6:]
            if tail == b'\x1b[201~':
                break
        return 'paste:'
    value = sequence.decode('ascii', 'ignore')
    enhanced = re.fullmatch(r'\x1b\[(\d+)(?:;(\d+))?u',value)
    if enhanced:
        code = int(enhanced[1]); modifier = int(enhanced[2] or '1')
        if modifier == 2 and ord('0') <= code <= ord('9'):
            return value
        if modifier == 5 and code == ord('c'):
            return '\x03'
        if modifier in {1,2} and code < 128:
            char = chr(code)
            return 'esc' if code == 27 else char.upper() if modifier == 2 else char
    return {b'\x1b': 'esc', b'\x1b[A': 'up', b'\x1b[B': 'down',
            b'\x1b[5~': 'pageup', b'\x1b[6~': 'pagedown'}.get(bytes(sequence), value)


def clip_line(text, width):
    value = safe_text(text).replace('\t', '    ')
    out = ''; used = 0
    for char in value:
        size = cell_width(char)
        if used+size > width:
            return out[:-1]+'…' if out else ''
        out += char
        used += size
    return out


def fit_styled(text, width):
    """Measure only terminal cells; colors must not steal space in split panes."""
    parts = re.split(r'(\033\[[0-9;]*m)', text)
    out = []; used = 0
    for part in parts:
        if part.startswith('\033['):
            out.append(part); continue
        for char in part:
            size = cell_width(char)
            if used+size > width:
                return ''.join(out)+'\033[0m'
            out.append(char); used += size
    return ''.join(out)


def wrap_cells(text, width):
    rows = []
    for line in text.split('\n'):
        row = ''; used = 0
        for char in line:
            size = cell_width(char)
            if row and used+size > width:
                rows.append(row); row = ''; used = 0
            row += char; used += size
        rows.append(row)
    return rows


def command_inks(colors):
    light=terminal_style.luminance(colors.get('_palette',{}).get('background','#111111'))>.3
    blue='\033[38;2;33;92;154m' if light else '\033[38;2;95;175;255m'
    gray='\033[38;2;95;95;95m' if light else '\033[38;2;160;160;160m'
    return blue,gray


def command_rows(bindings,width,colors):
    blue,gray=command_inks(colors)
    rows=[''];used=0
    for key,label in bindings:
        if used and used+2+sum(cell_width(char) for char in key+' '+label)>width:rows.append('');used=0
        if used:rows[-1]+=gray+'  ';used+=2
        for text,style in ((key,blue),(' '+label,gray)):
            rows[-1]+=style
            for char in text:
                size=cell_width(char)
                if used+size>width:rows.append(style);used=0
                if not used and char==' ':continue
                rows[-1]+=char;used+=size
    return [row+'\033[0m' for row in rows]


def share_note(text):
    try:
        from .notebook_core import Notebook
        from .notebook import nudge_sync
    except ImportError:
        from notebook_core import Notebook
        from notebook import nudge_sync
    # A normal note uses existing trusted Notebook replication; history itself
    # is never published or exposed through a remote clipboard endpoint.
    row = Notebook().create(safe_text(text), project='Clipboard')
    nudge_sync()
    return row


def published_clips():
    """Read only explicitly published slots. A remote request never samples the OS clipboard."""
    path=directory()/'history.sqlite3'
    if not path.exists():return []
    from contextlib import closing
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
        if not db.execute("SELECT 1 FROM settings WHERE name='auto_share' AND value='1'").fetchone():return []
        return [dict(text=text,stamp=stamp) for text,stamp in db.execute(
            'SELECT text,stamp FROM clips JOIN clip_stamp USING(id) WHERE published=1 ORDER BY id DESC LIMIT ?', (HISTORY_LIMIT,))]


def visible_clips(shelf):
    try:
        from fabric_files import request
    except ImportError:
        from .fabric_files import request
    try:remote=request('/v1/clipboard/fabric',timeout=4).get('clips',[])
    except (OSError,RuntimeError,ValueError):remote=[]
    entries=shelf.timed_rows()+[(str(row['node']),row['text'],row['stamp']) for row in remote]
    seen=set();result=[]
    for identity,text,_ in sorted(entries,key=lambda item:item[2],reverse=True):
        if text not in seen:
            result.append((identity,text));seen.add(text)
            if len(result)==HISTORY_LIMIT:break
    return result


def shared_clips():
    try:from .notebook_core import Notebook
    except ImportError:from notebook_core import Notebook
    notes=Notebook().list(kind='note')
    return [(n['id'],n['body']) for n in notes if n['project']=='Clipboard'][:HISTORY_LIMIT]


def show(*, pick=False, insert=False, fd=None, reader=None, shelf=None, shared=False):
    fd = sys.stdin.fileno() if fd is None else fd
    reader = reader or read_key
    owned = shelf is None
    shelf = shelf or Shelf()
    previous = termios.tcgetattr(fd)
    selected = 0
    expanded = False
    scroll = 0
    notice = ''
    try:
        tty.setraw(fd)
        sys.stdout.write('\033[?25l\033[?2004h')
        sample_automatic(shelf)
        ensure_watcher()
        # Freeze numbered slots while this popup owns input. New copies are
        # still captured in the background, but cannot move a target mid-keypress.
        rows = shared_clips() if shared else visible_clips(shelf)
        while True:
            selected = max(0, min(selected, len(rows)-1))
            width, height = shutil.get_terminal_size((90, 26))
            width = max(1, width-1)
            colors = terminal_style.list_colors()
            state = 'capture '+capture_description(shelf)
            lines = [colors['CYAN']+'CLIPBOARD SHELF'+ '\033[0m · '+state+' · Fabric auto-share '+('on' if shelf.setting('auto_share')=='1' else 'off')]
            if shared:
                lines=[colors['CYAN']+'FABRIC CLIPS'+'\033[0m · shared through Notes']
            if not shared and not shelf.enabled:
                lines += command_rows([('e','enables background clipboard history on this computer.')],width,colors)
                lines += ['Local capture is off. Incoming Fabric clips remain available.']
            action = 'choose' if pick else 'insert' if insert else 'copy & close'
            controls=command_rows([('1–9,0',action),('Shift-number','remove'),('↑↓','move'),('Enter','preview'),
                ('x','remove'),('e','capture on/off'),('a','add clipboard'),('s','share to Fabric'),('f','saved clips'),('r','refresh'),
                ('Esc','list' if expanded else 'back')],width,colors)
            if shared:
                controls=command_rows([('1–9,0',action),('↑↓','move'),('Enter','preview'),('r','refresh'),('f','local clips'),('Esc','back')],width,colors)
            page=max(1,height-len(lines)-len(controls)-2)
            if expanded and rows:
                content = wrap_cells(safe_text(items.preview(rows[selected][1])).expandtabs(4), width)
                scroll = min(scroll, max(0, len(content)-page))
                lines += content[scroll:scroll+page]
            else:
                top = max(0, selected-page+1)
                for index, (_, text) in list(enumerate(rows))[top:top+page]:
                    summary = ' ↵ '.join(items.describe(text).splitlines())
                    if not shared and isinstance(rows[index][0],str):summary='['+rows[index][0]+'] '+summary
                    prefix = f'{SLOTS[index]} '+('› ' if index == selected else '  ')
                    line = command_inks(colors)[0]+prefix+colors['WHITE']+clip_line(summary, max(0,width-len(prefix)))
                    lines.append(terminal_style.list_row(line, width, index, index == selected, colors))
                if not rows:
                    lines += ['No shared clips yet. Press s on a local clip to share it.' if shared else 'No saved clips yet. a adds the current clipboard; e requests automatic capture.']
            lines += controls
            lines += [safe_text(notice)]
            frame = [fit_styled(line, width) for line in lines]
            # Each styled row has already been measured; wrap explanatory text
            # separately to avoid the terminal scrolling the enclosing workspace.
            sys.stdout.write('\033[2J\033[H'+'\r\n'.join(frame[:max(1,height-1)])+'\033[0m\033[J')
            sys.stdout.flush()
            key = reader(fd, 1)
            if not key:
                continue
            if key.startswith('paste:'):
                continue
            if key in {'esc', '\x1b', 'q', '\x03'}:
                if expanded:
                    expanded = False; scroll = 0; continue
                return None
            if key in {'up', 'k'}:
                if expanded: scroll = max(0,scroll-1)
                else: selected = max(0,selected-1)
                continue
            if key in {'down', 'j'}:
                if expanded: scroll += 1
                else: selected = min(len(rows)-1,selected+1)
                continue
            if key in {'pageup','pagedown'} and expanded:
                scroll = max(0,scroll+(-page if key == 'pageup' else page)); continue
            if key in {'\r','\n','enter'} and rows:
                expanded = not expanded; scroll = 0; continue
            if key in {'f','r'}:
                try:
                    next_shared=not shared if key=='f' else shared
                    rows=shared_clips() if next_shared else visible_clips(shelf)
                    shared=next_shared;selected=0;expanded=False;scroll=0;notice=''
                except (OSError,ValueError,sqlite3.Error) as exc:notice='Could not load shared clips: '+str(exc)
                continue
            if shared and (key in {'e','a','x','s'} or removal_slot(key) is not None):continue
            if key == 'e':
                if not shelf.enabled and backend() is None:
                    notice = 'Clipboard unavailable: install wl-clipboard (Wayland) or xclip (X11).'
                    continue
                shelf.set('enabled', '0' if shelf.enabled else '1')
                if shelf.enabled:
                    shelf.set('blocked_wayland','')
                    sample_automatic(shelf)
                    ensure_watcher()
                rows = visible_clips(shelf)
                notice = 'Capture enabled' if shelf.enabled else 'Capture stopped; saved clips retained'
                continue
            if key == 'a':
                try:text=read_item()
                except ValueError as exc:
                    notice=str(exc);continue
                if text is None:notice='Clipboard read unavailable'
                else:shelf.observe(text);rows=visible_clips(shelf);notice='Current clipboard added'
                continue
            remove = removal_slot(key)
            if key == 'x':
                remove = selected
            if remove is not None and remove < len(rows):
                if isinstance(rows[remove][0],str):
                    notice='Remove this clip on its source computer.';continue
                shelf.remove(rows[remove][0]); rows = visible_clips(shelf)
                notice = 'Removed from history; system clipboard unchanged'; continue
            if key == 's' and rows:
                try:

                    if items.unpack(rows[selected][1]):
                        notice='Attachments use Fabric auto-share; Notes clips accept text.';continue
                    share_note(rows[selected][1]); notice = 'Saved to Notes · Clipboard project · normal Fabric sync'
                except (OSError, ValueError, sqlite3.Error) as exc:
                    notice = 'Note save failed: '+str(exc)
                continue
            if len(key) == 1 and key in SLOTS and SLOTS.index(key) < len(rows):
                text = rows[SLOTS.index(key)][1]
                if pick:return text
                if insert:
                    if items.unpack(text):
                        notice='Choose text to insert into this editor.';continue
                    return safe_text(text)
                # Recall is not a fresh copy to broadcast back to paired computers.
                shelf.set('recalling',hashlib.sha256(text.encode()).hexdigest())
                try:restored=items.restore(text, copy_clipboard, shelf.root)
                except (OSError,ValueError,subprocess.SubprocessError):restored=False
                if restored:
                    shelf.observe(text)
                    shelf.set('recalling','')
                    return text
                shelf.set('recalling','')
                notice = 'Clipboard write failed · saved clips retained'
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, previous)
        sys.stdout.write('\033[?2004l\033[?25h\033[0m\033[2J\033[H')
        sys.stdout.flush()
        if owned:
            shelf.close()


def main(argv=None):
    parser = argparse.ArgumentParser(prog='lk clip', description=__doc__)
    parser.add_argument('action', nargs='?', choices=['on','off','status','clear','add','shared','share'])
    parser.add_argument('mode',nargs='?',choices=['on','off'])
    parser.add_argument('--watch', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--capture-stdin',action='store_true',help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if (args.action=='share')!=bool(args.mode):parser.error('Use lk clip share on or lk clip share off')
    if args.capture_stdin:
        capture_stdin();return 0
    if args.watch:
        watch(); return 0
    if not args.action or args.action=='shared':
        if not sys.stdin.isatty():
            parser.error('Open the shelf in a terminal; use lk clip status for a text report')
        show(shared=args.action=='shared'); return 0
    shelf = Shelf()
    try:
        if args.action=='share':
            if args.mode=='on':
                if backend() is None:raise SystemExit('Clipboard capture unavailable on this computer.')
                if shelf.setting('auto_share')!='1':
                    # Establish a baseline before publishing future captures.
                    if not wayland_session():shelf.observe(read_item())
                shelf.set('enabled','1')
                shelf.auto_share(True)
                ensure_watcher()
            else:shelf.auto_share(False)
        elif args.action == 'on':
            if backend() is None:
                print('Clipboard unavailable: install wl-clipboard (Wayland) or xclip (X11).'); return 1
            shelf.set('enabled','1');shelf.set('blocked_wayland','');sample_automatic(shelf);ensure_watcher()
        elif args.action == 'off':
            shelf.set('enabled','0')
        elif args.action == 'add':
            try:text=read_item()
            except ValueError as exc:print(str(exc));return 1
            if text is None:print('Clipboard read unavailable');return 1
            shelf.observe(text)
        elif args.action == 'clear':
            shelf.clear()
        print(f'Clipboard capture {capture_description(shelf)} · {len(shelf.rows())}/10 saved · Fabric auto-share {"on" if shelf.setting("auto_share")=="1" else "off"}')
        return 0
    finally:
        shelf.close()


if __name__ == '__main__':
    raise SystemExit(main())
