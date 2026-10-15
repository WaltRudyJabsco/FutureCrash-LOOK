"""A local reading desk around existing browsers; each browser owns its session."""
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import termios
import textwrap
import tty
from urllib.parse import urlencode, urlsplit

import terminal_style

BROWSERS = ('w3m', 'lynx', 'links', 'links2', 'chawan', 'qutebrowser')
GUIDES = {
    'w3m': 'Esc-h tags on/off · number then Esc-j selects · Tab link · Enter open · B back · q quit',
    'lynx': 'o options → Keypad mode · number + Enter open · ← back · g address · q quit',
    'links': 'Esc menu → View → HTML options → Links are numbered · number + Enter open · ← back · g address · q quit',
    'links2': 'Esc menu → View → HTML options → Links are numbered · number + Enter open · ← back · g address · q quit',
    'chawan': 'f letter hints · type letters, Enter open · / find · q quit',
    'qutebrowser': 'f letter hints · o address · j/k scroll · H back · / find · :quit',
}
SHELF = (
    ('Internet Archive', 'https://archive.org/', 'Films, recordings, books, and the unexpected'),
    ('Project Gutenberg', 'https://www.gutenberg.org/', 'A library without a checkout desk'),
    ('Wikipedia', 'https://en.wikipedia.org/', 'Follow one thread into another'),
    ('Hacker News', 'https://news.ycombinator.com/', 'A naturally text-shaped corner of the web'),
    ('Chawan', 'https://chawan.net/', 'Terminal browsing with letter hints'),
    ('Qutebrowser', 'https://qutebrowser.org/quickstart.html', 'Keyboard browsing in a graphical window'),
)


def folder():
    return Path.home() / '.local/share/look/web'


def clean(value):
    return ''.join(c for c in str(value) if c.isprintable()).strip()


def address(value):
    value = str(value).strip()
    if not value or any(c.isspace() or not c.isprintable() for c in value):
        raise ValueError('Enter one web address; use search for words')
    if '://' not in value:
        value = 'https://' + value
    parsed = urlsplit(value)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname:
        raise ValueError('Use an http:// or https:// web address')
    if parsed.username is not None or parsed.password is not None:
        raise ValueError('Use the browser login form rather than credentials in a URL')
    parsed.port  # Validate malformed ports before handing anything to a browser.
    return value


def search_url(words):
    words = str(words).strip()
    if not words:
        raise ValueError('Enter some search words')
    return 'https://html.duckduckgo.com/html/?' + urlencode({'q': words})


def discover():
    result = {}
    for name in BROWSERS:
        executable = shutil.which('cha' if name == 'chawan' else name)
        if name == 'qutebrowser' and not executable:
            for root in (Path('/Applications'), Path.home() / 'Applications'):
                candidate = root / 'qutebrowser.app/Contents/MacOS/qutebrowser'
                if candidate.is_file() and os.access(candidate, os.X_OK):
                    executable = str(candidate)
                    break
        if executable:
            result[name] = executable
    return result


def load_state():
    try:
        data = json.loads((folder() / 'desk.json').read_text())
        if not isinstance(data, dict):
            raise ValueError('Invalid saved reading desk')
    except FileNotFoundError:
        return {'browser': '', 'bookmarks': []}
    bookmarks = []
    if not isinstance(data.get("bookmarks", []), list):
        raise ValueError("Saved bookmarks must be a list")
    for row in data.get('bookmarks', []):
        try:
            bookmarks.append({'title': clean(row['title']), 'url': address(row['url'])})
        except (KeyError, TypeError, ValueError):
            continue
    browser = data.get('browser', '')
    result={'browser': browser if isinstance(browser, str) and browser in BROWSERS else '', 'bookmarks': bookmarks}
    if isinstance(data.get('tags'),bool):result['tags']=data['tags']
    identity=data.get('home_note')
    if isinstance(identity,str) and len(identity)==32 and all(c in '0123456789abcdef' for c in identity):result['home_note']=identity
    return result


def save_state(data):
    folder().mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=folder(), delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(data, stream, ensure_ascii=False, indent=2)
    try:
        os.replace(temporary, folder() / 'desk.json')
    finally:
        temporary.unlink(missing_ok=True)


def note_link(row):
    title = clean(row['title']).replace('\\', '\\\\').replace('[', '\\[').replace(']', '\\]')
    url = address(row['url']).replace('(', '%28').replace(')', '%29')
    return '[' + title + '](' + url + ')'


def note_record(store,identity):
    rows=[row for row in store.list(include_done=True) if row['id']==identity]
    return rows[0] if len(rows)==1 and not rows[0]['conflict'] else None


def home_note(state,store,replace_missing=False):
    identity=state.get('home_note')
    if identity and not replace_missing:return note_record(store,identity)
    body='Web Home\n\nYour reading desk. Press e to edit; add headings, links and your own notes.\n\n## News\n[Google News](https://news.google.com/)\n\n## Reading\n'
    rows=state.get('bookmarks',[])
    body+='\n'.join(note_link(row) for row in rows)
    body+='\n\n'+ '\n'.join(note_link({'title':title,'url':url}) for title,url,_ in SHELF)
    identity=store.create(body,project='Web')['note']
    state['home_note']=identity;save_state(state)
    return note_record(store,identity)


def home_page(state, row=None):
    palette = terminal_style.list_colors()['_palette']
    rows = [(r['title'], r['url'], 'Your bookmark') for r in state['bookmarks']] + list(SHELF)
    if row is not None:
        import notebook_markdown
        rows=[]
        for label,target in notebook_markdown.extract_links(row['body']):
            if not target.startswith(('https://','http://')):continue
            try:rows.append((label,address(target),'From your home note'))
            except ValueError:continue
    prose=''
    if row is not None:
        import re
        text='\n'.join(re.sub(r'\x1b\[[0-9;]*m','',line).rstrip() for line in notebook_markdown.render(row['body'],90))
        prose='<pre style="white-space:pre-wrap">'+html.escape(text)+'</pre>'
    cards = ''.join('<li><a href="' + html.escape(url, quote=True) + '">' + html.escape(title) + '</a><p>' + html.escape(description) + '</p></li>' for title, url, description in rows)
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LOOK · Reading Desk</title>
<style>body{{background:{palette['background']};color:{palette['foreground']};font:18px/1.7 monospace;max-width:850px;margin:8vh auto;padding:0 24px}}a{{color:{palette['color4']};}}a:focus{{background:{palette['selection_background']};color:{palette['selection_foreground']};}}h1{{font-size:2.8em;line-height:1.1}}small,p{{opacity:.8}}ul{{list-style:none;padding:0}}li{{border-top:1px solid {palette['color8']};padding:18px 0}}li p{{margin:4px 0;font-size:.85em}}input,button{{font:inherit;padding:8px;background:{palette['background']};color:{palette['foreground']};border:1px solid {palette['color8']};}}</style>
<header><small>LOOK / THE READING DESK</small><h1>The web.<br>At your fingertips.</h1><p>One link, then another. Take the scenic route.</p></header>
{prose}<form action="https://html.duckduckgo.com/html/" method="get"><label>Search <input name="q" aria-label="Search the web"></label><button>Go</button></form><ul>{cards}</ul>
<footer><small>Qutebrowser: f → letters opens a link. Chawan: f → letters → Enter.<br>Return to your terminal for lk web and your Notebook links.</small></footer></html>'''


def w3m_keymap(directory):
    """Overlay the effective personal keymap for this invocation; never rewrite it."""
    root=Path(os.environ.get('W3M_DIR') or Path.home()/'.w3m').expanduser()
    source=root/'keymap'
    config=root/'config'
    if config.is_file():
        for line in config.read_text().splitlines():
            parts=line.split(None,1)
            if len(parts)==2 and parts[0]=='keymap_file':
                source=Path(parts[1].strip()).expanduser()
                if not source.is_absolute():source=root/source
    original=source.read_text() if source.is_file() else ''
    overlay=Path(directory)/'keymap'
    # Enter follows normally, then restores clean reading; numbered selection uses w3m prefixes.
    overlay.write_text(original+'\nkeymap M-h COMMAND "SET_OPTION display_link_number=toggle; RESHAPE"\n'
                       +'keymap M-j LINK_N\nkeymap C-m COMMAND "GOTO_LINK; SET_OPTION display_link_number=0; RESHAPE"\nkeymap C-j COMMAND "GOTO_LINK; SET_OPTION display_link_number=0; RESHAPE"\n')
    return overlay



def launch(name, executable, url, styled=True, tags=False):
    # Argument lists keep pasted URLs inert. Styles are invocation-only; personal
    # browser configuration and keymaps remain owned by the browser.
    with tempfile.TemporaryDirectory(prefix='look-web-') as directory:
        args = [executable]
        if name == 'w3m':
            args += ['-o', 'display_link_number='+str(int(tags)), '-o', 'keymap_file='+str(w3m_keymap(directory))]
            if styled:
                for option in ('color=1', 'basic_color=terminal', 'bg_color=terminal', 'anchor_color=blue', 'visited_color=magenta', 'active_style=1', 'active_color=cyan'):
                    args += ['-o', option]
        elif name == 'lynx':
            args += ['-number_links='+('on' if tags else 'off'), '-default_colors']
            if styled:
                style = Path(directory) / 'look.lss'
                style.write_text('normal:normal:default:default\ndefault:normal:default:default\na:normal:blue:default\nh1:bold:cyan:default\nh2:bold:cyan:default\nalink:reverse:default:default\nstatus:reverse:default:default\nalert:bold:red:default\nwhereis:reverse:magenta:default\n')
                args += ['-lss=' + str(style)]
        elif name in {'links', 'links2'}:
            args += ['-html-numbered-links', str(int(tags))]
            if styled:
                palette = terminal_style.list_colors()['_palette']
                light = terminal_style.luminance(palette['background']) > .5
                args += ['-html-ignore-document-color', '1', '-html-text-color', '0' if light else '7', '-html-background-color', '7' if light else '0', '-html-link-color', '4' if light else '6']
        result = subprocess.run([*args, url], check=False)
        return result.returncode


def desk(state, browsers, read_key, styled):
    import look_renderer
    import notebook
    store=notebook.Notebook()
    home=home_note(state,store)
    current=home;stack=[];index=0;top=0;notice='';help_open=False;pane_help=False
    fd=sys.stdin.fileno();old=termios.tcgetattr(fd)
    names=list(browsers)
    name=state.get('browser') if state.get('browser') in browsers else next(iter(browsers),'')
    colors=terminal_style.list_colors()

    def prompt(label,initial=''):
        termios.tcsetattr(fd,termios.TCSADRAIN,old);sys.stdout.write('\033[?25h')
        try:return look_renderer.prompt_line(label+' › ',initial=initial)
        finally:tty.setcbreak(fd);sys.stdout.write('\033[?25l')

    def open_target(target):
        nonlocal current,index,top,notice
        kind,value=notebook.resolve_link(store,current,target)
        if kind=='note':
            stack.append(current['id']);current=value;index=top=0;return
        if kind=='command' and not notebook.confirm_command(fd,read_key,value):return
        termios.tcsetattr(fd,termios.TCSADRAIN,old);sys.stdout.write('\033[?25h');sys.stdout.flush()
        try:
            if kind=='url':
                if not name:raise ValueError('Install a browser; b selects installed browsers')
                code=launch(name,browsers[name],address(value),styled,tags=state.get('tags',False))
                notice='Back at your reading desk' if not code else 'Browser exited with status '+str(code)
            elif kind=='command':notice='Command exited '+str(notebook.run_note_command(value))
            else:notebook.open_link(kind,value);notice='Back at your reading desk'
        finally:tty.setcbreak(fd);sys.stdout.write('\033[?25l')

    try:
        tty.setcbreak(fd)
        while True:
            # Notebook owns revisions/conflicts; never cache a second editable copy.
            if current:current=note_record(store,current['id'])
            width,height=shutil.get_terminal_size((100,30));width=max(24,width-1)
            links=[]
            body=notebook.render_markdown(current['body'],width,links) if current else ['Home note missing or conflicted. Press n to choose a note, or e to create a new home.']
            body=[line.replace('38;5;117',colors['CYAN'][2:-1]) for line in body]
            index=max(0,min(index,max(0,len(links)-1)))
            controls='↑↓ links · Shift-↑↓ read page · Shift-←→ first/last · Enter open · l links'
            actions='e edit note · n choose home · a bookmark · h home · r related · y copy link'
            settings='b browser · t tags · u URL · s search · W shell pane · ? help · q/Esc back'
            footer=[]
            for text in (controls,actions,settings):footer+=terminal_style.command_lines(text,width,colors=colors)
            if help_open:footer+=terminal_style.command_lines(GUIDES.get(name,'No browser installed · lk web list'),width,colors=colors)
            if pane_help:footer+=terminal_style.command_lines(' · '.join(terminal_style.pane_shortcuts()),width,colors=colors)
            page=max(1,height-len(footer)-6)
            top=max(0,min(top,max(0,len(body)-page)))
            title=clean(current['title']) if current else 'Choose your home'
            header=[colors['CYAN']+'LOOK / THE READING DESK\033[0m · '+title,
                    colors['GRAY']+(name or 'No browser')+' · '+('graphical' if name=='qutebrowser' else 'terminal')+' · tags '+('on demand' if name in {'chawan','qutebrowser'} else 'on' if state.get('tags',False) else 'off')+' · '+('HOME' if current and current['id']==state.get('home_note') else 'NOTE')+'\033[0m',
                    '─'*width]
            lines=header
            token=' ['+str(index+1)+']'
            for number,line in enumerate(body[top:top+page],top):
                focused=bool(links and token in look_renderer.strip_ansi(line))
                lines.append(terminal_style.list_row(line,width,number,True,colors) if focused else line)
            lines+=['']*max(0,page-len(body[top:top+page]))
            selected=(str(index+1)+' / '+str(len(links))+' · '+clean(links[index][0])+' · '+clean(links[index][1] if isinstance(links[index][1],str) else 'command — confirmation required')) if links else 'No links yet · e edits Markdown · a adds a bookmark'
            lines+=[colors['GRAY']+selected+'\033[0m',*footer,colors['YELLOW']+clean(notice)+'\033[0m']
            sys.stdout.write('\033[H\033[2J\033[?25l'+'\n'.join(look_renderer.fit(line,width) for line in lines)+'\033[J');sys.stdout.flush()
            key=read_key(fd,1)
            if not key:continue
            notice=''
            try:
                if key in {'q','\x03'}:return 0
                if key=='esc':
                    if stack:current=note_record(store,stack.pop());index=top=0;continue
                    return 0
                if key in {'up','down','\t'}:
                    index=max(0,min(len(links)-1,index+(-1 if key=='up' else 1)))
                    token=' ['+str(index+1)+']'
                    location=next((i for i,line in enumerate(body) if token in look_renderer.strip_ansi(line)),top)
                    if location<top:top=location
                    elif location>=top+page:top=location-page+1
                elif key in {'shiftup','pageup'}:top-=page
                elif key in {'shiftdown','pagedown',' '}:top+=page
                elif key in {'shiftleft','home'}:index=top=0
                elif key in {'shiftright','end'}:index=max(0,len(links)-1);top=max(0,len(body)-page)
                elif key=='?':help_open=not help_open
                elif key=='W':notice=terminal_style.open_pane(Path.cwd());pane_help=notice.startswith('Shell opened beside LOOK')
                elif key=='b' and names:
                    name=names[(names.index(name)+1)%len(names)];state['browser']=name;save_state(state)
                elif key=='t':state['tags']=not state.get('tags',False);save_state(state)
                elif key=='h':current=home_note(state,store);stack=[];index=top=0
                elif key=='n':
                    chosen=notebook.choose_note(store,fd,read_key)
                    if chosen:
                        state['home_note']=chosen['id'];save_state(state);current=chosen;stack=[];index=top=0
                elif key=='e':
                    if current:notice=notebook.quick_edit(store,current,fd,read_key)
                    else:current=home_note(state,store,replace_missing=True);notice='Created Web Home in Notes'
                elif key in {'u','s','a'}:
                    value,cancelled=prompt('Search words' if key=='s' else 'Web address')
                    if cancelled or not value.strip():continue
                    url=search_url(value) if key=='s' else address(value)
                    if key=='a':
                        title,cancelled=prompt('Bookmark name',urlsplit(url).hostname or '')
                        if cancelled:continue
                        home=home_note(state,store)
                        if not home:raise ValueError('Choose a home note first with n')
                        store.change(home['id'],{'body':home['body'].rstrip()+'\n\n'+note_link({'title':title or url,'url':url})+'\n'},expected=home['revision'])
                        notebook.nudge_sync();notice='Bookmark added to home note'
                    else:open_target(url)
                elif key=='y' and links:
                    label,target=links[index]
                    if not isinstance(target,str):raise ValueError('Edit the note to copy a command block')
                    notice='Notebook link copied' if look_renderer.copy_text(notebook.make_link(label,target)) else 'Clipboard unavailable'
                elif key=='r' and not current:notice='Choose a home note first with n'
                elif key in {'l','r'} or key in {'\r','\n'} and links or len(key)==1 and key in '123456789' and int(key)<=len(links):
                    target=notebook.choose_link(fd,read_key,notebook.related_notes(store,current) if key=='r' else links,'RELATED NOTES' if key=='r' else 'HOME LINKS') if key in {'l','r'} else links[int(key)-1 if key in '123456789' else index][1]
                    if target is not None:open_target(target)
            except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:notice=clean(str(exc))
    finally:
        termios.tcsetattr(fd,termios.TCSADRAIN,old);sys.stdout.write('\033[0m\033[?25h\n');sys.stdout.flush()


def main(args=None, *, read_key=None):
    parser = argparse.ArgumentParser(prog='lk web', description='A keyboard reading desk for installed terminal browsers and qutebrowser.')
    parser.add_argument('target', nargs='*', help='URL, search WORDS, home, or list')
    parser.add_argument('--browser', choices=BROWSERS, help='Select a browser; qutebrowser opens a graphical window')
    parser.add_argument('--tags', choices=('on','off'), help='Initial numbered-link display; defaults to remembered preference or off')
    parser.add_argument('--native-style', action='store_true', help='Keep the browser appearance instead of LOOK invocation colors')
    options = parser.parse_args(args)
    try:
        browsers = discover()
        state = load_state()
        if options.tags is not None:state['tags']=options.tags=='on'
        name = options.browser or (state.get('browser') if state.get('browser') in browsers else next(iter(browsers), ''))
        if options.target == ['list']:
            for browser in BROWSERS:
                print(browser + ' · ' + ('installed' if browser in browsers else 'not installed') + (' · graphical' if browser == 'qutebrowser' else ' · terminal'))
            return 0
        if options.target:
            if name not in browsers:
                raise ValueError((name or 'A supported browser') + ' is not installed; run lk web list')
            if options.target == ['home']:
                folder().mkdir(parents=True, exist_ok=True)
                page = folder() / 'home.html'
                from notebook_core import Notebook
                row=home_note(state,Notebook())
                if row is None:raise ValueError('Home note missing/conflicted; open lk web and press n to choose a note')
                page.write_text(home_page(state,row))
                url = page.as_uri()
            elif options.target[0] == 'search':url = search_url(' '.join(options.target[1:]))
            elif len(options.target) == 1:url = address(options.target[0])
            else:raise ValueError('Use lk web search WORDS, or one URL')
            if name != 'qutebrowser' and not (sys.stdin.isatty() and sys.stdout.isatty()):
                raise ValueError('Terminal browsing needs an interactive terminal')
            return launch(name, browsers[name], url, not options.native_style, tags=state.get('tags',False))
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            print('Run lk web in a terminal, or lk web list to inspect installed browsers.')
            return 0
        if options.browser:
            if name not in browsers:raise ValueError(name + ' is not installed')
            state['browser'] = name
        return desk(state, browsers, read_key, not options.native_style)
    except (OSError, ValueError) as exc:
        print('LOOK Web: ' + str(exc), file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        return 0
