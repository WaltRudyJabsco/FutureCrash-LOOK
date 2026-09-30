from pathlib import Path
import importlib.util,sys
ROOT=Path(__file__).resolve().parents[1]

def renderer():
    p=ROOT/'look'/'look_renderer.py'; spec=importlib.util.spec_from_file_location('look_renderer_761',p)
    m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m); return m

def test_kitty_delete_has_empty_payload_delimiter(monkeypatch):
    r=renderer(); monkeypatch.setattr(r,'_terminal_graphics_format',lambda:'kitty')
    command=r._clear_native_preview()
    assert command == '\x1b_Ga=d,d=A,q=2;\x1b\\'

def test_native_render_is_behind_idle_input_gate():
    text=(ROOT/'look'/'look_renderer.py').read_text()
    idle=text.index("settled_key=read_key(PREVIEW_SETTLE_SECONDS)")
    render=text.index("blob=_native_preview_block(preview_path")
    assert idle < render
    assert "if not settled_key:" in text[idle:render]

def test_portal_caps_native_height_and_never_stores_blob_in_overlay():
    text=(ROOT/'look'/'look_renderer.py').read_text()
    assert "native_overlay=(len(context_rows)+1,left_w+4,picked,right_w,list_usable)" in text
    assert "min(preview_h,32)" in text
    assert "native_overlay=(len(context_rows)+1,left_w+4,native_blob)" not in text

def test_ctrl_c_during_native_write_exits_without_traceback():
    text=(ROOT/'look'/'look_renderer.py').read_text()
    block=text[text.index("blob=_native_preview_block(preview_path"):text.index("if pending:", text.index("blob=_native_preview_block(preview_path"))]
    assert "except KeyboardInterrupt:" in block
