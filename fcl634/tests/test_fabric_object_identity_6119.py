import sqlite3
from pathlib import Path

from look import file_catalog
import core.node as node


def test_small_indexed_files_gain_exact_content_identity(tmp_path):
    root=tmp_path/'files'; root.mkdir(); (root/'same.md').write_text('same bytes\n')
    db=tmp_path/'catalog.sqlite3'
    file_catalog.scan(db,root)
    con=sqlite3.connect(db)
    digest=con.execute("SELECT digest FROM content_state WHERE path=?",(str(root/'same.md'),)).fetchone()[0]
    con.close()
    assert digest.startswith('sha256:') and len(digest)==71


def test_existing_v2_catalog_migrates_digest_column(tmp_path):
    db=tmp_path/'old.sqlite3'; con=sqlite3.connect(db)
    con.execute("CREATE TABLE content_state(path TEXT PRIMARY KEY, mtime REAL NOT NULL, bytes INTEGER NOT NULL, kind TEXT NOT NULL, chars INTEGER NOT NULL, indexed REAL NOT NULL, error TEXT NOT NULL DEFAULT '')")
    con.execute('PRAGMA user_version=2'); con.commit(); con.close()
    migrated=file_catalog.connect(db)
    cols={row[1] for row in migrated.execute('PRAGMA table_info(content_state)')}
    migrated.close()
    assert 'digest' in cols


def test_fabric_search_collapses_same_object_but_keeps_locations(monkeypatch):
    digest='sha256:'+'a'*64
    monkeypatch.setattr(node,'_local_file_search',lambda q,limit:{'entries':[{'node':'M4','path':'/a/doc.md','name':'doc.md','bytes':4,'mtime':2,'digest':digest}]})
    monkeypatch.setattr(node,'node_info',lambda:{})
    monkeypatch.setattr(node.PEERS,'public',lambda:[{'name':'M3','url':'http://m3','node':{'identity':{'name':'M3'}}}])
    monkeypatch.setattr(node,'_remote_url',lambda snapshot,name,path:'http://m3'+path)
    monkeypatch.setattr(node,'http_json',lambda *a,**k:{'entries':[{'node':'M3','path':'/b/doc.md','name':'doc.md','bytes':4,'mtime':1,'digest':digest}]})
    out=node._fabric_file_search('doc',80)
    assert out['count']==1 and out['locations']==2
    assert out['entries'][0]['object_id']==digest
    assert {x['node'] for x in out['entries'][0]['locations']}=={'M4','M3'}


def test_signal_video_uses_generic_artifact_stream_when_identified():
    js=(Path(__file__).resolve().parents[1]/'signal-window'/'app.js').read_text()
    server=(Path(__file__).resolve().parents[1]/'signal-window'/'server.py').read_text()
    assert "document.createElement('video')" in js
    assert '/api/artifact?node=' in js
    assert 'def _proxy_artifact(' in server
    assert 'NODE_URL+"/v1/media/artifact"' in server
