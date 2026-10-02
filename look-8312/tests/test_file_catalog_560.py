from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'look'))
import file_catalog


def test_scan_is_metadata_only_and_skips_default_cache(tmp_path):
    home=tmp_path/'home'; home.mkdir()
    (home/'Portland schools.pdf').write_bytes(b'x')
    (home/'code.py').write_text('print(1)')
    (home/'.cache').mkdir(); (home/'.cache'/'huge.zip').write_bytes(b'x')
    db=tmp_path/'files.sqlite3'
    result=file_catalog.scan(db,home,default_home=True)
    assert result['count']==2
    assert file_catalog.status(db)['count']==2


def test_plain_language_metadata_search(tmp_path):
    root=tmp_path/'root'; root.mkdir()
    (root/'Portland enrollment report.pdf').write_bytes(b'x')
    (root/'other.txt').write_bytes(b'x')
    db=tmp_path/'files.sqlite3'; file_catalog.scan(db,root)
    rows=file_catalog.search(db,'find Portland enrollment pdf')
    assert [r['name'] for r in rows]==['Portland enrollment report.pdf']


def test_search_rows_preserves_node_identity():
    rows=[{'node':'3090','path':'/srv/report.pdf','name':'report.pdf','ext':'.pdf','bytes':9,'mtime':1}]
    found=file_catalog.search_rows(rows,'pdf')
    assert found[0]['node']=='3090'
