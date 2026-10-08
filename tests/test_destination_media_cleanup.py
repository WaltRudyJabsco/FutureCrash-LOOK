import ast
import io
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'look'))
from look import look_renderer as renderer, destination_history as history, media_open
from look import fabric_files as ff
from core import file_transfer
from tools import configure_media


def test_footer_keys_are_bright_and_wrapping_uses_visible_width():
    parts=['H hidden','B clipboard','C Copy To','M Move To','R rename','D delete']
    lines=renderer.action_footer(parts,35)
    assert all(len(renderer.strip_ansi(line))<=35 for line in lines)
    plain=' '.join(renderer.strip_ansi(line) for line in lines)
    assert plain.count('B clipboard')==1 and 'B Copy' not in plain
    assert '⇧' not in plain and renderer.CYAN in lines[0] and renderer.BOLD in lines[0]


def setup_picker(monkeypatch,tmp_path,keys):
    monkeypatch.setattr(renderer.termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(renderer.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(renderer.tty,'setcbreak',lambda fd:None)
    monkeypatch.setattr(renderer.sys,'stdin',Mock(fileno=lambda:0))
    output=io.StringIO(); monkeypatch.setattr(renderer.sys,'stdout',output)
    monkeypatch.setattr(history,'location',lambda:tmp_path/'history.json')
    choices=iter(keys); monkeypatch.setattr(renderer,'read_key',lambda:next(choices))
    return output


def test_picker_starts_common_and_tab_exposes_full_root(tmp_path,monkeypatch):
    output=setup_picker(monkeypatch,tmp_path,['\t','\r'])
    calls=[]
    def browse(dest,common=False):
        calls.append(common)
        rows=[{'name':'Home','path':'/home/jreno'},{'name':'Filesystem /','path':'/'}] if common else [{'name':'etc','path':'/etc'}]
        return {'path':'/','directories':rows}
    monkeypatch.setattr(ff,'browse',browse)
    chosen=renderer._destination_picker(ff.Destination('3090','/'))
    assert str(chosen)=='@3090:/etc' and calls==[True,False]
    assert 'COMMON PLACES' in output.getvalue() and history.recent('3090')[0]['value']=='@3090:/etc'


def test_filesystem_entry_can_descend_from_virtual_common_root(tmp_path,monkeypatch):
    setup_picker(monkeypatch,tmp_path,['\x1b[C','\r'])
    calls=[]
    def browse(dest,common=False):
        calls.append(common)
        return {'path':'/','directories':[{'name':'Filesystem /','path':'/'}] if common else [{'name':'srv','path':'/srv'}]}
    monkeypatch.setattr(ff,'browse',browse)
    assert str(renderer._destination_picker(ff.Destination('3090','/')))=='@3090:/srv'
    assert calls==[True,False]


def test_history_completion_is_node_qualified_and_avoids_network(tmp_path,monkeypatch):
    monkeypatch.setattr(history,'location',lambda:tmp_path/'history.json')
    history.remember('@3090:/run/media/jreno/2TB Storage/Movies')
    history.remember('@m3max-pro:/Volumes/Archive')
    assert len(history.recent('3090'))==1
    monkeypatch.setattr(ff,'browse',lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError('unnecessary remote lookup')))
    assert renderer._complete_path_text('@3090:/run/me')=='@3090:/run/media/jreno/2TB Storage/Movies/'
    assert history.location().stat().st_mode&0o777==0o600


def test_remote_completion_handles_spaces_and_remote_home(tmp_path,monkeypatch):
    monkeypatch.setattr(history,'location',lambda:tmp_path/'history.json')
    calls=[]
    def browse(dest):
        calls.append(str(dest)); return {'directories':[{'name':'2TB Storage','path':'/run/media/2TB Storage'}]}
    monkeypatch.setattr(ff,'browse',browse)
    assert renderer._complete_path_text('@3090:/run/media/2T')=='@3090:/run/media/2TB Storage/'
    assert renderer._complete_path_text('@3090:~/')=='@3090:~/2TB Storage/'
    assert renderer._complete_path_text('@3090:~')=='@3090:~/2TB Storage/'
    assert calls==['@3090:/run/media','@3090:~/','@3090:~']


def test_local_completion_descends_after_trailing_slash(tmp_path,monkeypatch):
    monkeypatch.setattr(history,'location',lambda:tmp_path/'history.json')
    (tmp_path/'A folder').mkdir()
    assert renderer._complete_path_text(str(tmp_path)+'/')==str(tmp_path)+'/A folder/'


def test_common_places_include_existing_media_roots_and_full_filesystem(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',classmethod(lambda cls:tmp_path))
    for name in ('Documents','Downloads','Music'): (tmp_path/name).mkdir()
    state=tmp_path/'.local/share/look'; state.mkdir(parents=True)
    root=tmp_path/'Storage with spaces'; root.mkdir()
    (state/'media_library.json').write_text(json.dumps({'roots':[str(root),'/']}))
    listing=file_transfer.common_places(); paths=[row['path'] for row in listing['directories']]
    assert str(tmp_path) in paths and str(tmp_path/'Downloads') in paths and str(root) in paths
    assert paths.count('/')==1 and listing['mode']=='common'
    assert str(tmp_path/'Videos') not in paths


def test_linux_media_open_bypasses_missing_association_and_quotes_no_shell(monkeypatch,tmp_path):
    monkeypatch.setattr(media_open.sys,'platform','linux')
    monkeypatch.setattr(media_open,'mpv_binary',lambda:'/home/linuxbrew/.linuxbrew/bin/mpv')
    path=tmp_path/'My video.mp4'
    command=media_open.command(path,'system')
    assert command[-2:]==['--',str(path)] and command[0].endswith('/mpv')
    launch=Mock(); monkeypatch.setattr(renderer.subprocess,'Popen',launch)
    assert renderer.open_default(path)==(True,'')
    assert launch.call_args.args[0]==command


def test_preferred_player_and_other_platforms_are_respected(monkeypatch,tmp_path):
    monkeypatch.setattr(media_open.sys,'platform','linux')
    monkeypatch.setattr(media_open.shutil,'which',lambda name:'/usr/bin/vlc' if name=='vlc' else None)
    assert media_open.command(tmp_path/'video.mp4','vlc')==['/usr/bin/vlc',str(tmp_path/'video.mp4')]
    assert media_open.command(tmp_path/'file.pdf','system') is None
    monkeypatch.setattr(media_open.sys,'platform','darwin')
    assert media_open.command(tmp_path/'video.mp4','system') is None


def test_desktop_registration_repairs_missing_defaults_but_keeps_vlc(tmp_path,monkeypatch):
    apps=tmp_path/'applications'; apps.mkdir(); (apps/'vlc.desktop').write_text('[Desktop Entry]\n')
    defaults={'video/mp4':'vlc.desktop','video/webm':'missing.desktop'}; writes=[]
    monkeypatch.setattr(configure_media.shutil,'which',lambda name:'xdg-mime' if name=='xdg-mime' else None)
    def run(args,**kwargs):
        if args[1]=='query': return SimpleNamespace(returncode=0,stdout=defaults.get(args[3],''))
        writes.append(args); defaults[args[3]]=args[2]; return SimpleNamespace(returncode=0,stdout='')
    monkeypatch.setattr(configure_media.subprocess,'run',run)
    configure_media.configure('/home/linuxbrew/.linuxbrew/bin/mpv',tmp_path)
    assert defaults['video/mp4']=='vlc.desktop' and defaults['video/webm']=='look-mpv.desktop'
    assert ' -- %U' in (apps/'look-mpv.desktop').read_text()
    assert not any(args[-1]=='video/mp4' for args in writes)
    writes.clear(); configure_media.configure('/home/linuxbrew/.linuxbrew/bin/mpv',tmp_path)
    assert writes==[]


def test_find_prefers_local_copy_and_marks_other_node_same_path_remote(tmp_path):
    source=Path('look/lk').read_text(); tree=ast.parse(source)
    function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='_file_find_command')
    rows=[{'path':'/same/path','node':'3090','locations':[{'path':'/same/path','node':'3090'}]},
          {'path':'/remote/copy','node':'3090','locations':[{'path':'/remote/copy','node':'3090'},{'path':'/local/copy','node':'m3max-pro'}]}]
    captured=[]
    ns={'_media_fabric_cli':lambda args:{'entries':rows,'local_node':'m3max-pro','errors':[{'node':'offline'}]},
        '_file_find_selector':lambda entries,query,source:captured.append((entries,source)) or 0}
    exec(compile(ast.Module(body=[function],type_ignores=[]),'look/lk','exec'),ns)
    assert ns['_file_find_command'](['ukulele'])==0
    assert rows[0]['local'] is False and rows[1]['local'] is True and rows[1]['path']=='/local/copy'
    assert 'partial, unavailable: offline' in captured[0][1]


def test_new_modules_use_supported_python_grammar():
    for path in ('look/look_renderer.py','look/media_open.py','look/destination_history.py','tools/configure_media.py'):
        ast.parse(Path(path).read_text(),filename=path,feature_version=(3,10))


def test_actual_filter_bars_have_one_clipboard_hint_and_no_shift_letter_symbols():
    tree=ast.parse(Path('look/look_renderer.py').read_text())
    bars=[node.value for node in ast.walk(tree) if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='action_parts' for target in node.targets) and isinstance(node.value,ast.List)]
    found=False
    for bar in bars:
        values=[item.value for item in bar.elts if isinstance(item,ast.Constant) and isinstance(item.value,str)]
        assert sum(value.startswith('B ') for value in values)<=1
        assert not any(value.startswith(('⇧H','⇧F','⇧R','⇧D')) for value in values)
        if 'B clipboard' in values: found=True
    assert found


def test_remote_result_never_opens_same_named_existing_local_file(tmp_path):
    file=tmp_path/'video.mp4'; file.write_bytes(b'local copy is unrelated')
    tree=ast.parse(Path('look/lk').read_text())
    function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='_file_find_selector')
    choices=iter(['\r','Y','q']); copied=[]
    namespace={'Path':Path,'sys':SimpleNamespace(stdin=Mock(isatty=lambda:True,fileno=lambda:0),stdout=Mock(isatty=lambda:True,write=lambda text:None)),
        'termios':SimpleNamespace(tcgetattr=lambda fd:[],tcsetattr=lambda *args:None,TCSADRAIN=0,error=OSError),
        'tty':SimpleNamespace(setcbreak=lambda fd:None),'shutil':SimpleNamespace(get_terminal_size=lambda *args:SimpleNamespace(columns=100,lines=30)),
        '_c':lambda value,*args:value,'_read_tty_key':lambda fd:next(choices),'_copy_value':lambda value:copied.append(value) or True,
        'render':lambda *args:(_ for _ in ()).throw(AssertionError('opened wrong local file'))}
    exec(compile(ast.Module(body=[function],type_ignores=[]),'look/lk','exec'),namespace)
    assert namespace['_file_find_selector']([{'path':str(file),'node':'3090','local':False}],'video','Fabric · partial')==0
    assert copied==['@3090:'+str(file)]
