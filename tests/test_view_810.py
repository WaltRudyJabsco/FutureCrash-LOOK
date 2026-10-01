from pathlib import Path
import importlib.util
import sys

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('look_renderer_810',ROOT/'look'/'look_renderer.py')
lr=importlib.util.module_from_spec(spec); sys.modules[spec.name]=lr; spec.loader.exec_module(lr)

def test_albert_dark_audio_card_has_explicit_light_foreground():
    html=(ROOT/'albert'/'index.html').read_text()
    assert '.audio-card{padding:18px;color:#f3f1ea}' in html
    assert '.audio-card .now{color:#fff}' in html
    assert '.audio-transport button{border:1px solid #6e6b64;background:transparent;color:#f3f1ea' in html

def test_sort_modes_reorder_and_label(tmp_path):
    (tmp_path/'z.txt').write_text('z')
    (tmp_path/'a.py').write_text('a')
    (tmp_path/'folder').mkdir()
    names=[p.name for p in lr.matching_paths(tmp_path,'kind',True)]
    assert names[0]=='folder'
    assert set(names[1:])=={'a.py','z.txt'}
    view='\n'.join(lr.build_view(tmp_path,'kind',True,100,2))
    assert 'SORT KIND' in lr.strip_ansi(view)

def test_pager_exposes_live_sort_and_sticky_header_hooks():
    src=(ROOT/'look'/'look_renderer.py').read_text()
    assert "key=='F' and on_sort" in src
    assert 'header_rows=sticky_header' in src
    assert "sort_cycle=['smart','recent','size','kind','added']" in src
