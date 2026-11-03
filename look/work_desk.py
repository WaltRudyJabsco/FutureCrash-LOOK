"""Read Markdown, review command blocks and open inline terminals."""
import argparse
import codecs
import curses
import errno
import fcntl
import os
from pathlib import Path
import pty
import re
import shlex
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time

from notebook_markdown import SHELL_FENCES, command_block, render, safe_text

DEMO = """# LK Work

A Markdown document with a terminal inside it. Press e to edit this file.

Select the shell block with Tab or the arrow keys. Press Enter to run
the displayed commands in an interactive shell.

```shell
printf 'Hello from LK Work. Try typing pwd, then Enter.\\n'
```

Ctrl+G returns to the document. Enter on the block resumes the same shell.
"""
MAX_DOCUMENT_BYTES = 256 * 1024
FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})[ \t]*([^\s`~]*)[^\n]*$')


def document_blocks(source):
    """Recognize complete top-level fences without running nested examples."""
    lines = source.splitlines(keepends=True)
    opening = None
    previous = 0
    for index, line in enumerate(lines):
        if opening is None:
            match = FENCE.fullmatch(line.rstrip('\r\n'))
            if match:
                opening = (index, *match.groups())
            continue
        start, marker, language = opening
        if re.fullmatch(r' {0,3}'+re.escape(marker[0])+r'{'+str(len(marker))+r',}[ \t]*', line.rstrip('\r\n')):
            opening = None
            language = language.lower()
            if language in SHELL_FENCES or language == 'command':
                info = lines[start].lstrip()[len(marker):].strip()
                yield ''.join(lines[previous:start]), ''.join(lines[start+1:index]), language, info
                previous = index+1
    yield ''.join(lines[previous:]), None, '', ''


class InlineShell:
    def __init__(self, pyte, cwd, script, columns, rows, language):
        self.screen = pyte.Screen(columns, rows)
        self.stream = pyte.Stream(self.screen)
        self.decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        self.script = tempfile.TemporaryDirectory(prefix='lk-work-')
        try:
            path = Path(self.script.name)/'block.sh'
            path.write_text(script, encoding='utf-8')
            shell = (os.environ.get('SHELL') or '/bin/sh') if language == 'shell' else '/bin/'+language
            if not os.path.isabs(shell) or not os.access(shell, os.X_OK):
                raise ValueError(f'Shell unavailable: {shell}')
            self.pid, self.fd = pty.fork()
        except BaseException:
            self.script.cleanup()
            raise
        if self.pid == 0:
            try:
                os.chdir(cwd)
                env = dict(os.environ, TERM='xterm', PS1='work $ ')
                options = {'bash':['--noprofile','--norc'], 'zsh':['-f']}.get(language, [])
                os.execve(shell, [shell,*options,'-i'], env)
            except OSError as error:
                os.write(2, f'{error}\n'.encode())
                os._exit(127)
        self.running = True
        try:
            self.resize(columns, rows)
            self.send(('. '+shlex.quote(str(path))+'\n').encode())
            os.set_blocking(self.fd, False)
        except BaseException:
            self.close()
            raise

    def resize(self, columns, rows):
        if (columns, rows) != (self.screen.columns, self.screen.lines):
            self.screen.resize(lines=rows, columns=columns)
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack('HHHH', rows, columns, 0, 0))

    def send(self, data):
        if not self.running:
            return
        try:
            os.write(self.fd, data)
        except BlockingIOError:
            return
        except OSError as error:
            if error.errno != errno.EIO:
                raise
            self.running = False

    def read(self):
        for _ in range(8):
            if not self.running:
                return
            try:
                data = os.read(self.fd, 8192)
            except BlockingIOError:
                return
            except OSError as error:
                if error.errno != errno.EIO:
                    raise
                data = b''
            self.stream.feed(self.decoder.decode(data, final=not data))
            if not data:
                self.running = False

    def close(self):
        # Signal before closing the master. Some terminals wait for output to drain.
        try:
            try:
                os.kill(self.pid, signal.SIGHUP)
            except ProcessLookupError:
                pass
            for _ in range(10):
                if os.waitpid(self.pid, os.WNOHANG)[0]:
                    return
                time.sleep(.02)
            try:
                os.kill(self.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.waitpid(self.pid, 0)
        finally:
            os.close(self.fd)
            self.script.cleanup()


KEYS = {
    curses.KEY_UP:b'\x1b[A', curses.KEY_DOWN:b'\x1b[B',
    curses.KEY_RIGHT:b'\x1b[C', curses.KEY_LEFT:b'\x1b[D',
    curses.KEY_HOME:b'\x1b[H', curses.KEY_END:b'\x1b[F',
    curses.KEY_DC:b'\x1b[3~', curses.KEY_BACKSPACE:b'\x7f',
    curses.KEY_PPAGE:b'\x1b[5~', curses.KEY_NPAGE:b'\x1b[6~',
    curses.KEY_ENTER:b'\r',
}
# pyte decodes child escape sequences. Emit only colors and attributes that
# we construct ourselves, never control sequences supplied by the child.
BASE_COLORS = ('black','red','green','brown','blue','magenta','cyan','white')
NAMED_COLORS = {name:i for i,name in enumerate(BASE_COLORS)}
NAMED_COLORS.update({'bright'+name:i+8 for i,name in enumerate(BASE_COLORS)})
NAMED_COLORS.update({'yellow':3,'brightyellow':11})


def color_code(value, background=False):
    offset = 10 if background else 0
    if value in NAMED_COLORS:
        index = NAMED_COLORS[value]
        return str((30+index if index<8 else 90+index-8)+offset)
    if re.fullmatch(r'[0-9a-fA-F]{6}',value):
        rgb = [str(int(value[i:i+2],16)) for i in (0,2,4)]
        return ';'.join(['48' if background else '38','2',*rgb])
    return '49' if background else '39'


def styled_terminal_rows(screen):
    for row in range(screen.lines):
        cells = []
        previous = None
        for column in range(screen.columns):
            char = screen.buffer[row][column]
            style = (char.fg,char.bg,char.bold,char.italics,char.underscore,char.reverse,char.strikethrough)
            if style != previous:
                codes = ['0',color_code(char.fg),color_code(char.bg,True)]
                codes.extend(code for enabled,code in zip(style[2:],('1','3','4','7','9')) if enabled)
                cells.append('\033['+';'.join(codes)+'m')
                previous = style
            cells.append(safe_text(char.data))
        yield ''.join(cells)+'\033[0m'


def curses_terminal_line(window,row,column,screen,index,pairs):
    for pos in range(screen.columns):
        char = screen.buffer[index][pos]
        if not char.data:
            continue
        fg,bg = (curses_color(value) for value in (char.fg,char.bg))
        colors = fg,bg
        if colors not in pairs and len(pairs) < min(curses.COLOR_PAIRS-1,255):
            pair = len(pairs)+1
            curses.init_pair(pair,fg,bg)
            pairs[colors] = curses.color_pair(pair)
        attr = pairs.get(colors,0)
        for enabled,flag in ((char.bold,curses.A_BOLD),(char.underscore,curses.A_UNDERLINE),
                             (char.reverse,curses.A_REVERSE)):
            if enabled:
                attr |= flag
        try:
            window.addstr(row,column+pos,safe_text(char.data),attr)
        except curses.error:
            pass


def curses_color(value):
    if value in NAMED_COLORS:
        return NAMED_COLORS[value] % curses.COLORS
    if re.fullmatch(r'[0-9a-fA-F]{6}',value) and curses.COLORS>=256:
        red,green,blue = (round(int(value[i:i+2],16)/51) for i in (0,2,4))
        return 16+36*red+6*green+blue
    return -1


def inline_height(page):
    return max(2,min(20,(page*2)//3,page-2))


def notes_key(key):
    mapping = {
        'up':b'\x1b[A','down':b'\x1b[B','right':b'\x1b[C','left':b'\x1b[D',
        'home':b'\x1b[H','end':b'\x1b[F','delete':b'\x1b[3~',
        'pageup':b'\x1b[5~','pagedown':b'\x1b[6~','enter':b'\r','esc':b'\x1b',
    }
    if key.startswith('paste:'):
        return key[6:].encode()
    if len(key)==1:
        return key.replace('\n','\r').encode()
    return mapping.get(key)


ANSI_STYLE = re.compile(r'\x1b\[[0-9;]*m')


def document_rows(source, width):
    return [ANSI_STYLE.sub('', row).rstrip() for row in render(source, width)]


def read_document(path):
    if not path.is_file():
        raise ValueError('Choose a Markdown file.')
    with path.open('rb') as file:
        data = file.read(MAX_DOCUMENT_BYTES+1)
    if len(data)>MAX_DOCUMENT_BYTES:
        raise ValueError('Choose a document smaller than 256 KiB.')
    return data.decode('utf-8-sig')


def edit_document(window, path):
    editor = shlex.split(os.environ.get('VISUAL') or os.environ.get('EDITOR') or
                         ('nvim' if shutil.which('nvim') else 'vi'))
    curses.def_prog_mode()
    curses.endwin()
    try:
        subprocess.run([*editor, str(path)], check=True)
    finally:
        curses.reset_prog_mode()
        window.clearok(True)


def hint_rows(bindings, width):
    rows = [[]]
    used = 0
    for key, action in bindings:
        length = len(key)+len(action)+3
        if rows[-1] and used+length > width:
            rows.append([])
            used = 0
        rows[-1].append((key, action))
        used += length
    return rows


def run_command(window, path, target):
    from look_renderer import read_key
    from notebook import confirm_command, resolve_command, run_note_command

    target = resolve_command({'path':path},target)
    curses.def_prog_mode()
    curses.endwin()
    try:
        if not confirm_command(sys.stdin.fileno(),lambda *_: read_key(),target):
            return 'Command cancelled'
        return 'Command exited '+str(run_note_command(target))
    finally:
        curses.reset_prog_mode()
        window.clearok(True)


def desk(window, pyte, path, source, block=None, editable=True):
    title, cwd = path.name, path.parent
    parts = list(document_blocks(source))
    curses.raw()
    window.keypad(True)
    window.timeout(50)
    accent = curses.A_BOLD
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        accent |= curses.color_pair(1)
    pairs = {(-1,-1):0}
    sessions = {}
    focused = False
    offset = 0
    shell_indices = [i for i, part in enumerate(parts) if part[2] in SHELL_FENCES]
    selected = shell_indices[block-1] if block else None
    reveal_selection = selected is not None
    rendered_width = None
    notice = ''
    try:
        while True:
            height, width = window.getmaxyx()
            if height < 9 or width < 30:
                window.erase()
                window.addnstr(0, 0, 'Resize terminal to continue', max(0,width-1))
                window.refresh()
                try:
                    key = window.get_wch()
                except curses.error:
                    continue
                if key in ('q', '\x03', '\x1b'):
                    return
                continue
            columns = width-5
            bindings = [('Ctrl+G','document'), ('Ctrl+C','interrupt'), ('exit','end shell')] if focused else [
                ('↑↓','scroll'), ('Tab','next action'), ('Enter','open'), *([('e','edit')] if editable else []), ('q','quit')]
            hints = hint_rows(bindings, width-1)
            footer_top = height-len(hints)-1
            terminal_rows = inline_height(footer_top-1)
            for session in sessions.values():
                session.read()
            shell = sessions.get(selected)
            if focused and not shell.running:
                focused = False
            if focused and (columns, terminal_rows) != (shell.screen.columns, shell.screen.lines):
                shell.resize(columns, terminal_rows)
            if rendered_width != columns:
                prose_rows = [document_rows(prose, columns) for prose, _, _, _ in parts]
                rendered_width = columns
            rows = []
            positions = []
            for number, ((_, script, language, info), prose) in enumerate(zip(parts, prose_rows)):
                rows.extend((row, curses.A_NORMAL) for row in prose)
                if script is None:
                    continue
                positions.append(len(rows))
                session = sessions.get(number)
                active = focused and selected == number
                label = 'Shell exited' if session and not session.running else 'Live shell' if active else 'Resume shell' if session else 'Run shell block'
                if language == 'command':
                    try:
                        name, _ = command_block(info,script)
                    except ValueError:
                        name = 'Invalid command block'
                    header = 'Run: '+safe_text(name)
                else:
                    header = f'[{language}] {label} {number+1} · {cwd}'
                rows.append((header, accent | (curses.A_REVERSE if selected == number else 0)))
                if session and (active or not session.running):
                    rows.extend(('│ '+safe_text(line), (session.screen,i))
                                for i,line in enumerate(session.screen.display))
                else:
                    rows.extend(('│ '+line, curses.A_DIM) for line in safe_text(script).expandtabs(4).splitlines())
            block = positions[selected] if selected is not None else 0
            page = max(1,footer_top-1)
            if focused or reveal_selection:
                offset = block
                reveal_selection = False
            offset = min(offset, max(0,len(rows)-page))
            window.erase()
            window.addnstr(0, 0, 'LK WORK  ·  '+safe_text(title), max(0,width-1), accent)
            for index, (line, style) in enumerate(rows[offset:offset+page],1):
                try:
                    if isinstance(style,tuple):
                        screen,screen_row = style
                        window.addstr(index,1,'│ ')
                        if curses.has_colors():
                            curses_terminal_line(window,index,3,screen,screen_row,pairs)
                        else:
                            window.addnstr(index,1,line,width-2)
                    else:
                        window.addnstr(index, 1, line, max(0,width-2), style)
                except curses.error:
                    pass
            for row, bindings in enumerate(hints, footer_top):
                column = 0
                for key, action in bindings:
                    window.addnstr(row,column,key,width-column-1,accent)
                    column += len(key)
                    label = ' '+action+'  '
                    window.addnstr(row,column,label,width-column-1,curses.A_DIM)
                    column += len(label)
            if notice:
                window.addnstr(height-1,0,safe_text(notice),width-1,curses.A_DIM)
            cursor_row = block+2+shell.screen.cursor.y-offset if focused else -1
            try:
                curses.curs_set(int(0<cursor_row<footer_top))
                if 0<cursor_row<footer_top:
                    window.move(cursor_row,min(width-1,3+shell.screen.cursor.x))
            except curses.error:
                pass
            window.refresh()
            try:
                key = window.get_wch()
            except curses.error:
                continue
            if focused:
                if key == '\x07':
                    focused = False
                else:
                    data = KEYS.get(key) if isinstance(key,int) else key.replace('\n','\r').encode()
                    if data:
                        shell.send(data)
                continue
            if key in ('q','\x1b','\x03'):
                return
            if key == 'e' and editable:
                try:
                    edit_document(window, path)
                    updated = read_document(path)
                    updated_parts = list(document_blocks(updated))
                    for number in list(sessions):
                        if number >= len(updated_parts) or updated_parts[number][1:] != parts[number][1:]:
                            sessions.pop(number).close()
                    parts = updated_parts
                    rendered_width = None
                    selected = None
                    notice = 'Reloaded '+path.name
                except (OSError, ValueError, subprocess.CalledProcessError) as error:
                    notice = str(error)
            elif key == '\t' and positions:
                selected = 0 if selected is None else (selected+1) % len(positions)
                offset = positions[selected]
            elif key in (curses.KEY_DOWN, 'j', curses.KEY_NPAGE, curses.KEY_UP, 'k', curses.KEY_PPAGE):
                direction = 1 if key in (curses.KEY_DOWN, 'j', curses.KEY_NPAGE) else -1
                step = page if key in (curses.KEY_PPAGE, curses.KEY_NPAGE) else 1
                offset = max(0,min(max(0,len(rows)-page),offset+direction*step))
                visible = [i for i, row in enumerate(positions) if offset<=row<offset+page]
                if selected not in visible:
                    selected = visible[0] if visible else None
            elif key in ('\n','\r',curses.KEY_ENTER) and selected is not None:
                _, script, language, info = parts[selected]
                if language == 'command':
                    try:
                        _, target = command_block(info,script)
                        notice = run_command(window,path,target)
                    except (ValueError,OSError) as error:
                        notice = str(error)
                    continue
                if shell and not shell.running:
                    sessions.pop(selected).close()
                    shell = None
                if shell is None:
                    shell_language = 'shell' if language == 'terminal' else language
                    sessions[selected] = InlineShell(pyte,cwd,script,columns,terminal_rows,shell_language)
                focused = True
    finally:
        for session in sessions.values():
            session.close()


def main(argv=None):
    parser = argparse.ArgumentParser(prog='lk work', description='Read Markdown, review command blocks and open interactive shell blocks.')
    parser.add_argument('document', nargs='?', type=Path, help='Markdown file. Omit to open the demo.')
    parser.add_argument('--block', type=int, help='Select a shell block by number.')
    parser.add_argument('--read-only', action='store_true', help='Edit managed notes in Notes.')
    args = parser.parse_args(argv)
    try:
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            raise ValueError('Open LK Work in Kitty or another interactive terminal.')
        if args.document:
            path = args.document.expanduser().resolve(strict=True)
        else:
            path = Path.home()/'.local/share/look/work/demo.md'
            path.parent.mkdir(parents=True,exist_ok=True)
            try:
                with path.open('x', encoding='utf-8') as file:
                    file.write(DEMO)
            except FileExistsError:
                pass
        source = read_document(path)
        try:
            import pyte
        except ImportError:
            raise ValueError('LK Work needs pyte in the Python environment running lk. Install it in a virtual environment and run lk with that Python.') from None
        if args.block is not None and not 1 <= args.block <= sum(part[2] in SHELL_FENCES for part in document_blocks(source)):
            raise ValueError('Shell block no longer exists.')
        curses.wrapper(desk,pyte,path,source,args.block,not args.read_only)
    except (OSError,ValueError,curses.error) as error:
        print(f'LK Work · {error}',file=sys.stderr)
        return 1
    return 0
