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


def home_page(state):
    palette = terminal_style.list_colors()['_palette']
    rows = [(r['title'], r['url'], 'Your bookmark') for r in state['bookmarks']] + list(SHELF)
    cards = ''.join('<li><a href="' + html.escape(url, quote=True) + '">' + html.escape(title) + '</a><p>' + html.escape(description) + '</p></li>' for title, url, description in rows)
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LOOK · Reading Desk</title>
<style>body{{background:{palette['background']};color:{palette['foreground']};font:18px/1.7 monospace;max-width:850px;margin:8vh auto;padding:0 24px}}a{{color:{palette['color4']};}}a:focus{{background:{palette['selection_background']};color:{palette['selection_foreground']};}}h1{{font-size:2.8em;line-height:1.1}}small,p{{opacity:.8}}ul{{list-style:none;padding:0}}li{{border-top:1px solid {palette['color8']};padding:18px 0}}li p{{margin:4px 0;font-size:.85em}}input,button{{font:inherit;padding:8px;background:{palette['background']};color:{palette['foreground']};border:1px solid {palette['color8']};}}</style>
<header><small>LOOK / THE READING DESK</small><h1>The web.<br>At your fingertips.</h1><p>One link, then another. Take the scenic route.</p></header>
<form action="https://html.duckduckgo.com/html/" method="get"><label>Search <input name="q" aria-label="Search the web"></label><button>Go</button></form><ul>{cards}</ul>
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
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    names = list(browsers)
    name = state.get('browser') if state.get('browser') in browsers else names[0] if names else ''
    index = 0
    notice = ''
    pane_help = False
    colors = terminal_style.list_colors()
    def prompt(label, initial=''):
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write('\033[?25h')
        try:
            return look_renderer.prompt_line(label + ' › ', initial=initial)
        finally:
            tty.setcbreak(fd)
            sys.stdout.write('\033[?25l')
    try:
        tty.setcbreak(fd)
        while True:
            rows = state['bookmarks'] + [{'title': title, 'url': url, 'description': desc} for title, url, desc in SHELF]
            width, height = shutil.get_terminal_size((100, 30))
            width = max(24, width)
            index = min(index, len(rows) - 1)
            header = [colors['CYAN'] + 'LOOK / THE READING DESK\033[0m', '  The web. At your fingertips.', '']
            def ink(text, role):
                return [colors[role] + line + '\033[0m' for line in textwrap.wrap(text, width=width)]
            header += ink(name + (' · graphical window' if name == 'qutebrowser' else ' · inside this terminal') if name else 'No supported browser installed', 'GREEN')
            header += ink('TAGS '+('on' if state.get('tags',False) else 'off')+' · t toggles launch preference' if name not in {'chawan','qutebrowser'} else 'TAGS on demand · f shows, Esc cancels', 'GRAY')
            header += (terminal_style.command_lines(GUIDES[name],width,colors=colors) if name in GUIDES else ink('Install w3m, Lynx, Links, Chawan or qutebrowser; reopen lk web.','GRAY')) + ['']
            footer = [''] + terminal_style.command_lines('↑↓ choose · Shift-arrows page/ends · Enter read · b browser · u URL · s search',width,colors=colors)
            footer += terminal_style.command_lines('t tags on/off · W shell pane · a bookmark · y copy Notebook link · h home page · q/Esc exit',width,colors=colors)
            if pane_help:footer += terminal_style.command_lines(' · '.join(terminal_style.pane_shortcuts()),width,colors=colors)
            footer += ink(clean(notice), 'YELLOW') or ['']
            page_size = max(1, (height - len(header) - len(footer) - 1) // 2)
            top = max(0, index - page_size + 1)
            lines = list(header)
            for number, row in enumerate(rows[top:top + page_size], top):
                label = ('› ' if number == index else '  ') + clean(row['title'])
                lines.append(terminal_style.list_row(label, width, number, number == index, colors))
                lines.append(colors['GRAY'] + '  ' + clean(row['url'])[:width-2] + '\033[0m')
            lines += footer
            sys.stdout.write('\033[H\033[2J\033[?25l' + '\n'.join(lines) + '\n')
            sys.stdout.flush()
            key = read_key(fd,1)
            if not key:continue
            notice = ''
            if key in {'q', 'esc', '\x03'}:
                return 0
            if key == 'W':
                notice = terminal_style.open_pane(Path.cwd())
                if notice.startswith('Shell opened beside LOOK'):pane_help = True
            elif key == 'up':index = max(0, index-1)
            elif key == 'down':index = min(len(rows)-1, index+1)
            elif key in {'shiftup', 'pageup'}:index = max(0, index-page_size)
            elif key in {'shiftdown', 'pagedown'}:index = min(len(rows)-1, index+page_size)
            elif key in {'shiftleft', 'home'}:index = 0
            elif key in {'shiftright', 'end'}:index = len(rows)-1
            elif key == 'b' and names:
                name = names[(names.index(name)+1) % len(names)]
                state['browser'] = name
                save_state(state)
            elif key == 't':
                state['tags']=not state.get('tags',False)
                save_state(state)
                notice='Numbered browsers start with tags '+('on' if state['tags'] else 'off')+' · letter-hint browsers stay on demand'
            elif key == 'y':
                notice = 'Notebook link copied' if look_renderer.copy_text(note_link(rows[index])) else 'Clipboard unavailable'
            elif key in {'u', 's', 'a', 'h', '\r', '\n'}:
                try:
                    if key in {'u', 's', 'a'}:
                        value, cancelled = prompt('Search words' if key == 's' else 'Web address')
                        if cancelled or not value.strip():continue
                        url = search_url(value) if key == 's' else address(value)
                        if key == 'a':
                            title, cancelled = prompt('Bookmark name', urlsplit(url).hostname or '')
                            if cancelled:continue
                            state['bookmarks'].append({'title': clean(title) or url, 'url': url})
                            save_state(state)
                            index = len(state['bookmarks'])-1
                            continue
                    elif key == 'h':
                        folder().mkdir(parents=True, exist_ok=True)
                        page = folder() / 'home.html'
                        page.write_text(home_page(state))
                        url = page.as_uri()
                    else:url = rows[index]['url']
                    if not name:
                        notice = 'Install a browser first; bookmarks and copying still work'
                        continue
                    termios.tcsetattr(fd, termios.TCSADRAIN, old)
                    sys.stdout.write('\033[?25h');sys.stdout.flush()
                    code = launch(name, browsers[name], url, styled, tags=state.get('tags',False))
                    notice = 'Back at your reading desk' if not code else 'Browser exited with status ' + str(code)
                except (ValueError, OSError) as exc:
                    notice = str(exc)
                finally:
                    tty.setcbreak(fd)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write('\033[0m\033[?25h\n');sys.stdout.flush()


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
                page.write_text(home_page(state))
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
