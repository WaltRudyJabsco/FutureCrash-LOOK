import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'look'))
import web_desk as web


@pytest.mark.parametrize('bad',['','javascript:alert(1)','file:///etc/passwd','https://user:pass@example.com','https://example.com/\x1b[2J','https://example.com/a b','https://example.com:abc'])
def test_addresses_reject_unsafe_or_ambiguous_inputs(bad):
    with pytest.raises(ValueError):web.address(bad)


def test_search_and_markdown_keep_input_inert():
    assert web.address('example.org/read')=='https://example.org/read'
    assert 'q=hello+%26+world' in web.search_url('hello & world')
    assert web.note_link({'title':'A [book]','url':'https://example.org/a(b)'})=='[A \\[book\\]](https://example.org/a%28b%29)'


def test_bookmarks_roundtrip_and_invalid_rows_are_skipped(tmp_path,monkeypatch):
    monkeypatch.setattr(web,'folder',lambda:tmp_path)
    state={'browser':'lynx','bookmarks':[{'title':'演奏者','url':'https://example.org'}]}
    web.save_state(state)
    assert web.load_state()==state
    state['bookmarks'].append({'title':'unsafe','url':'javascript:alert(1)'})
    web.save_state(state)
    assert len(web.load_state()['bookmarks'])==1


def test_home_page_escapes_bookmarks_and_uses_active_palette(monkeypatch):
    monkeypatch.setenv('LOOK_TERMINAL_THEME','paper')
    text=web.home_page({'bookmarks':[{'title':'<script>bad</script>','url':'https://example.org/?a=1&b=2'}]})
    assert '<script>' not in text and '&lt;script&gt;' in text
    assert '#f6f1e7' in text and '#201e1a' in text
    assert 'f → letters' in text


@pytest.mark.parametrize('name',['w3m','lynx','links','links2','chawan','qutebrowser'])
def test_launch_uses_argument_list_and_leaves_personal_configs_owned(name,monkeypatch):
    run=Mock(return_value=Mock(returncode=0));monkeypatch.setattr(web.subprocess,'run',run)
    url='https://example.org/?q=$(touch-nope);other=1'
    assert web.launch(name,'/bin/browser',url)==0
    args=run.call_args.args[0]
    assert args[0]=='/bin/browser' and args[-1]==url
    assert run.call_args.kwargs=={'check':False}
    if name=='lynx':assert '-number_links=off' in args
    if name in {'links','links2'}:assert '-html-numbered-links' in args
    if name in {'qutebrowser','chawan'}:assert args==['/bin/browser',url]


def test_native_style_does_not_override_appearance(monkeypatch):
    run=Mock(return_value=Mock(returncode=0));monkeypatch.setattr(web.subprocess,'run',run)
    web.launch('w3m','w3m','https://example.org',False)
    args=run.call_args.args[0]
    assert args[:3]==['w3m','-o','display_link_number=0']
    assert len(args)==6 and args[-1]=='https://example.org'


def test_missing_browser_has_actionable_message(monkeypatch,capsys,tmp_path):
    monkeypatch.setattr(web,'discover',lambda:{})
    monkeypatch.setattr(web,'folder',lambda:tmp_path)
    assert web.main(['https://example.org'])==1
    assert 'lk web list' in capsys.readouterr().err


def test_help_never_launches_browser():
    p=subprocess.run([sys.executable,str(ROOT/'look/lk'),'web','--help'],capture_output=True,text=True,timeout=5)
    assert p.returncode==0 and '--browser' in p.stdout and '--native-style' in p.stdout


def test_desk_handoff_and_return_in_real_terminal(tmp_path):
    import os,pty,select,time,fcntl,termios,struct
    executable=tmp_path/'browser'
    executable.write_text('#!'+sys.executable+'\nimport sys\nfrom pathlib import Path\nPath('+repr(str(tmp_path/'launched'))+').write_text(sys.argv[-1])\n')
    executable.chmod(0o755)
    script="import sys;sys.path.insert(0,"+repr(str(ROOT/'look'))+");import web_desk;from importlib.machinery import SourceFileLoader;lk=SourceFileLoader('lk_web_test',"+repr(str(ROOT/'look/lk'))+").load_module();web_desk.discover=lambda:{'w3m':"+repr(str(executable))+"};raise SystemExit(web_desk.main([],read_key=lk._read_tty_key))"
    master,slave=pty.openpty()
    fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',24,72,0,0))
    process=subprocess.Popen([sys.executable,'-c',script],stdin=slave,stdout=slave,stderr=slave,env={**os.environ,'HOME':str(tmp_path),'LOOK_TERMINAL_THEME':'paper'})
    output=bytearray()
    def until(phrase):
        deadline=time.monotonic()+5
        while phrase not in output and time.monotonic()<deadline:
            if select.select([master],[],[],.1)[0]:output.extend(os.read(master,65536))
        assert phrase in output,output.decode('utf8','replace')
    try:
        until(b'READING DESK')
        os.write(master,b'\r')
        until(b'Back at your reading desk')
        assert (tmp_path/'launched').read_text()=='https://news.google.com/'
        os.write(master,b'q')
        assert process.wait(timeout=5)==0
        assert termios.tcgetattr(slave)[3] & termios.ICANON
    finally:
        if process.poll() is None:process.kill();process.wait()
        os.close(master);os.close(slave)


def test_generated_notebook_link_is_openable_by_notebook_parser():
    import notebook_markdown
    row={'title':'A [book]','url':'https://example.org/a(b)'}
    links=notebook_markdown.extract_links(web.note_link(row))
    assert len(links)==1 and links[0][1]=='https://example.org/a%28b%29'

@pytest.mark.parametrize('name',['w3m','lynx','links','links2'])
@pytest.mark.parametrize('tags',[False,True])
def test_tag_preference_is_explicit_and_invocation_only(name,tags,monkeypatch,tmp_path):
    monkeypatch.setenv('W3M_DIR',str(tmp_path))
    captured=[]
    def run(args,**kwargs):
        captured.extend(args)
        if name=='w3m':
            path=Path(next(a.split('=',1)[1] for a in args if a.startswith('keymap_file=')))
            assert 'keymap M-h COMMAND' in path.read_text()
            assert 'keymap M-j LINK_N' in path.read_text()
        return Mock(returncode=0)
    monkeypatch.setattr(web.subprocess,'run',run)
    web.launch(name,'browser','https://example.org',tags=tags)
    if name=='w3m':assert 'display_link_number='+str(int(tags)) in captured
    elif name=='lynx':assert '-number_links='+('on' if tags else 'off') in captured
    else:assert captured[captured.index('-html-numbered-links')+1]==str(int(tags))
    assert not list(tmp_path.iterdir())


def test_w3m_overlay_preserves_custom_keymap_and_config(tmp_path,monkeypatch):
    root=tmp_path/'personal';root.mkdir()
    config=root/'config';config.write_text('keymap_file alternate\n')
    original=root/'alternate';original.write_text('keymap z NEXT_PAGE\n')
    monkeypatch.setenv('W3M_DIR',str(root))
    overlay=web.w3m_keymap(tmp_path)
    assert overlay.read_text().startswith(original.read_text())
    assert config.read_text()=='keymap_file alternate\n'
    assert original.read_text()=='keymap z NEXT_PAGE\n'


def test_tags_preference_roundtrips_without_legacy_migration(tmp_path,monkeypatch):
    monkeypatch.setattr(web,'folder',lambda:tmp_path)
    assert not web.load_state().get('tags',False)
    data={'browser':'w3m','bookmarks':[],'tags':True}
    web.save_state(data)
    assert web.load_state()==data


def test_home_note_migrates_once_and_remains_notebook_authority(tmp_path,monkeypatch):
    from notebook_core import Notebook
    store=Notebook(tmp_path/'notes',origin='test')
    monkeypatch.setattr(web,'folder',lambda:tmp_path/'web')
    state={'browser':'w3m','bookmarks':[{'title':'My bookmark','url':'https://example.org'}]}
    row=web.home_note(state,store)
    assert 'My bookmark' in row['body'] and state['home_note']==row['id']
    store.change(row['id'],{'body':'# My desk\n\n[Only this](https://example.net)'},expected=row['revision'])
    current=web.home_note(web.load_state(),store)
    assert current['body'].startswith('# My desk')
    assert len(store.list())==1
    assert state['bookmarks'][0]['title']=='My bookmark'
    exported=web.home_page(state,current)
    assert 'My desk' in exported and 'https://example.net' in exported
    assert 'https://archive.org/' not in exported


def test_deleted_home_is_not_silently_replaced(tmp_path,monkeypatch):
    from notebook_core import Notebook
    store=Notebook(tmp_path/'notes',origin='test')
    monkeypatch.setattr(web,'folder',lambda:tmp_path/'web')
    state={'bookmarks':[]}
    row=web.home_note(state,store)
    store.change(row['id'],{'status':'deleted'},expected=row['revision'])
    assert web.home_note(state,store) is None
    assert len(store.list())==0
    assert web.home_note(state,store,replace_missing=True)['id']!=row['id']


def test_export_does_not_turn_local_or_note_links_into_web_addresses(monkeypatch):
    body='# <script>\n[Local](relative/path)\n[Note](note:'+'a'*32+')\n[Bad](javascript:alert(1))\n[Good](https://example.org/)'
    text=web.home_page({'bookmarks':[]},{'body':body})
    assert 'href="https://relative/' not in text
    assert 'href="javascript:' not in text and 'href="https://note:' not in text
    assert 'href="https://example.org/"' in text and '&lt;script&gt;' in text


def test_navigation_translation_leaves_unmodified_input_and_utf8_unchanged():
    original='café'.encode()+b'\x1b[A\x1b[D\x1bh'
    assert web.navigation_bytes(original)==original
    assert web.navigation_bytes(b'\x1b[1;2A\x1b[1;2B\x1b[1;2D\x1b[1;2C')==b'\x1b[5~\x1b[6~\x1b[H\x1b[F'


def test_w3m_bridge_handles_fragmented_shift_keys_and_restores_terminal(tmp_path):
    import os,pty,select,time,fcntl,termios,struct
    child=tmp_path/'child.py';result=tmp_path/'input.bin'
    child.write_text('import os,tty,sys\nfrom pathlib import Path\ntty.setraw(0)\nprint("READY",flush=True)\ndata=b""\nwhile not data.endswith(b"END"):\n data+=os.read(0,4096)\nPath(sys.argv[1]).write_bytes(data)\n')
    script='import sys;sys.path.insert(0,'+repr(str(ROOT/'look'))+');import web_desk;raise SystemExit(web_desk.run_w3m([sys.executable,'+repr(str(child))+','+repr(str(result))+']))'
    master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',24,72,0,0))
    proc=subprocess.Popen([sys.executable,'-c',script],stdin=slave,stdout=slave,stderr=slave)
    try:
        output=b'';deadline=time.monotonic()+5
        while b'READY' not in output and time.monotonic()<deadline:
            if select.select([master],[],[],.1)[0]:output+=os.read(master,65536)
        assert b'READY' in output
        os.write(master,b'\x1b[1;');time.sleep(.01)
        os.write(master,b'2B\x1b[1;2A\x1b[1;2D\x1b[1;2C'+ 'café'.encode()+b'\x1b[AEND')
        assert proc.wait(timeout=5)==0
        assert result.read_bytes()==b'\x1b[6~\x1b[5~\x1b[H\x1b[F'+'café'.encode()+b'\x1b[AEND'
        assert termios.tcgetattr(slave)[3]&termios.ICANON
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
        os.close(master);os.close(slave)


def test_desk_can_choose_edit_and_bookmark_an_existing_note(tmp_path,monkeypatch):
    import io,os
    import notebook
    from notebook_core import Notebook
    store=Notebook(tmp_path/'notes',origin='test')
    other=store.create('Research\n\n[Article](https://example.org)',project='Research')['note']
    monkeypatch.setattr(web,'folder',lambda:tmp_path/'web')
    state={'bookmarks':[]}
    web.home_note(state,store)
    monkeypatch.setattr(notebook,'Notebook',lambda:store)
    monkeypatch.setattr(notebook,'choose_note',lambda *a:web.note_record(store,other))
    monkeypatch.setattr(notebook,'nudge_sync',lambda:None)
    def edit(store,row,*a):
        store.change(row['id'],{'body':row['body']+'\nMy annotation'},expected=row['revision'])
        return 'saved'
    monkeypatch.setattr(notebook,'quick_edit',edit)
    class Terminal(io.StringIO):
        def fileno(self):return 0
    monkeypatch.setattr(sys,'stdin',Terminal());monkeypatch.setattr(sys,'stdout',Terminal())
    monkeypatch.setattr(web.termios,'tcgetattr',lambda *a:[])
    monkeypatch.setattr(web.termios,'tcsetattr',lambda *a:None)
    monkeypatch.setattr(web.tty,'setcbreak',lambda *a:None)
    import look_renderer
    answers=iter([('https://example.net',False),('New bookmark',False)])
    monkeypatch.setattr(look_renderer,'prompt_line',lambda *a,**kw:next(answers))
    keys=iter(['n','e','a','q'])
    assert web.desk(state,{},lambda *a:next(keys),True)==0
    row=web.note_record(store,other)
    assert state['home_note']==other
    assert 'My annotation' in row['body'] and '[New bookmark](https://example.net)' in row['body']
