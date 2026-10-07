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
