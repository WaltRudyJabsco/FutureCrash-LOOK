from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_real_tty_preview_wait_has_no_periodic_clock():
    text=(ROOT/'look'/'look_renderer.py').read_text()
    block=text[text.index('def read_key_or_preview'):text.index('def matching_paths')]
    assert 'select.select([fd,wake_fd],[],[])' in block
    assert 'PREVIEW_SETTLE_SECONDS' not in text
    assert 'read_key(PREVIEW_SETTLE_SECONDS)' not in text

def test_preview_completion_does_not_redraw_text_frame():
    text=(ROOT/'look'/'look_renderer.py').read_text()
    needle="if key is None:\n                    paint_ready_preview()\n                    continue"
    assert needle in text

def test_selection_change_supersedes_old_preview_by_signature():
    text=(ROOT/'look'/'look_renderer.py').read_text()
    block=text[text.index('def request_native_preview'):text.index('def paint_ready_preview')]
    assert 'signature=(str(path),row,col,pw,min(ph,32))' in block
    assert 'preview_generation+=1' in block
    assert "threading.Thread(target=work,name='look-preview',daemon=True).start()" in block
