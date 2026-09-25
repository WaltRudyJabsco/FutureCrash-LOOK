import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('file_catalog_571',ROOT/'look/file_catalog.py')
fc=importlib.util.module_from_spec(spec); spec.loader.exec_module(fc)

def test_resolve_directory_from_indexed_parent(tmp_path):
    home=tmp_path/'Desktop'/'misc-programs'/'labs'; home.mkdir(parents=True)
    (home/'experiment.py').write_text('print(1)')
    db=tmp_path/'catalog.sqlite3'; fc.scan(db,tmp_path)
    rows=fc.resolve_paths(db,'labs folder')
    assert rows[0]['path']==str(home)
    assert rows[0]['kind']=='directory'

def test_exact_basename_beats_path_match(tmp_path):
    exact=tmp_path/'labs'; exact.mkdir(); (exact/'a.txt').write_text('a')
    weaker=tmp_path/'other'/'labs-notes'; weaker.mkdir(parents=True); (weaker/'b.txt').write_text('b')
    db=tmp_path/'catalog.sqlite3'; fc.scan(db,tmp_path)
    rows=fc.resolve_paths(db,'labs',kind='directory')
    assert rows[0]['path']==str(exact)
    assert rows[0]['score']>=1000

def test_folder_word_is_type_hint_not_filename_term(tmp_path):
    d=tmp_path/'Projects'/'Mercury'; d.mkdir(parents=True); (d/'draft.md').write_text('x')
    db=tmp_path/'catalog.sqlite3'; fc.scan(db,tmp_path)
    rows=fc.resolve_paths(db,'Mercury folder')
    assert any(r['path']==str(d) for r in rows)
    assert all(r['kind']=='directory' for r in rows)
