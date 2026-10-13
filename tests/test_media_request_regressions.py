import importlib.machinery
import importlib.util
import sys
from pathlib import Path

import pytest
from core import intent_normalizer

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def lk(monkeypatch, tmp_path):
    loader = importlib.machinery.SourceFileLoader('lk_media_requests', str(ROOT/'look/lk'))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, loader.name, module)
    loader.exec_module(module)
    monkeypatch.setattr(module, 'STATE_DIR', tmp_path)
    monkeypatch.setattr(module, 'MEDIA_SESSION_FILE', tmp_path/'session.json')
    return module


def catalog():
    return [{'node': node, 'id': f'{node}-{i}', 'path': f'/music/{i}.mp3',
             'artist': 'Talking Heads', 'album': 'Album', 'title': f'Track {i}',
             'bytes': 100+i, 'media_type': 'audio/mpeg'}
            for node in ('3090', 'm3max-pro', 'm4-air') for i in range(12)]


@pytest.mark.parametrize('phrase, count', [
    ('play 6 talking heads songs', 6), ('play a few talking heads', 3),
    ('› play a few talking heads', 3), ('play some Talking Heads', 8),
    ('play six songs by Talking Heads', 6),
    ('queue 6 Talking Heads songs', 6), ('add some more Talking Heads', 8),
])
def test_quantity_is_structured_before_catalog_search(phrase, count):
    intent = intent_normalizer.normalize(phrase)
    assert intent and intent.get('artist', '').casefold() == 'talking heads'
    assert intent['limit'] == count and intent['selection'] == 'random'
    assert 'query' not in intent
    action = 'media.queue' if phrase.startswith(('queue', 'add')) else 'media.play'
    assert intent['action'] == action
    args = intent_normalizer.media_tool(intent)['args']
    assert args['limit'] == count and args['artist'].casefold() == 'talking heads'


def test_artist_count_counts_songs_not_physical_copies(lk, monkeypatch):
    monkeypatch.setattr(lk, '_media_catalog_entries', lambda: (catalog(), {}))
    rows, _ = lk._media_resolve_targets(['some', 'Talking', 'Heads'])
    assert len(rows) == 8
    assert len({row['title'] for row in rows}) == 8
    assert all(len(row['locations']) == 3 for row in rows)


def test_directory_picker_displays_nearest_parent_and_keeps_its_focus(lk, monkeypatch, capsys):
    path = '/System/Volumes/Data/Library/Application Support/Instruments/Pianos/ped_mf.wav'
    row = {'path': path, 'root': '/', 'node': 'm3max-pro'}
    monkeypatch.setattr(lk, '_read_tty_key', lambda fd: '\n')
    picked = lk._media_choose_hide_directory(row, [row], 0)
    assert picked['path'] == str(Path(path).parent)
    output = capsys.readouterr().out
    assert 'Pianos' in output
    assert 'MEDIA ROOT' in output
    assert any('›' in line and 'Pianos' in line for line in output.splitlines())


def test_append_updates_live_mpv_without_replacing_current_track(lk, monkeypatch):
    session = lk.media_core.new_session(catalog()[:1])
    session.update(state='playing', runtime_queue_indices=[0], position=42)
    monkeypatch.setattr(lk, '_media_sync_session', lambda: session)
    monkeypatch.setattr(lk, '_media_mpv_alive', lambda: True)
    monkeypatch.setattr(lk, '_media_mpv_property', lambda name: 1 if name == 'playlist-count' else False)
    monkeypatch.setattr(lk, '_media_entry_source', lambda entry: entry['path'])
    commands = []
    monkeypatch.setattr(lk, '_media_mpv_request', lambda cmd: commands.append(cmd) or {'error': 'success'})
    assert lk._media_queue_append(catalog()[1:3]) == 2
    saved = lk._media_session()
    assert len(saved['queue']) == 3 and saved['runtime_queue_indices'] == [0, 1, 2]
    assert saved['current_index'] == 0 and saved['position'] == 42
    assert any(cmd[0] == 'loadlist' and cmd[-1] == 'append' for cmd in commands)
    assert not any(cmd[0] in {'seek', 'quit'} or 'replace' in cmd for cmd in commands)


@pytest.mark.parametrize('phrase', ['add some more of the artist', 'add some more'])
def test_more_uses_current_artist_host_evidence(lk, phrase):
    session=lk.media_core.new_session(catalog()[:1])
    lk._media_save_session(session)
    intent=lk._lo_media_intent_profile(phrase)
    assert intent['tool']=='media_queue'
    assert intent['args']['artist']=='Talking Heads' and intent['args']['limit']==8


def test_queue_artist_selector_appends_fresh_unique_songs(lk, monkeypatch):
    existing=lk.media_core.new_session(catalog()[:4])
    lk._media_save_session(existing)
    monkeypatch.setattr(lk, '_media_catalog_entries', lambda: (catalog(), {}))
    monkeypatch.setattr(lk, '_media_mpv_alive', lambda: False)
    result=lk._media_tool_queue(artist='Talking Heads',kind='audio',selection='random',limit=6)
    assert result.ok
    saved=lk._media_session()
    assert len(saved['queue'])==10
    assert len({r['title'] for r in saved['queue']})==10


@pytest.mark.parametrize('state', ['stopped','paused'])
def test_append_does_not_autostart_idle_or_paused_queue(lk, monkeypatch, state):
    session=lk.media_core.new_session(catalog()[:1])
    session.update(state=state,runtime_queue_indices=[0])
    monkeypatch.setattr(lk,'_media_sync_session',lambda:session)
    monkeypatch.setattr(lk,'_media_mpv_alive',lambda:True)
    monkeypatch.setattr(lk,'_media_mpv_property',lambda name:1 if name=='playlist-count' else True)
    monkeypatch.setattr(lk,'_media_entry_source',lambda entry:entry['path'])
    commands=[]
    monkeypatch.setattr(lk,'_media_mpv_request',lambda cmd:commands.append(cmd) or {'error':'success'})
    lk._media_queue_append(catalog()[1:2])
    assert len(commands)==1 and commands[0][0]=='loadlist'
    assert lk._media_session()['state']==state


def test_append_runtime_rejection_is_not_reported_as_playable_queue_success(lk, monkeypatch):
    session=lk.media_core.new_session(catalog()[:1])
    session.update(state='playing',runtime_queue_indices=[0])
    monkeypatch.setattr(lk,'_media_sync_session',lambda:session)
    monkeypatch.setattr(lk,'_media_mpv_alive',lambda:True)
    monkeypatch.setattr(lk,'_media_mpv_property',lambda name:1 if name=='playlist-count' else False)
    monkeypatch.setattr(lk,'_media_entry_source',lambda entry:entry['path'])
    monkeypatch.setattr(lk,'_media_mpv_request',lambda cmd:{'error':'failed'})
    monkeypatch.setattr(lk,'_media_query_matches',lambda *args,**kwargs:('artist',catalog()[1:2]))
    result=lk._media_tool_queue('Talking Heads')
    assert not result.ok and 'PLAYER APPEND FAILED' in result.message
    saved=lk._media_session()
    assert len(saved['queue'])==2 and saved['runtime_queue_indices']==[0]


def test_append_missing_source_does_not_shift_later_runtime_queue_indices(lk, monkeypatch):
    session=lk.media_core.new_session(catalog()[:1])
    session.update(state='playing',runtime_queue_indices=[0])
    monkeypatch.setattr(lk,'_media_sync_session',lambda:session)
    monkeypatch.setattr(lk,'_media_mpv_alive',lambda:True)
    monkeypatch.setattr(lk,'_media_mpv_property',lambda name:1 if name=='playlist-count' else False)
    def source(entry):
        if entry['title']=='Track 1': raise FileNotFoundError('offline source')
        return entry['path']
    monkeypatch.setattr(lk,'_media_entry_source',source)
    monkeypatch.setattr(lk,'_media_mpv_request',lambda cmd:{'error':'success'})
    lk._media_queue_append(catalog()[1:3])
    saved=lk._media_session()
    assert saved['runtime_queue_indices']==[0,2] and 'offline source' in saved['runtime_queue_error']


def test_hidden_tracks_are_excluded_before_random_limit(lk, monkeypatch):
    monkeypatch.setattr(lk,'_media_catalog_entries',lambda:(catalog(),{}))
    lk._media_save_visibility({'hidden_paths':['/music/0.mp3'],'hidden_trees':[]})
    rows,_=lk._media_resolve_targets(['6','Talking','Heads','songs'])
    assert len(rows)==6 and all(r['title']!='Track 0' for r in rows)


@pytest.mark.parametrize('phrase', ['play 2 Live Crew', 'play Five for Fighting'])
def test_artist_names_that_start_with_counts_remain_catalog_queries(phrase):
    intent=intent_normalizer.normalize(phrase)
    assert intent['query']==phrase[5:] and 'artist' not in intent


def test_literal_title_keeps_quantity_words_literal():
    intent=intent_normalizer.normalize('play "6 talking heads songs"')
    assert intent['query']=='6 talking heads songs' and intent['match_mode']=='literal'


def test_root_boundary_requires_explicit_confirmation(lk, monkeypatch, capsys):
    row={'path':'/samples/piano.wav','root':'/'}
    keys=iter(['down','\n','n','esc'])
    monkeypatch.setattr(lk,'_read_tty_key',lambda fd:next(keys))
    assert lk._media_choose_hide_directory(row,[row],0) is None
    assert 'hide all 1 catalog items here? Y/N' in capsys.readouterr().out


def test_empty_canonical_queue_does_not_attach_to_unrelated_runtime_playlist(lk, monkeypatch):
    monkeypatch.setattr(lk,'_media_sync_session',lambda:lk.media_core.new_session([]))
    monkeypatch.setattr(lk,'_media_mpv_alive',lambda:True)
    monkeypatch.setattr(lk,'_media_mpv_property',lambda name:3)
    commands=[]
    monkeypatch.setattr(lk,'_media_mpv_request',lambda cmd:commands.append(cmd))
    lk._media_queue_append(catalog()[:1])
    assert commands==[] and lk._media_session()['runtime_queue_error']



def test_random_selector_preserves_locations_of_already_sha_merged_tracks(lk):
    rows=catalog()
    for row in rows: row['digest']='sha256:'+row['title']
    merged=lk.media_core.merge_catalog_entries(rows,local_node='3090')
    selected=lk._media_selection_catalog(merged)
    assert len(selected)==12
    assert all(len(row['locations'])==3 for row in selected)
    assert all({loc['node'] for loc in row['locations']}=={'3090','m3max-pro','m4-air'} for row in selected)


@pytest.mark.parametrize('phrase,count',[('play 6 talking heads songs',6),('› play a few talking heads',3),('play some Talking Heads',8)])
def test_lo_structured_quantity_reaches_player_as_exact_unique_queue(lk,monkeypatch,tmp_path,phrase,count):
    monkeypatch.setattr(lk,'_media_catalog_entries',lambda:(catalog(),{}))
    sessions=[]
    monkeypatch.setattr(lk,'_media_launch_session',lambda session:sessions.append(session) or 0)
    intent=lk._lo_media_intent_profile(phrase)
    result=lk._run_capability_tool(intent['tool'],intent['args'],tmp_path,'power')
    assert result.ok
    assert len(sessions)==1 and len(sessions[0]['queue'])==count
    assert len({row['title'] for row in sessions[0]['queue']})==count


def test_mac_local_disc_requests_run_in_foreground(lk,monkeypatch):
    from look import disc_ui,disc_import
    from unittest.mock import Mock
    monkeypatch.setitem(sys.modules,'disc_ui',disc_ui)
    monkeypatch.setitem(sys.modules,'disc_import',disc_import)
    monkeypatch.setattr(sys,'platform','darwin')
    monkeypatch.setattr(lk,'_media_local_node_names',lambda:{'local','m3max-pro'})
    routed=Mock(return_value={'ok':True});direct=Mock(return_value={'ok':True})
    monkeypatch.setattr(lk,'_media_fabric_cli',routed)
    monkeypatch.setattr(disc_import,'request',direct)
    def run(argv,factory,*args):
        factory('m3max-pro')('scan',{'kind':'cd'})
        factory('3090')('scan',{'kind':'cd'})
        return 0
    monkeypatch.setattr(disc_ui,'main',run)
    assert lk.media(['import'])==0
    direct.assert_called_once_with('scan',{'kind':'cd'})
    assert routed.call_count==1 and '--node' in routed.call_args.args[0] and '3090' in routed.call_args.args[0]


def test_metadata_editor_routes_each_owner_and_reports_partial_failures(lk,monkeypatch,tmp_path):
    from look import media_metadata
    from unittest.mock import Mock
    monkeypatch.setitem(sys.modules,'media_metadata',media_metadata)
    monkeypatch.setattr(lk,'HOME',tmp_path)
    monkeypatch.setattr(lk,'_media_local_node_names',lambda:{'local'})
    rows=[{'id':'one','node':'local','artist':'Old'},{'id':'two','node':'peer','artist':'Old'}]
    direct=Mock(return_value={'ok':True,'entries':[{'id':'one','artist':'New'}]})
    monkeypatch.setattr(media_metadata,'edit',direct)
    remote=Mock(side_effect=RuntimeError('Peer offline'));monkeypatch.setattr(lk,'_media_fabric_cli',remote)
    result=lk._media_edit_rows(rows,{'artist':'New'})
    assert not result['ok'] and result['count']==1 and result['errors']==['peer: Peer offline']
    assert rows[0]['artist']=='New' and rows[1]['artist']=='Old'
    assert direct.call_args.args[1]['entries'][0]['expected']['artist']=='Old'
    assert remote.call_count==1 and remote.call_args.args[0][-1]=='peer'


def test_cli_bulk_edit_requires_explicit_all_and_preserves_individual_titles(lk,monkeypatch,capsys):
    from unittest.mock import Mock
    rows=[{'id':str(n),'path':f'/music/{n}.flac','artist':'Old','title':str(n)} for n in (1,2)]
    monkeypatch.setattr(lk,'_media_catalog_entries',lambda:(rows,{}))
    edited=Mock(return_value={'ok':True,'count':2,'errors':[]});monkeypatch.setattr(lk,'_media_edit_rows',edited)
    assert lk._media_edit_command(['Old','--artist','New'])==1
    edited.assert_not_called()
    assert lk._media_edit_command(['Old','--all','--title','Same'])==1
    edited.assert_not_called()
    assert lk._media_edit_command(['Old','--all','--artist','New'])==0
    assert edited.call_args.args[1]=={'artist':'New'}


def test_metadata_prompt_blank_fields_preserve_each_title(lk,monkeypatch):
    from look import media_metadata
    from unittest.mock import Mock
    monkeypatch.setitem(sys.modules,'media_metadata',media_metadata)
    monkeypatch.setattr(lk.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(lk.tty,'setcbreak',lambda *args:None)
    answers=iter(['s','New Artist','','','','yes'])
    monkeypatch.setattr('builtins.input',lambda label:next(answers))
    edited=Mock(return_value={'ok':True,'count':2,'entries':[],'errors':[]});monkeypatch.setattr(lk,'_media_edit_rows',edited)
    rows=[{'title':'First','artist':'Old'},{'title':'Second','artist':'Old'}]
    assert lk._media_edit_prompt(rows,0,None)['count']==2
    assert edited.call_args.args[1]=={'artist':'New Artist'}


def test_selector_edits_all_marked_rows_and_updates_open_view(lk,monkeypatch):
    import io
    from unittest.mock import Mock
    class Terminal(io.StringIO):
        def isatty(self):return True
        def fileno(self):return 0
    monkeypatch.setattr(sys,'stdin',Terminal())
    monkeypatch.setattr(sys,'stdout',Terminal())
    monkeypatch.setattr(lk.termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(lk.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(lk.tty,'setcbreak',lambda *args:None)
    keys=iter(['A','E','esc']);monkeypatch.setattr(lk,'_read_tty_key',lambda *args:next(keys))
    rows=[{'id':str(n),'path':f'/music/{n}.flac','node':'local','artist':'Old','title':str(n)} for n in (1,2)]
    def edit(chosen,*args):
        return {'count':len(chosen),'entries':[dict(row,artist='New') for row in chosen],'errors':[]}
    edited=Mock(side_effect=edit);monkeypatch.setattr(lk,'_media_edit_prompt',edited)
    assert lk._media_selector(rows)==('none',None)
    assert len(edited.call_args.args[0])==2
    assert all(row['artist']=='New' for row in rows)


@pytest.mark.parametrize('keys,artist',[(['q','\r'],'Queen'),(['b','q','\r'],'BQ Band')])
def test_media_find_lowercase_q_filters_instead_of_quitting(lk,monkeypatch,keys,artist):
    import io
    class Terminal(io.StringIO):
        def isatty(self):return True
        def fileno(self):return 0
    monkeypatch.setattr(sys,'stdin',Terminal());monkeypatch.setattr(sys,'stdout',Terminal())
    monkeypatch.setattr(lk.termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(lk.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(lk.tty,'setcbreak',lambda *args:None)
    sequence=iter(keys);monkeypatch.setattr(lk,'_read_tty_key',lambda *args:next(sequence))
    rows=[{'id':'one','path':'/music/song.flac','node':'local','artist':artist,'title':'Song'},
          {'id':'two','path':'/music/other.flac','node':'local','artist':'Other','title':'Song'}]
    action,selected=lk._media_selector(rows)
    assert action=='play' and len(selected)==1 and selected[0]['artist']==artist


def test_album_and_artist_browser_lowercase_q_is_filter_text(lk,monkeypatch):
    import io
    from look import media_library_ui
    class Terminal(io.StringIO):
        def isatty(self):return True
        def fileno(self):return 0
    monkeypatch.setattr(sys,'stdin',Terminal());monkeypatch.setattr(sys,'stdout',Terminal())
    monkeypatch.setattr(lk.termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(lk.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(lk.tty,'setcbreak',lambda *args:None)
    keys=iter(['q','\r'])
    selected=media_library_ui.choose([{'label':'Queen','entries':[{}]},{'label':'Other','entries':[{}]}],
        'ARTISTS',lambda *args:next(keys),lambda text,width:text)
    assert selected['label']=='Queen'


def test_refresh_discovers_new_album_without_losing_existing_row_objects(lk,monkeypatch,tmp_path):
    monkeypatch.setattr(lk,'HOME',tmp_path)
    old={'node':'local','id':'old','title':'Old title'}
    added={'node':'local','id':'new','artist':'Oscar Peterson','album':'Live From Chicago'}
    monkeypatch.setattr(lk,'_media_catalog_entries',lambda:([dict(old,title='Corrected title'),added],{}))
    rows=[old]
    lk._media_refresh_rows(rows)
    assert rows[0] is old and old['title']=='Corrected title'
    assert rows[1]==added
    lk._media_refresh_rows(rows)
    assert len(rows)==2
    scoped=[old];lk._media_refresh_rows(scoped,discover=False)
    assert scoped==[old]


def test_unavailable_fabric_merges_fresh_local_album_with_cached_remote_music(lk,monkeypatch,tmp_path):
    import json,time
    monkeypatch.setattr(lk,'HOME',tmp_path)
    cache=tmp_path/'.cache/look/fabric-media-catalog.json';cache.parent.mkdir(parents=True)
    cache.write_text(json.dumps({'_look_cached_at':time.time(),'nodes':[{'node':'m3'},{'node':'3090'}],
                                'entries':[{'node':'m3','id':'old'},{'node':'3090','id':'remote'}]}))
    fresh={'id':'new','artist':'The Oscar Peterson Trio'}
    monkeypatch.setattr(lk,'_media_library',lambda:{'entries':[fresh]})
    def offline(*a,**k):raise OSError('fabric unavailable')
    monkeypatch.setattr(lk.urllib.request,'urlopen',offline)
    result=lk._media_fabric_catalog()
    assert result['stale'] and result['locations']==2
    assert {row['id'] for row in result['entries']}=={'new','remote'}
    assert next(row for row in result['entries'] if row['id']=='new')['node']=='m3'
    assert result['catalog_error']=='fabric unavailable'


@pytest.mark.parametrize('compressed', [False, True])
def test_lk_reads_and_caches_live_catalog_response(lk, monkeypatch, tmp_path, compressed):
    import gzip, io, json
    monkeypatch.setattr(lk, 'HOME', tmp_path)
    payload={'nodes':[{'node':'m3'},{'node':'3090'}],
             'entries':[{'node':'m3','id':'local'},{'node':'3090','id':'remote'}]}
    raw=json.dumps(payload).encode()
    response=io.BytesIO(gzip.compress(raw) if compressed else raw)
    response.headers={'Content-Encoding':'gzip'} if compressed else {}
    def fetch(request, timeout):
        assert request.get_header('Accept-encoding')=='gzip'
        return response
    monkeypatch.setattr(lk.urllib.request, 'urlopen', fetch)
    monkeypatch.setattr(lk, '_media_library', lambda: {'entries':[]})
    result=lk._media_fabric_catalog()
    assert result==payload
    cached=json.loads((tmp_path/'.cache/look/fabric-media-catalog.json').read_text())
    assert cached['entries']==payload['entries']


def test_invalid_catalog_falls_back_with_diagnostic(lk, monkeypatch, tmp_path):
    import io
    monkeypatch.setattr(lk, 'HOME', tmp_path)
    monkeypatch.setattr(lk.urllib.request, 'urlopen', lambda *a, **kw: io.BytesIO(b'[]'))
    monkeypatch.setattr(lk, '_media_library', lambda: {'entries':[]})
    result=lk._media_fabric_catalog()
    assert result['fallback'] and result['catalog_error']=='Invalid catalog response'


def test_refresh_removes_old_locations_and_refreshes_owner_health(lk,monkeypatch,tmp_path):
    monkeypatch.setattr(lk,'HOME',tmp_path)
    fresh={'node':'3090','id':'real','path':'/music/real.mp3','title':'New title'}
    monkeypatch.setattr(lk,'_media_catalog_entries',lambda:([fresh],{'nodes':[{'node':'3090','count':1}]}))
    old=dict(fresh,title='Old title');rows=[old,{'node':'3090','id':'deleted'}];meta={'fallback':True}
    lk._media_refresh_rows(rows,catalog_meta=meta)
    assert rows==[fresh] and rows[0] is old
    assert not meta.get('fallback') and meta['nodes'][0]['count']==1


def test_collapsed_sha_keeps_owner_hidden_rules_for_each_copy(lk,monkeypatch):
    monkeypatch.setattr(lk,'_media_visibility',lambda:{})
    rows=[{'node':'3090','id':'hidden','path':'/hidden/song.mp3','digest':'sha256:x',
           'fabric_hidden_by':'/hidden','locations':[
               {'node':'3090','id':'hidden','path':'/hidden/song.mp3','fabric_hidden_by':'/hidden'},
               {'node':'m3','id':'visible','path':'/Music/song.mp3','fabric_hidden_by':''}]}]
    visible=lk._media_collapse(rows)
    assert len(visible)==1 and visible[0]['node']=='m3'
    assert visible[0]['source_count']==1
    assert len(lk._media_collapse(rows,show_all=True,show_hidden=True))==2


def test_partial_fabric_keeps_cached_remote_knowledge_and_marks_owner_offline(lk,monkeypatch,tmp_path):
    import io,json,time
    monkeypatch.setattr(lk,'HOME',tmp_path)
    cache=tmp_path/'.cache/look/fabric-media-catalog.json';cache.parent.mkdir(parents=True)
    cache.write_text(json.dumps({'_look_cached_at':time.time()-60,'entries':[{'node':'3090','id':'remote'}]}))
    payload={'entries':[{'node':'m3','id':'local'}],'nodes':[{'node':'m3','count':1}],
             'errors':[{'node':'3090','error':'sleeping'}]}
    monkeypatch.setattr(lk.urllib.request,'urlopen',lambda *a,**kw:io.BytesIO(json.dumps(payload).encode()))
    result=lk._media_fabric_catalog()
    assert {row['id'] for row in result['entries']}=={'local','remote'}
    assert next(row for row in result['entries'] if row['node']=='3090')['offline']
    owner=next(node for node in result['nodes'] if node['node']=='3090')
    assert owner['cached'] and not owner['online'] and owner['count']==1


def test_forget_root_backs_up_only_catalog_and_keeps_files(lk,monkeypatch,tmp_path):
    import json
    monkeypatch.setattr(lk,'HOME',tmp_path)
    root=tmp_path/'samples';root.mkdir();file=root/'sound.wav';file.write_bytes(b'keep me')
    library=tmp_path/'media_library.json';library.write_text(json.dumps({'roots':[str(root)],'entries':[{'path':str(file),'root':str(root)}]}))
    monkeypatch.setattr(lk,'MEDIA_LIBRARY_FILE',library)
    assert lk._media_scan_command(['--forget',str(root)])==0
    assert file.read_bytes()==b'keep me'
    assert json.loads(library.read_text())['entries']==[]
    backup=next(tmp_path.glob('media_library.before-forget-*'))
    assert len(json.loads(backup.read_text())['entries'])==1


def test_media_find_orders_and_types_use_metadata_not_filesystem(lk):
    rows=[{'id':'a','path':'/a.mp3','title':'Zulu','media_type':'audio/mpeg','mtime':10,'added_at':20,'bytes':100},
          {'id':'b','path':'/b.mkv','title':'Alpha','media_type':'video/matroska','mtime':30,'bytes':200},
          {'id':'c','path':'/c.flac','title':'Beta','format':'flac','mtime':20,'added_at':40,'bytes':50}]
    def ids(mode,reverse=False):return [row['id'] for row in lk._media_find_order(rows,mode,reverse)]
    assert ids(0)==['a','b','c']
    assert ids(1)==['b','c','a']
    assert ids(2)==['b','c','a']
    assert ids(3)==['c','a','b']
    assert ids(4)==['c','a','b']
    assert ids(5)==['b','a','c']
    assert ids(0,True)==['c','b','a'] and ids(1,True)==['a','c','b']
    assert ids(2,True)==['a','c','b'] and ids(3,True)==['a','c','b']
    assert ids(4,True)==['b','a','c']
    rows[0]['sources']=[{'added_at':100,'mtime':200}]
    assert ids(2)[0]=='a' and ids(3)[0]=='a'
    rows[0]['added_at']='nan';rows[0]['sources']=[]
    assert ids(3)[0]=='c'


@pytest.mark.parametrize('keys,expected',[
    (['F','F','\r'],['new']),
    (['G','\r'],['new']),
    (['G','G','\r'],['old']),
    (['F','G','\r'],['old']),
    (['f','\r'],['old']),
    (['F','\t','G','\r'],['new']),
    (['/','F','F','\r'],['new']),
])
def test_media_find_sort_filter_keys_and_selection(lk,monkeypatch,keys,expected):
    import io
    class Terminal(io.StringIO):
        def isatty(self):return True
        def fileno(self):return 0
    output=Terminal()
    monkeypatch.setattr(sys,'stdin',Terminal());monkeypatch.setattr(sys,'stdout',output)
    monkeypatch.setattr(lk.termios,'tcgetattr',lambda fd:[])
    monkeypatch.setattr(lk.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(lk.tty,'setcbreak',lambda *args:None)
    sequence=iter(keys);monkeypatch.setattr(lk,'_read_tty_key',lambda *args:next(sequence))
    monkeypatch.setattr(lk,'_media_visibility',lambda:{'hidden_paths':[],'hidden_trees':[],'fabric_hidden_paths':[],'fabric_hidden_trees':[]})
    rows=[{'id':'old','path':'/old.mp3','title':'Zulu f song','media_type':'audio/mpeg','mtime':10},
          {'id':'new','path':'/new.mkv','title':'Alpha movie','media_type':'video/matroska','mtime':30}]
    action,selected=lk._media_selector(rows)
    assert action=='play' and [row['id'] for row in selected]==expected
    assert 'SORT ' in output.getvalue()


@pytest.mark.parametrize('row,label',[
    ({'path':'/music/a.flac'},'Audio'),
    ({'path':'/movies/PCU.mkv'},'Movie'),
    ({'path':'/television/episode.m4v'},'TV'),
    ({'path':'/Podcasts/episode.mp3'},'Podcast'),
    ({'path':'/clips/a.mp4'},'Video'),
])
def test_media_find_readable_types(lk,row,label):
    assert lk._media_find_type(row)==label


def test_type_sort_groups_albums_across_formats_and_track_artists(lk):
    def row(title,album,track,artist,fmt):
        return {'title':title,'album':album,'track':track,'disc':1,'artist':artist,'album_artist':'Oscar Peterson & Stéphane Grappelli','format':fmt,'path':'/music/'+title+'.'+fmt}
    rows=[row('Z first','Together',1,'Oscar Peterson','flac'),row('A second','Together',2,'Stéphane Grappelli','mp3'),row('Other album','Another',1,'Oscar Peterson','flac')]
    assert [r['title'] for r in lk._media_find_order(rows,4)]==['Other album','Z first','A second']


@pytest.mark.parametrize('width',[33,65,87,120])
def test_media_columns_fit_unicode_and_have_readable_headers(lk,width):
    row={'path':'/music/a.flac','artist':'Stéphane 演奏者','title':'Very long title '*12,'album':'Together','track':2}
    text=lk._strip_ansi(lk._media_find_row(row,width))
    import unicodedata
    cells=sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in {'W','F'} else 1 for c in text)
    assert cells==width and text.startswith('Audio')
    header=lk._strip_ansi(lk._media_find_row({},width,header=True))
    assert 'TYPE' in header and 'TITLE' in header
    if width>=65:assert 'ARTIST' in header and 'ALBUM' in header


def test_apple_tv_remote_error_names_owner_and_does_not_launch(lk,monkeypatch):
    monkeypatch.setattr(lk.sys,'platform','darwin')
    monkeypatch.setattr(lk,'_media_local_node_names',lambda:{'m3'})
    opened,message=lk._media_open_with({'node':'3090','path':'/tv/episode.m4v'},'TV')
    assert not opened and '3090' in message and 'Shift-T does not transfer' in message



def test_mp_transport_panel_has_progress_and_existing_controls(lk):
    snap={'state':'playing','position':30,'duration':60,'entry':{'artist':'Artist','title':'Song'},'index':0,'session':{'queue':[{}]}}
    lines=lk._media_mp_transport_lines(snap,100)
    assert len(lines)==4 and all('\n' not in line for line in lines)
    plain=' '.join(lk._strip_ansi(x) for x in lines)
    assert 'NOW PLAYING' in plain and 'PLAYING' in plain and 'Song' in plain and 'Queue 1/1' in plain
    assert '=' in lines[2] and 'space' in plain and 'seek' in plain
    assert len(lk._media_mp_transport_lines(None,72))==4


def test_media_find_image_toggle_keeps_filter_selection(lk,monkeypatch):
    import io
    rows=[{'id':'1','path':'/music/a.flac','title':'Alpha'}]
    monkeypatch.setattr(lk.sys,'stdin',type('Input',(object,),{'isatty':lambda self:True,'fileno':lambda self:0})())
    out=io.StringIO();out.isatty=lambda:True;monkeypatch.setattr(lk.sys,'stdout',out)
    monkeypatch.setattr(lk.termios,'tcgetattr',lambda fd:[]);monkeypatch.setattr(lk.termios,'tcsetattr',lambda *a:None);monkeypatch.setattr(lk.tty,'setcbreak',lambda fd:None)
    keys=iter(['M','\t','\r']);monkeypatch.setattr(lk,'_read_tty_key',lambda *a:next(keys))
    action,selected=lk._media_selector(rows)
    assert action=='play' and selected[0]['id']=='1'
    assert 'Preview: ASCII' in out.getvalue()


def test_remote_app_copy_verifies_and_keeps_only_on_request(lk,monkeypatch,tmp_path):
    import io
    import media_storage
    payload=b'original protected movie bytes'
    class Response(io.BytesIO):
        headers={'Content-Length':str(len(payload))}
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    monkeypatch.setenv('HOME',str(tmp_path))
    monkeypatch.setattr(lk,'_media_local_node_names',lambda:{'local','mac'})
    monkeypatch.setattr(lk.urllib.request,'urlopen',lambda *a,**k:Response(payload))
    monkeypatch.setattr(lk,'MEDIA_LIBRARY_FILE',tmp_path/'library.json')
    answers=iter(['t','y']);monkeypatch.setattr('builtins.input',lambda *a:next(answers))
    path,message=lk._media_copy_for_app({'node':'server','id':'film','path':'/movies/Film.m4v'})
    assert path.read_bytes()==payload and message=='Copied locally'
    assert not lk.MEDIA_LIBRARY_FILE.exists()
    assert not (tmp_path/'Media').exists()
    answers=iter(['k','y']);monkeypatch.setattr('builtins.input',lambda *a:next(answers))
    path,message=lk._media_copy_for_app({'node':'server','id':'film','path':'/movies/Film.m4v'})
    assert path.is_relative_to(tmp_path/'Media/movies')
    assert any(row['path']==str(path) for row in lk._media_library()['entries'])


def test_remote_app_copy_rejects_truncation(lk,monkeypatch,tmp_path):
    import io
    class Response(io.BytesIO):
        headers={'Content-Length':'100'}
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    monkeypatch.setenv('HOME',str(tmp_path))
    monkeypatch.setattr(lk,'_media_local_node_names',lambda:{'local'})
    monkeypatch.setattr(lk.urllib.request,'urlopen',lambda *a,**k:Response(b'partial'))
    answers=iter(['t','y']);monkeypatch.setattr('builtins.input',lambda *a:next(answers))
    path,message=lk._media_copy_for_app({'node':'server','id':'film','path':'/Film.m4v'})
    assert path is None and 'Incomplete' in message
    assert not list(tmp_path.rglob('*.m4v')) and not list(tmp_path.rglob('.copy-*'))


def test_mp_sort_actions_preserve_queue_order():
    source=(ROOT/'look/lk').read_text().split('def media_mp(initial_query=""):',1)[1]
    assert 'next_key=(mode,query,sort_mode,reverse_sort)' in source
    assert 'if mode=="library":visible=_media_find_order' in source
    assert 'key not in "ABCDLQJKERMFG"' in source
    assert 'Queue order follows playback' in source


def test_remote_video_thumbnail_does_not_reuse_opening_frame_cache(lk,monkeypatch,tmp_path):
    import hashlib,io
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    monkeypatch.setattr(lk,'_media_local_node_names',lambda:{'local'})
    row={'node':'server','id':'movie','path':'/Movie.mkv','mtime':12}
    folder=tmp_path/'.cache/look/media-art/remote';folder.mkdir(parents=True)
    old=hashlib.sha256(b'server|movie|/Movie.mkv|12').hexdigest()[:28]
    (folder/(old+'.jpg')).write_bytes(b'old black frame')
    assert lk._media_remote_cover_path(row,fetch=False) is None
    monkeypatch.setattr(lk.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(b'fresh later frame'))
    fresh=lk._media_remote_cover_path(row)
    assert fresh.read_bytes()==b'fresh later frame'
    assert fresh!=folder/(old+'.jpg')
    assert lk._media_remote_cover_path(row,fetch=False)==fresh


def test_audio_stream_stays_headless_and_hides_old_mpv_cover(lk,monkeypatch):
    monkeypatch.setattr(lk,'_media_mpv_binary',lambda:'mpv')
    monkeypatch.setattr(lk,'_media_mpv_alive',lambda:True)
    monkeypatch.setattr(lk,'_media_reuse_needs_visible_restart',lambda video:False)
    monkeypatch.setattr(lk,'_media_wait_for_mpv_loaded',lambda:True)
    monkeypatch.setattr(lk,'_media_pause_playing_system',lambda:None)
    calls=[]
    monkeypatch.setattr(lk,'_media_mpv_request',lambda cmd:calls.append(cmd) or {'error':'success'})
    session=lk.media_core.new_session([{'title':'Music','path':'/audio.mp4','media_type':'audio/mp4'}])
    assert not lk._media_queue_has_video(session['queue'])
    assert lk._media_launch_stream('http://localhost/music','Music',session)==0
    assert calls.index(['set_property','audio-display','no'])<calls.index(['loadfile','http://localhost/music','replace'])
    assert ['set_property','force-window','no'] in calls
    assert lk._media_session()['presentation']=='audio'


def test_fabric_care_tool_authority_and_read_only_profile(lk,monkeypatch):
    import io,json
    calls=[]
    def request(req,**kwargs):
        calls.append(json.loads(req.data));return io.BytesIO(json.dumps({'nodes':[],'releases_match':True}).encode())
    monkeypatch.setattr(lk.urllib.request,'urlopen',request)
    lk._fabric_care_tool('fabric_status',{},'conservative','check our fabric')
    with pytest.raises(PermissionError):lk._fabric_care_tool('fabric_maintain',{'operation':'backup'},'workspace','explain fabric backups')
    with pytest.raises(PermissionError):lk._fabric_care_tool('fabric_maintain',{'operation':'backup'},'conservative','back up our fabric')
    with pytest.raises(PermissionError):lk._fabric_care_tool('fabric_maintain',{'operation':'sync','source':'other'},'workspace','update all computers from this computer')
    lk._fabric_care_tool('fabric_maintain',{'operation':'sync','source':'local'},'workspace','update all computers from this computer')
    assert len(calls)==2 and calls[-1]['source']=='local'


def test_fabric_care_oneshot_does_not_need_model(lk,monkeypatch,capsys):
    import io,json
    monkeypatch.setattr(lk.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(json.dumps({'nodes':[],'releases_match':True}).encode()))
    assert lk.ollama_chat(initial_prompt='check our fabric',access_profile='workspace',one_shot=True)==0
    assert 'Fabric check' in capsys.readouterr().out


def test_shared_engine_care_has_fabric_provenance(lk,monkeypatch,tmp_path):
    import io,json
    from look import lo_engine
    monkeypatch.setattr(lo_engine,'_load_core',lambda:lk)
    monkeypatch.setattr(lo_engine,'_load_web_key',lambda:None)
    monkeypatch.setattr(lk.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(json.dumps({'nodes':[],'releases_match':True}).encode()))
    result=lo_engine.chat_once('check our fabric',workspace=str(tmp_path))
    assert result['provenance']['edge']=='FABRIC'
    assert result['provenance']['confidence']=='OBSERVED'
    assert 'Fabric check' in result['text']


def test_editor_routes_every_copy_with_its_own_expected_values(lk,monkeypatch,tmp_path):
    import json
    from unittest.mock import Mock
    from look import media_metadata
    monkeypatch.setitem(sys.modules,'media_metadata',media_metadata)
    monkeypatch.setattr(lk,'HOME',tmp_path)
    monkeypatch.setattr(lk,'_media_local_node_names',lambda:{'local'})
    rows=[{'id':'a','node':'owner-a','title':'Original','locations':[
        {'id':'a','node':'owner-a','title':'Original','episode':1},
        {'id':'b','node':'owner-b','title':'Old copy','episode':None}]}]
    def route(args):
        body=json.loads(args[1]);item=body['entries'][0]
        return {'ok':True,'entries':[{'id':item['id'],'title':'Corrected','episode':2}]}
    routed=Mock(side_effect=route);monkeypatch.setattr(lk,'_media_fabric_cli',routed)
    result=lk._media_edit_rows(rows,{'title':'Corrected','episode':2})
    assert result['count']==2 and routed.call_count==2
    bodies=[json.loads(call.args[0][1]) for call in routed.call_args_list]
    assert [body['entries'][0]['expected']['episode'] for body in bodies]==[1,None]
    assert all(row['title']=='Corrected' for row in rows[0]['locations'])


def test_individual_tv_edit_reviews_distinct_titles_before_writing(lk,monkeypatch):
    from unittest.mock import Mock
    monkeypatch.setattr(lk.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(lk.tty,'setcbreak',lambda *args:None)
    rows=[{'id':str(n),'title':'Unnamed '+str(n),'media_type':'video/mp4'} for n in (1,2)]
    answers=iter(['i','Series','1','episode','First','1','Series','1','episode','Second','2','y'])
    monkeypatch.setattr('builtins.input',lambda prompt:next(answers))
    edited=Mock(return_value={'ok':True,'count':1,'entries':[],'errors':[]})
    monkeypatch.setattr(lk,'_media_edit_rows',edited)
    assert lk._media_edit_prompt(rows,0,None)['count']==2
    assert [call.args[1]['title'] for call in edited.call_args_list]==['First','Second']
    assert [call.args[1]['episode'] for call in edited.call_args_list]==[1,2]


def test_individual_editor_cancels_before_any_write(lk,monkeypatch):
    from unittest.mock import Mock
    monkeypatch.setattr(lk.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(lk.tty,'setcbreak',lambda *args:None)
    answers=iter(['i','','','','First','1','','','','Second','2','n'])
    monkeypatch.setattr('builtins.input',lambda label:next(answers))
    edited=Mock();monkeypatch.setattr(lk,'_media_edit_rows',edited)
    rows=[{'id':str(n),'media_type':'video/mp4','title':'Old'} for n in (1,2)]
    assert lk._media_edit_prompt(rows,0,None)['count']==0
    edited.assert_not_called()


def test_metadata_field_prefills_standard_editor_and_escape_cancels(lk,monkeypatch):
    from unittest.mock import Mock
    from look import look_renderer
    monkeypatch.setitem(sys.modules,'look_renderer',look_renderer)
    monkeypatch.setattr(lk.sys.stdin,'isatty',lambda:True)
    monkeypatch.setattr(lk.sys.stdout,'isatty',lambda:True)
    editor=Mock(return_value=('Episode 12',False))
    monkeypatch.setattr(look_renderer,'prompt_line',editor)
    assert lk._media_edit_field('Episode / video title','Episode 11')=='Episode 12'
    editor.assert_called_once_with('Episode / video title › ',initial='Episode 11')
    editor.return_value=('',True)
    with pytest.raises(KeyboardInterrupt):lk._media_edit_field('TV series','Show')


def test_prefilled_tv_editor_only_saves_changed_fields(lk,monkeypatch,capsys):
    from unittest.mock import Mock
    monkeypatch.setattr(lk.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(lk.tty,'setcbreak',lambda *args:None)
    rows=[{'id':'one','media_type':'video/mp4','series':'A Show','season':2,
           'content_kind':'episode','title':'Episode 11','episode':11}]
    def field(label,initial):
        return 'Episode 12' if label=='Episode / video title' else initial
    prompt=Mock(side_effect=field);monkeypatch.setattr(lk,'_media_edit_field',prompt)
    monkeypatch.setattr('builtins.input',lambda label:'y')
    edited=Mock(return_value={'ok':True,'count':1,'entries':[],'errors':[]})
    monkeypatch.setattr(lk,'_media_edit_rows',edited)
    assert lk._media_edit_prompt(rows,0,None)['count']==1
    assert [call.args[1] for call in prompt.call_args_list]==['A Show','2','episode','Episode 11','11']
    assert edited.call_args.args[1]=={'title':'Episode 12'}
    output=capsys.readouterr().out
    assert '1/5 · TV series' in output and '5/5 · Episode number' in output


def test_accepting_all_prefilled_values_does_not_write(lk,monkeypatch):
    from unittest.mock import Mock
    monkeypatch.setattr(lk.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(lk.tty,'setcbreak',lambda *args:None)
    monkeypatch.setattr(lk,'_media_edit_field',lambda label,initial:initial)
    edited=Mock();monkeypatch.setattr(lk,'_media_edit_rows',edited)
    assert lk._media_edit_prompt([{'title':'Keep me','artist':'Artist'}],0,None)['count']==0
    edited.assert_not_called()


def test_tv_rows_show_series_and_episode_without_changing_music_metadata(lk):
    row={'media_type':'video/mp4','series':'A Comedy','season':1,'episode':1,
         'content_kind':'episode','title':'First episode','artist':'','album':''}
    assert lk._media_row_label(row)=='A Comedy — First episode · Season 1 · Ep 1'
    rendered=lk._strip_ansi(lk._media_find_row(row,120))
    assert 'A Comedy' in rendered and 'Season 1' in rendered and 'Ep 1' in rendered
    assert rendered.startswith('TV')
    assert row['artist']=='' and row['album']=='' and row['title']=='First episode'
    label=lk._media_row_label(row)
    assert lk._strip_ansi(lk._media_styled_row_label(row,label))==label
    music={'artist':'Artist','album':'Album','title':'Song','track':3}
    assert lk._media_row_label(music)=='Artist — 03 Song · Album'
    movie={'media_type':'video/mp4','category':'movies','title':'A Movie'}
    assert lk._media_row_label(movie)=='A Movie'


def test_tv_type_sort_groups_series_seasons_and_episodes(lk):
    rows=[{'title':'Later','series':'Show','season':2,'episode':1,'media_type':'video/mp4'},
          {'title':'Z first','series':'Show','season':1,'episode':1,'media_type':'video/mp4'},
          {'title':'A second','series':'Show','season':1,'episode':2,'media_type':'video/mp4'},
          {'title':'Unknown','artist':'Show','album':'Legacy','category':'tv','media_type':'video/mp4'}]
    assert [r['title'] for r in lk._media_find_order(rows,4)]==['Unknown','Z first','A second','Later']
    special={'series':'Show','season':0,'episode':2,'content_kind':'special'}
    assert lk._media_display_groups(special)==('Show','Season 0 · Ep 2 · Special')
