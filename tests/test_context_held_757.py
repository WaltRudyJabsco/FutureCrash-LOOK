from pathlib import Path
import importlib.util, sys
ROOT=Path(__file__).resolve().parents[1]

def load_renderer():
    p=ROOT/'look'/'look_renderer.py'; spec=importlib.util.spec_from_file_location('r757',p)
    m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m); return m

def test_filter_context_callback_has_no_pager_local_marked_reference():
    text=(ROOT/'look'/'look_renderer.py').read_text()
    assert "filter_context=lambda q,w=None: build_view" in text
    assert "q,None,None,interactive_rows=False" in text
    assert "q,None,marked,interactive_rows=False" not in text

def test_filtered_header_reports_directory_and_filtered_counts(tmp_path):
    (tmp_path/'alpha').mkdir(); (tmp_path/'beta').mkdir(); (tmp_path/'alpha.txt').write_text('a'); (tmp_path/'beta.txt').write_text('b')
    r=load_renderer(); rows=r.build_view(tmp_path,'smart',False,100,2,'alpha',None,None,interactive_rows=False)
    head=r.strip_ansi(rows[0]); assert str(tmp_path) in head; assert '1 dirs · 1 files' in head

def test_albert_media_and_camera_contracts_present():
    server=(ROOT/'albert'/'server.py').read_text(); html=(ROOT/'albert'/'index.html').read_text(); lk=(ROOT/'look'/'lk').read_text()
    assert "state=prepared.get('prepared') or prepared.get('session') or prepared" in server
    assert "if path in {'/api/media/audio','/v1/media/item'}:" in server
    assert 'capture="environment"' in html and 'what am I looking at?' in html
    assert 'text.casefold().startswith("some ")' in lk
