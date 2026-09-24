from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('file_catalog_572',ROOT/'look/file_catalog.py')
fc=importlib.util.module_from_spec(spec); spec.loader.exec_module(fc)


def test_plain_lexical_miss_never_becomes_recent_listing(tmp_path):
    root=tmp_path/'home'; root.mkdir()
    (root/'newest.txt').write_text('ordinary unrelated words',encoding='utf-8')
    db=tmp_path/'catalog.sqlite3'; fc.scan(db,root)
    assert fc.search(db,'flibbertigibbet')==[]
    assert fc.combined_search(db,'flibbertigibbet')==[]


def test_content_query_returns_content_not_unrelated_recent_files(tmp_path):
    root=tmp_path/'home'; root.mkdir()
    (root/'essay.md').write_text('GDP can be a countermeasure to happiness.',encoding='utf-8')
    (root/'newest.txt').write_text('completely unrelated',encoding='utf-8')
    db=tmp_path/'catalog.sqlite3'; fc.scan(db,root)
    rows=fc.combined_search(db,'GDP happiness')
    assert rows
    assert rows[0]['name']=='essay.md'
    assert rows[0]['match'] in {'content','name+content'}
    assert all(r['name']!='newest.txt' for r in rows)


def test_explicit_recent_metadata_query_can_list_without_lexical_terms(tmp_path):
    root=tmp_path/'home'; root.mkdir()
    (root/'anything.txt').write_text('x',encoding='utf-8')
    db=tmp_path/'catalog.sqlite3'; fc.scan(db,root)
    assert fc.search(db,'recent files')


def test_unified_node_uses_real_word_regex():
    source=(ROOT/'core/node.py').read_text(encoding='utf-8')
    assert 're.findall(r"[\\w.+-]+",str(query or "").casefold())' in source
    assert 're.findall(r"[\\\\w.+-]+",str(query or "").casefold())' not in source
