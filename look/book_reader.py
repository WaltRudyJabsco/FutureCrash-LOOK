"""Bookokrat reader preference, foreground handoff and one fixed optional package."""
from __future__ import annotations
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

MODES=('auto','bookokrat','system')
BINARY_DIRS=('/opt/homebrew/bin','/home/linuxbrew/.linuxbrew/bin','/usr/local/bin','/usr/bin')


def binary(name):
    found=shutil.which(name)
    if found:return found
    roots=(*BINARY_DIRS,Path.home()/'.cargo/bin',Path.home()/'.local/bin')
    return next((str(Path(root)/name) for root in roots if (Path(root)/name).is_file() and os.access(Path(root)/name,os.X_OK)),None)


def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name)
    try:
        with os.fdopen(fd,'w') as stream:json.dump(value,stream)
        os.replace(temp,path)
    finally:Path(temp).unlink(missing_ok=True)


def preference(mode=None):
    path=Path.home()/'.config/look/book-reader.json'
    if mode is not None:
        if mode not in MODES:raise ValueError('Choose auto, bookokrat or system')
        write_json(path,{'reader':mode})
    try:value=json.loads(path.read_text()).get('reader','auto')
    except (OSError,ValueError,AttributeError):value='auto'
    return value if value in MODES else 'auto'


def graphics():
    return bool(os.environ.get('KITTY_WINDOW_ID') or os.environ.get('TERM')=='xterm-kitty'
                or os.environ.get('TERM_PROGRAM') in {'ghostty','iTerm.app','WezTerm','WarpTerminal'}
                or os.environ.get('KONSOLE_VERSION'))


def command(path,mode=None):
    mode=mode or preference()
    if mode=='system':return None
    tool=binary('bookokrat')
    if not tool:return None
    path=Path(path).resolve()
    if path.suffix.casefold()=='.pdf' and not graphics():
        if mode=='bookokrat':raise ValueError('PDF reading in Bookokrat needs a graphics-capable terminal such as Kitty; use o for the system reader')
        return None
    args=[tool,str(path),'--zen-mode']
    if not graphics():args.append('--no-images')
    return args


SHIFT_BINDINGS={'<S-Up>':'scroll_page_up','<S-Down>':'scroll_page_down',
                '<S-Left>':'go_top','<S-Right>':'go_bottom'}


def configure_bindings():
    """Add group defaults, leaving every explicit user binding and comment intact."""
    import tomllib
    config=Path.home()/'.config' if sys.platform=='darwin' else Path(os.environ.get('XDG_CONFIG_HOME') or Path.home()/'.config')
    path=config/'bookokrat/keybindings.toml'
    path.parent.mkdir(parents=True,exist_ok=True)
    with (path.parent/'.look-bindings.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        text=path.read_text() if path.exists() else ''
        try:values=tomllib.loads(text)
        except ValueError as exc:raise ValueError('Bookokrat keybindings.toml is invalid; fix it before adding LOOK controls') from exc
        existing=values.get('all',{})
        missing={key:value for key,value in SHIFT_BINDINGS.items() if key not in existing}
        if not missing:return path
        lines=['# LOOK Shift-arrows: page up/down, beginning/end. Edit or use "nop" to override.']
        lines += [json.dumps(key)+' = '+json.dumps(value) for key,value in missing.items()]
        # Insert within an existing [all] table; otherwise dotted keys belong
        # before any table header. Never serialize the user's whole config.
        content=text.splitlines(keepends=True);section=None
        for index,line in enumerate(content):
            if not line.lstrip().startswith('['):continue
            try:header=tomllib.loads(line)
            except ValueError:continue
            if header=={'all':{}}:section=index+1;break
        if section is None:
            addition='\n'.join([lines[0],*['all.'+line for line in lines[1:]]])+'\n'
            updated=addition+text
        else:
            content[section:section]=['\n'.join(lines)+'\n'];updated=''.join(content)
        tomllib.loads(updated)
        if path.exists():
            backup=path.with_suffix('.toml.look-backup')
            try:
                with backup.open('x') as out:out.write(text)
            except FileExistsError:pass
        fd,temp=tempfile.mkstemp(dir=path.parent,prefix='.look-keybindings-')
        try:
            with os.fdopen(fd,'w') as out:out.write(updated)
            os.chmod(temp,path.stat().st_mode&0o777 if path.exists() else 0o600)
            os.replace(temp,path)
        finally:Path(temp).unlink(missing_ok=True)
    return path


def capture_reader_clipboard():
    """Catch the last copy on return, only when the owner enabled LK Clip."""
    import clipboard_shelf
    if not (clipboard_shelf.directory()/'history.sqlite3').is_file():return
    shelf=clipboard_shelf.Shelf()
    try:
        clipboard_shelf.sample_automatic(shelf)
    finally:shelf.close()


def open_book(path,system_open,*,mode=None):
    args=command(path,mode)
    if args is None:
        result=system_open(path)
        if not result.startswith('OPEN OK'):raise RuntimeError(result)
        return 'Opened in system reader'
    # A stable library directory and content-named cache preserve reader-local
    # bookmarks regardless of which project directory launched the shelf.
    library=Path.home()/'.local/share/look/book-reader';library.mkdir(parents=True,exist_ok=True)
    configure_bindings()
    import clipboard_shelf
    clipboard_shelf.ensure_watcher()
    try:result=subprocess.run(args,cwd=library,check=False)
    finally:capture_reader_clipboard()
    if result.returncode:raise RuntimeError('Bookokrat exited with status '+str(result.returncode)+'; press o for the system reader')
    return 'Returned from Bookokrat · reading position is saved by the reader on this computer'


def setup_root():return Path.home()/'.cache/look/book-reader-setup'


def setup_state():
    try:value=json.loads((setup_root()/'status.json').read_text())
    except (OSError,ValueError):return {'state':'idle'}
    if value.get('state')=='installing':
        pid=value.get('pid')
        if pid:
            try:os.kill(int(pid),0)
            except (OSError,ValueError):value=dict(value,state='failed',error='Setup worker stopped; retry setup')
        elif time.time()-value.get('created',0)>10:value=dict(value,state='failed',error='Setup worker did not start; retry setup')
    return value


def status():
    tool=binary('bookokrat');version=''
    if tool:
        try:version=subprocess.run([tool,'--version'],stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=3,check=True).stdout.strip()
        except (OSError,subprocess.SubprocessError):pass
    import book_speech
    return {'speech_setup':book_speech.setup_status(),'ok':True,'reader':preference(),'installed':bool(tool and version),'version':version,
            'can_install':bool(binary('brew')),'setup':setup_state()}


def install(confirmed=False):
    if confirmed is not True:raise PermissionError('Bookokrat setup requires confirmation')
    current=status()
    if current['installed']:return current
    if not binary('brew'):raise RuntimeError('Install Bookokrat using your package manager; LOOK setup uses Homebrew/Linuxbrew where available')
    folder=setup_root();folder.mkdir(parents=True,exist_ok=True)
    with (folder/'launch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if setup_state().get('state')=='installing':return status()
        job=uuid.uuid4().hex
        write_json(folder/'status.json',{'state':'installing','job':job,'created':time.time()})
        try:
            with (folder/'setup.log').open('ab') as log:
                subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--install-worker',job],
                                 stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
        except OSError as exc:
            write_json(folder/'status.json',{'state':'failed','job':job,'error':str(exc)})
            raise
    return status()


def install_worker(job):
    folder=setup_root();path=folder/'status.json'
    def update(**fields):
        value=json.loads(path.read_text())
        if value.get('job')!=job:raise RuntimeError('Reader setup was superseded')
        write_json(path,dict(value,**fields))
    try:
        update(pid=os.getpid())
        brew=binary('brew')
        if not brew:raise RuntimeError('Homebrew/Linuxbrew unavailable')
        # Fixed package, argv-only, no sudo, scripts, arbitrary names or tap changes.
        result=subprocess.run([brew,'install','bookokrat'],stdin=subprocess.DEVNULL,
            env={**os.environ,'HOMEBREW_NO_AUTO_UPDATE':'1'},timeout=600,check=False)
        if result.returncode or not binary('bookokrat'):raise RuntimeError('Bookokrat installation failed; see '+str(folder/'setup.log'))
        update(state='ready',finished=time.time())
    except Exception as exc:update(state='failed',error=str(exc),finished=time.time())


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--install-worker':install_worker(sys.argv[2])
    else:raise SystemExit('This helper installs only Bookokrat; use lk books reader install')
