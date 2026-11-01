import zipfile

import pytest
import book_audio
import book_speech


PNG=b'\x89PNG\r\n\x1a\nillustration'


def illustrated(path,body,image=PNG):
    with zipfile.ZipFile(path,'w') as archive:
        archive.writestr('META-INF/container.xml','<container><rootfile full-path="OPS/book.opf"/></container>')
        archive.writestr('OPS/book.opf','''<package><manifest>
          <item id="chapter" href="text/chapter.xhtml"/>
          <item id="picture" href="images/map.png" media-type="image/png"/>
          </manifest><spine><itemref idref="chapter"/></spine></package>''')
        archive.writestr('OPS/text/chapter.xhtml',body)
        archive.writestr('OPS/images/map.png',image)
    return path


def test_illustrations_preserve_narration_and_long_paragraph_bookmarks(tmp_path,monkeypatch):
    monkeypatch.setattr(book_speech,'MAX_PASSAGE_CHARS',8)
    path=illustrated(tmp_path/'book.epub','<p>First paragraph.</p><img src="../images/map.png" alt="The harbour"><p>Last.</p>')
    rows=book_speech.chapters(path)
    assert rows[0]['paragraphs']==['First pa','ragraph.','Last.']
    assert rows[0]['images']==[{'before':2,'source':'OPS/images/map.png','alt':'The harbour'}]
    content=book_audio.chapter_content(rows,0)
    assert content['images']==[{'before':2,'index':0,'alt':'The harbour'}]
    assert 'OPS/' not in str(content)
    assert book_audio.image(path,rows,0,0)==(PNG,'image/png')


def test_mid_paragraph_image_does_not_create_new_speech_addresses(tmp_path):
    rows=book_speech.chapters(illustrated(tmp_path/'book.epub','<p>First <img src="../images/map.png">paragraph.</p><p>Last.</p>'))
    assert rows[0]['paragraphs']==['First paragraph.','Last.']
    assert rows[0]['images'][0]['before']==1


def test_only_packaged_raster_images_can_be_requested(tmp_path):
    body='''<p>Read me.</p><img src="https://example.com/tracker.png">
      <img src="file:///etc/passwd"><img src="../../../outside.png">
      <img src="../images/unknown.png"><img src="data:image/png;base64,AAAA">
      <img src="../images/map.png">'''
    rows=book_speech.chapters(illustrated(tmp_path/'book.epub',body))
    assert len(rows[0]['images'])==1
    for chapter,index in [(-1,0),(0,-1),(0,1),(1,0)]:
        with pytest.raises(ValueError):book_audio.image(tmp_path/'book.epub',rows,chapter,index)


def test_image_size_and_actual_file_type_are_checked(tmp_path,monkeypatch):
    path=illustrated(tmp_path/'book.epub','<p>Read.</p><img src="../images/map.png">',b'<svg onload="bad()"/>')
    rows=book_speech.chapters(path)
    with pytest.raises(ValueError,match='Unsupported'):book_audio.image(path,rows,0,0)
    monkeypatch.setattr(book_audio,'MAX_IMAGE_BYTES',4)
    with pytest.raises(ValueError,match='exceeds'):book_audio.image(path,rows,0,0)


def test_image_only_spine_pages_keep_existing_chapter_addresses(tmp_path):
    path=illustrated(tmp_path/'book.epub','<p>Read me.</p>')
    with zipfile.ZipFile(path) as archive:files={name:archive.read(name) for name in archive.namelist()}
    files['OPS/book.opf']=files['OPS/book.opf'].replace(b'</manifest>',b'<item id="plate" href="plate.xhtml"/></manifest>').replace(b'</spine>',b'<itemref idref="plate"/></spine>')
    files['OPS/plate.xhtml']=b'<img src="images/map.png" alt="A full-page plate">'
    with zipfile.ZipFile(path,'w') as archive:
        for name,data in files.items():archive.writestr(name,data)
    rows=book_speech.chapters(path)
    assert len(rows)==1 and rows[0]['paragraphs']==['Read me.']
    assert rows[0]['images'][0]['before']==1
