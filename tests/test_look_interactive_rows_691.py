from pathlib import Path
import importlib.util
import sys

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('look_renderer',ROOT/'look'/'look_renderer.py')
mod=importlib.util.module_from_spec(SPEC); sys.modules[SPEC.name]=mod; SPEC.loader.exec_module(mod)

def test_interactive_smart_view_is_one_row_per_candidate_even_in_wide_terminal(tmp_path):
    for i in range(240):
        (tmp_path/f'item-{i:03d}.txt').write_text(str(i))
    candidates=mod.matching_paths(tmp_path,'smart',True,'')
    rows=mod.build_view(tmp_path,'smart',True,240,2,'',candidates[137],set(),interactive_rows=True)
    assert len(rows)==len(candidates)
    assert sum('item-137.txt' in mod.strip_ansi(row) for row in rows)==1
    assert 'item-137.txt' in mod.strip_ansi(rows[137])
    assert 'item-138.txt' not in mod.strip_ansi(rows[137])

def test_interactive_filtered_view_has_no_section_or_header_rows(tmp_path):
    (tmp_path/'alpha-dir').mkdir()
    (tmp_path/'alpha-file.txt').write_text('x')
    candidates=mod.matching_paths(tmp_path,'smart',True,'alpha')
    rows=mod.build_view(tmp_path,'smart',True,200,2,'alpha',candidates[0],set(),interactive_rows=True)
    assert len(rows)==2
    plain=[mod.strip_ansi(r) for r in rows]
    assert not any('LOOK' in r or 'FOLDERS' in r or 'FILES' in r for r in plain)
    assert all('alpha-' in r for r in plain)

def test_static_wide_view_may_still_pack_columns(tmp_path):
    for i in range(30):
        (tmp_path/f'f{i:02d}').write_text('x')
    rows=mod.build_view(tmp_path,'smart',True,200,2)
    body=[mod.strip_ansi(r) for r in rows[2:]]
    assert any(sum(f'f{i:02d}' in row for i in range(30)) > 1 for row in body)

def test_interactive_clipboard_uses_existing_batch_transaction_path():
    source=(ROOT/'look'/'look_renderer.py').read_text()
    assert "shelf.update(kind=kind,paths=" in source
    assert "'_batch',kind,str(dest)" in source
    assert "notice='pasted · lk undo'" in source
    assert "'B clipboard','T Cut','P Paste'" in source
