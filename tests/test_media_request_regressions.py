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
    answers=iter(['New Artist','','','','yes'])
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
