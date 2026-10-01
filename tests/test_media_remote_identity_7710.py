from pathlib import Path
import importlib.util
import json
import sys

ROOT=Path(__file__).resolve().parents[1]


def _load_node(name='fcl_node_7710_test'):
    core=ROOT/'core'
    sys.path.insert(0,str(core))
    spec=importlib.util.spec_from_file_location(name,core/'node.py')
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod


def test_source_advertises_and_resolves_same_id_for_legacy_idless_row(tmp_path,monkeypatch):
    node=_load_node()
    media=tmp_path/'Talking Heads'/'Little Creatures'/'Wild Wild Life.mp3'
    media.parent.mkdir(parents=True)
    media.write_bytes(b'fabric-media')
    library=tmp_path/'media_library.json'
    library.write_text(json.dumps({'entries':[{'path':str(media),'media_type':'audio/mpeg'}]}))
    monkeypatch.setattr(node,'LOOK_MEDIA_LIBRARY',library)
    monkeypatch.setattr(node,'identity',lambda:{'name':'3090'})

    catalog=node._local_media_catalog()
    assert len(catalog['entries'])==1
    advertised=catalog['entries'][0]
    assert advertised['id']

    row,path=node._local_media_entry(advertised['id'])
    assert path==media
    assert str(row['path'])==str(media)


def test_source_id_derivation_matches_look_media_core(tmp_path):
    node=_load_node('fcl_node_7710_id_test')
    sys.path.insert(0,str(ROOT/'look'))
    import media_core
    media=tmp_path/'Artist'/'Album'/'Song.mp3'
    media.parent.mkdir(parents=True)
    media.write_bytes(b'x')
    row=media_core.entry_from_path(media)
    assert node._media_catalog_id(str(media.resolve())) == row['id']


def test_path_repair_remains_catalog_bounded(tmp_path,monkeypatch):
    node=_load_node('fcl_node_7710_path_test')
    media=tmp_path/'library'/'song.mp3'; media.parent.mkdir(); media.write_bytes(b'ok')
    outside=tmp_path/'secret.mp3'; outside.write_bytes(b'no')
    library=tmp_path/'media_library.json'
    library.write_text(json.dumps({'entries':[{'path':str(media)}]}))
    monkeypatch.setattr(node,'LOOK_MEDIA_LIBRARY',library)
    try:
        node._local_media_entry('missing',str(outside))
    except FileNotFoundError:
        pass
    else:
        raise AssertionError('path repair escaped the scanned catalog')


def test_advertised_legacy_id_streams_over_audio_endpoint_with_range(tmp_path,monkeypatch):
    import threading
    import urllib.request

    node=_load_node('fcl_node_7710_http_test')
    payload=b'0123456789abcdef'
    media=tmp_path/'Talking Heads'/'Stop Making Sense'/'Psycho Killer.mp3'
    media.parent.mkdir(parents=True)
    media.write_bytes(payload)
    library=tmp_path/'media_library.json'
    library.write_text(json.dumps({'entries':[{'path':str(media),'media_type':'audio/mpeg'}]}))
    monkeypatch.setattr(node,'LOOK_MEDIA_LIBRARY',library)
    monkeypatch.setattr(node,'identity',lambda:{'name':'3090'})

    advertised=node._local_media_catalog()['entries'][0]
    server=node.FabricHTTPServer(('127.0.0.1',0),node.API,plane='local')
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    try:
        url=f"http://127.0.0.1:{server.server_port}/v1/media/audio?id={advertised['id']}"
        req=urllib.request.Request(url,headers={'Range':'bytes=4-9'})
        with urllib.request.urlopen(req,timeout=2) as response:
            assert response.status==206
            assert response.headers['Content-Range']==f'bytes 4-9/{len(payload)}'
            assert response.read()==b'456789'
    finally:
        server.shutdown(); server.server_close()
