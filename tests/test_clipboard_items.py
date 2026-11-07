import base64
import json
from pathlib import Path
from unittest.mock import Mock
import pytest
import clipboard_items as items
import clipboard_shelf as shelf
import printing
import look_renderer


def test_file_snapshot_survives_source_removal_and_roundtrips(tmp_path):
    source=tmp_path/'recipe.md';source.write_text('# Soup')
    value=items.file_snapshot(source.as_uri());source.unlink()
    assert items.unpack(value)['data']==b'# Soup'
    assert '[text/markdown]' in items.describe(value)
    assert items.unpack('ordinary text') is None


def test_bounds_and_untrusted_paths(tmp_path):
    with pytest.raises(ValueError):items.pack(b'x'*(items.MAX_BYTES+1),'large.bin')
    with pytest.raises(ValueError):items.file_snapshot(tmp_path.as_uri())
    with pytest.raises(ValueError):items.file_snapshot('https://example.com/test')
    value=items.PREFIX+json.dumps(dict(name='../outside',mime='text/plain',data='eA=='))
    with pytest.raises(ValueError):items.unpack(value)


def test_attachments_share_only_when_opted_in(tmp_path,monkeypatch):
    monkeypatch.setattr(shelf,'directory',lambda:tmp_path)
    s=shelf.Shelf(tmp_path)
    try:
        s.observe(items.pack(b'first','first.bin'))
        assert shelf.published_clips()==[]
        s.auto_share(True);value=items.pack(b'second','second.bin');s.observe(value)
        assert [v['text'] for v in shelf.published_clips()]==[value]
        s.auto_share(False);assert shelf.published_clips()==[]
        for i in range(12):s.observe(items.pack(str(i).encode(),str(i)+'.bin'))
        assert len(s.rows())==10
    finally:s.close()


def test_linux_prefers_file_and_image_over_text(monkeypatch,tmp_path):
    monkeypatch.setattr(items.sys,'platform','linux');monkeypatch.setenv('WAYLAND_DISPLAY','test')
    source=tmp_path/'data.bin';source.write_bytes(b'bytes')
    monkeypatch.setattr(items,'run',Mock(side_effect=[b'text/plain\ntext/uri-list',source.as_uri().encode()]))
    assert items.unpack(items.capture(lambda:'wrong'))['data']==b'bytes'
    monkeypatch.setattr(items,'run',Mock(side_effect=[b'text/plain\nimage/png',b'png']))
    assert items.unpack(items.capture(lambda:'wrong'))['mime']=='image/png'


def test_print_falls_back_and_never_sends_unsupported(monkeypatch):
    monkeypatch.setattr(shelf,'read_item',lambda **kwargs:items.pack(b'zip','archive.zip'))
    picker=Mock(return_value=None);monkeypatch.setattr(shelf,'show',picker)
    send=Mock();monkeypatch.setattr(printing,'request',send)
    assert printing.clipboard_print(None)=='Cancelled.'
    assert picker.call_args.kwargs["pick"] is True;send.assert_not_called()


def test_print_attachment_materialized_only_for_review(monkeypatch):
    monkeypatch.setattr(shelf,'read_item',lambda **kwargs:items.pack(b'hello','note.txt'))
    paths=[]
    def review(path,*args,**kwargs):
        assert path.read_bytes()==b'hello';paths.append(path);return 0
    monkeypatch.setattr(printing,'selected_file',review)
    printing.clipboard_print(None,'tiny')
    assert not paths[0].exists()


def test_pdf_requires_pages_before_prepare(tmp_path,monkeypatch):
    source=tmp_path/'one.pdf';source.write_bytes(b'%PDF-test')
    monkeypatch.setattr(look_renderer,'prompt_line',lambda prompt:('',False))
    prepare=Mock();monkeypatch.setattr(printing,'prepare_file',prepare)
    assert printing.selected_file(source,None,queue='desk')==0
    prepare.assert_not_called()


def test_large_print_image_is_normalized_without_history_expansion(monkeypatch):
    import clipboard_image
    raw=b'x'*(items.MAX_BYTES+1)
    def process(path,**kwargs):
        assert path.read_bytes()==raw
        kwargs['output'].write_bytes(b'bounded-png')
        return {'size':[2048,1152]}
    monkeypatch.setattr(clipboard_image,'process',process)
    with pytest.raises(ValueError):items.image_snapshot(raw,'screenshot.png','image/png')
    item=items.unpack(items.image_snapshot(raw,'screenshot.png','image/png',for_print=True))
    assert item['data']==b'bounded-png'
    assert item['name']=='clipboard-print.png'


def test_capture_failure_reason_survives_picker(monkeypatch):
    def fail(**kwargs):raise ValueError('Image exceeds 64 MiB')
    monkeypatch.setattr(shelf,'read_item',fail)
    picker=Mock(return_value=None);monkeypatch.setattr(shelf,'show',picker)
    assert printing.clipboard_print(None)=='Cancelled.'
    assert '64 MiB' in picker.call_args.kwargs['initial_notice']
