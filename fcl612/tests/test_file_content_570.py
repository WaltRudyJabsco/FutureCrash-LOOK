from pathlib import Path
import sys, zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'look'))
import file_catalog


def test_scan_indexes_plain_text_and_finds_content(tmp_path):
    root=tmp_path/'home'; root.mkdir()
    (root/'notes.md').write_text('GDP can become a countermeasure to happiness when consumption is the proxy.',encoding='utf-8')
    db=tmp_path/'files.sqlite3'
    result=file_catalog.scan(db,root)
    assert result['content_indexed']==1
    rows=file_catalog.combined_search(db,'where was that thing I wrote about GDP countermeasure happiness')
    assert rows and rows[0]['name']=='notes.md'
    assert rows[0]['match'] in {'content','name+content'}
    assert 'GDP' in rows[0]['snippet']


def test_html_content_strips_script_noise(tmp_path):
    root=tmp_path/'home'; root.mkdir()
    (root/'essay.html').write_text('<script>secretNoiseToken</script><p>civic mysticism and trust</p>',encoding='utf-8')
    db=tmp_path/'files.sqlite3'; file_catalog.scan(db,root)
    assert file_catalog.content_search(db,'civic mysticism')
    assert not file_catalog.content_search(db,'secretNoiseToken')


def test_docx_content_without_external_dependency(tmp_path):
    root=tmp_path/'home'; root.mkdir(); doc=root/'draft.docx'
    xml='<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>American Mercury winter draft</w:t></w:r></w:p></w:body></w:document>'
    with zipfile.ZipFile(doc,'w') as z: z.writestr('word/document.xml',xml)
    db=tmp_path/'files.sqlite3'; file_catalog.scan(db,root)
    rows=file_catalog.content_search(db,'Mercury winter')
    assert rows and rows[0]['name']=='draft.docx'


def test_unchanged_content_is_not_reextracted(tmp_path):
    root=tmp_path/'home'; root.mkdir(); (root/'note.txt').write_text('stable searchable phrase')
    db=tmp_path/'files.sqlite3'
    assert file_catalog.scan(db,root)['content_indexed']==1
    assert file_catalog.scan(db,root)['content_indexed']==0
    assert file_catalog.content_search(db,'stable searchable phrase')
