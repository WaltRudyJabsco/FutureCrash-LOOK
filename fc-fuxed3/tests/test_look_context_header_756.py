from pathlib import Path
import importlib.util
import sys

ROOT=Path(__file__).resolve().parents[1]


def _renderer():
    path=ROOT/'look'/'look_renderer.py'
    spec=importlib.util.spec_from_file_location('look_renderer_756',path)
    mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
    return mod


def test_filter_header_keeps_directory_identity_and_filtered_counts(tmp_path):
    (tmp_path/'alpha').mkdir(); (tmp_path/'beta').mkdir()
    (tmp_path/'alpha.txt').write_text('a'); (tmp_path/'beta.txt').write_text('b')
    r=_renderer()
    rows=r.build_view(tmp_path,'smart',False,100,2,'alpha',interactive_rows=False)
    plain=r.strip_ansi(rows[0])
    assert 'LOOK' in plain
    assert str(tmp_path) in plain
    assert '1 dirs · 1 files' in plain


def test_interactive_pager_has_fixed_filter_context_callback():
    text=(ROOT/'look'/'look_renderer.py').read_text()
    assert 'filter_context=None' in text
    assert 'if filtering and filter_context:' in text
    assert 'list_usable=max(1,usable-len(context_rows))' in text
    assert 'filter_context=lambda q,w=None: build_view' in text
