import ast
import hashlib
import json
from pathlib import Path
import socket
import platform
import time
import urllib.request
import urllib.error
import urllib.parse
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]

def functions():
    names={'_media_pin_playable_entry','_media_remote_preview_identities','_media_remote_preview_identity','_media_remote_preview_key','_media_fetch_remote_preview'}
    tree=ast.parse((ROOT/'look/lk').read_text())
    ns={'Path':Path,'socket':socket,'platform':platform,'urllib':urllib,'time':time,'hashlib':hashlib,'json':json,
        '_media_local_node_names':lambda:{'mac'},'_media_entry_label':lambda r:'Song',
        'REMOTE_ART_RETRY_SECONDS':20.0,'_REMOTE_MEDIA_PREVIEW_CACHE':{},'_REMOTE_MEDIA_PREVIEW_MISS':{}}
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'lk-test','exec'),ns)
    return ns

def row():
    return {'node':'owner','id':'missing','path':'/unmounted/song.m4a',
            'art':{'node':'owner','id':'missing','path':'/unmounted/song.m4a'},
            'locations':[{'node':'owner','id':'available','path':'/mounted/song.m4a'}]}

def response(payload=None):
    r=Mock(status=200);r.__enter__=Mock(return_value=r);r.__exit__=Mock(return_value=False)
    if payload is not None:r.read.return_value=json.dumps(payload).encode()
    return r

def test_pin_updates_art_owner_when_primary_copy_is_missing(monkeypatch):
    ns=functions()
    monkeypatch.setattr(urllib.request,'urlopen',Mock(side_effect=[urllib.error.HTTPError('x',404,'missing',{},None),response()]))
    pinned=ns['_media_pin_playable_entry'](row())
    assert pinned['id']=='available' and pinned['art']['id']=='available'
    assert pinned['art']['path']=='/mounted/song.m4a'

def test_slow_primary_does_not_prevent_trying_healthy_duplicate(monkeypatch):
    ns=functions()
    monkeypatch.setattr(urllib.request,'urlopen',Mock(side_effect=[socket.timeout(),response()]))
    pinned=ns['_media_pin_playable_entry'](row())
    assert pinned['id']=='available' and 'reachability' not in pinned

def test_old_queue_art_falls_back_to_available_location_and_caches(monkeypatch):
    ns=functions();request=Mock(side_effect=[urllib.error.HTTPError('x',404,'missing',{},None),response({'lines':['cover']})])
    monkeypatch.setattr(urllib.request,'urlopen',request)
    assert ns['_media_fetch_remote_preview'](row(),22,11)==['cover']
    assert ns['_media_fetch_remote_preview'](row(),22,11)==['cover']
    assert request.call_count==2
    assert 'id=available' in request.call_args.args[0].full_url

def test_owner_missing_copy_is_not_retried_at_every_address(monkeypatch):
    from core import node
    monkeypatch.setattr(node,'identity',lambda:{'name':'local'})
    monkeypatch.setattr(node,'node_info',lambda:{})
    monkeypatch.setattr(node.PEERS,'public',lambda:[])
    monkeypatch.setattr(node,'_peer_for_target',lambda *args:{})
    monkeypatch.setattr(node,'_file_race',lambda *args:('http://owner-one',{}))
    monkeypatch.setattr(node,'_peer_bases',lambda peer:['http://owner-one','http://owner-two'])
    request=Mock(side_effect=urllib.error.HTTPError('x',404,'missing',{},None))
    monkeypatch.setattr(node.urllib.request,'urlopen',request)
    monkeypatch.setattr(node.FABRIC_IDENTITY,'auth_headers_for_url',lambda url:{})
    handler=object.__new__(node.API);handler.sendj=Mock()
    handler._serve_media_terminal_preview('owner','missing')
    assert request.call_count==1
    assert handler.sendj.call_args.args[0]==404
