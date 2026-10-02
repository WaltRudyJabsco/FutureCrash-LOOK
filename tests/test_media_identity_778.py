from pathlib import Path
import importlib.machinery, importlib.util, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core import node

loader=importlib.machinery.SourceFileLoader('lk778',str(ROOT/'look/lk'))
spec=importlib.util.spec_from_loader('lk778',loader)
lk=importlib.util.module_from_spec(spec); loader.exec_module(lk)


def test_system_owner_keyword_executes_and_propagates(monkeypatch):
    monkeypatch.setattr(lk.platform,'system',lambda:'Darwin')
    seen=[]
    monkeypatch.setattr(lk,'_media_macos_owner',lambda *,include_paused_owner=True: seen.append(include_paused_owner) or None)
    assert lk._media_system_owner(include_paused_owner=False) is None
    assert lk._media_system_owner(include_paused_owner=True) is None
    assert seen == [False, True]


def test_remote_media_source_carries_catalog_id_and_catalog_path(monkeypatch):
    monkeypatch.setattr(lk,'_media_local_node_names',lambda:{'m4-air'})
    entry={'node':'3090','id':'abc123','path':'/srv/music/Talking Heads/track.jpg'}
    url=lk._media_entry_source(entry)
    assert 'node=3090' in url and 'id=abc123' in url
    assert 'path=%2Fsrv%2Fmusic%2FTalking+Heads%2Ftrack.jpg' in url


def test_local_media_path_recovery_is_catalog_bounded(tmp_path, monkeypatch):
    media=tmp_path/'song.mp3'; media.write_bytes(b'abc')
    rows=[{'id':'new-id','path':str(media),'media_type':'audio/mpeg'}]
    monkeypatch.setattr(node,'_read_media_library',lambda:{'entries':rows})
    row,path=node._local_media_entry('old-id',str(media))
    assert row['id']=='new-id' and path==media
    outside=tmp_path/'secret.mp3'; outside.write_bytes(b'nope')
    try:
        node._local_media_entry('old-id',str(outside))
    except FileNotFoundError:
        pass
    else:
        raise AssertionError('path hint must not escape current media catalog')


def test_proxy_forwards_path_locator_and_range_contract():
    src=(ROOT/'core/node.py').read_text()
    assert 'params={"id":entry_id,"path":path_hint}' in src
    assert 'params["representation"]="browser"' in src
    assert 'headers["Range"]=self.headers.get("Range")' in src
    assert '_local_media_entry(entry_id,path_hint)' in src
