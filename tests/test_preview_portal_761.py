from pathlib import Path
import importlib.util,sys
ROOT=Path(__file__).resolve().parents[1]

def renderer():
    p=ROOT/'look'/'look_renderer.py'; spec=importlib.util.spec_from_file_location('look_renderer_761',p)
    m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m); return m

def test_kitty_delete_has_empty_payload_delimiter(monkeypatch):
    r=renderer(); monkeypatch.setattr(r,'_terminal_graphics_format',lambda:'kitty')
    assert r._clear_native_preview() == '\x1b_Ga=d,d=A,q=2;\x1b\\'

def test_native_render_is_background_edge_job_not_timed_input_gate():
    text=(ROOT/'look'/'look_renderer.py').read_text()
    assert 'PREVIEW_SETTLE_SECONDS' not in text
    assert 'threading.Thread(target=work' in text
    assert 'blob=_native_preview_block(path,pw,min(ph,32))' in text
    assert 'read_key_or_preview(preview_r)' in text

def test_portal_caps_native_height_and_never_stores_blob_in_overlay():
    text=(ROOT/'look'/'look_renderer.py').read_text()
    assert "native_overlay=(len(context_rows)+1,left_w+4,picked,right_w,list_usable)" in text
    assert 'min(ph,32)' in text
    assert 'native_overlay=(len(context_rows)+1,left_w+4,native_blob)' not in text

def test_worker_never_writes_terminal_and_stale_generation_is_discarded():
    text=(ROOT/'look'/'look_renderer.py').read_text()
    block=text[text.index('def request_native_preview'):text.index('def paint_ready_preview')]
    assert 'sys.stdout.write' not in block
    assert 'generation!=preview_generation' in block
    paint=text[text.index('def paint_ready_preview'):text.index('try:',text.index('def paint_ready_preview'))+500]
    assert 'generation!=preview_generation' in paint
