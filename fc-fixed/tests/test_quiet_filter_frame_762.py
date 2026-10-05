from pathlib import Path
import importlib.util, io, sys

ROOT=Path(__file__).resolve().parents[1]

def load_renderer():
    p=ROOT/'look'/'look_renderer.py'
    spec=importlib.util.spec_from_file_location('look_renderer_762',p)
    mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
    return mod

class TTYIn(io.StringIO):
    def isatty(self): return True
class TTYOut(io.StringIO):
    def isatty(self): return True

def test_filtered_frame_erases_stale_right_hand_text(monkeypatch,tmp_path):
    r=load_renderer(); a=tmp_path/'a.png'; a.write_bytes(b'x')
    seq=iter(['','\r'])
    monkeypatch.setattr(r,'read_key',lambda timeout=None: next(seq))
    monkeypatch.setattr(r,'_terminal_graphics_format',lambda:'kitty')
    monkeypatch.setattr(r,'_native_preview_block',lambda *args:'PIXELS')
    monkeypatch.setattr(r.sys,'stdin',TTYIn()); out=TTYOut(); monkeypatch.setattr(r.sys,'stdout',out)
    r.pager(['OLD FULL WIDTH DIRECTORY COLUMNS'],20,120,
            rebuild=lambda q,picked=None,w=None,marked=None:[('>> ' if picked==a else '')+'a.png'],
            filter_context=lambda q,w:['LOOK  ~/Desktop  0 dirs · 1 files','---'],
            candidates=lambda q:[a],on_activate=lambda p:None,force_interactive=True,initial_query='pn')
    screen=out.getvalue()
    # Every rewritten list/context line erases whatever the previous wider frame left to its right.
    assert 'a.png' in screen and screen.index('\x1b[K',screen.index('a.png')) < screen.index('a.png')+130
    assert 'LOOK  ~/Desktop  0 dirs · 1 files\x1b[K' in screen
    # Replacement is atomic from the user's point of view: delete old graphic immediately before new payload.
    assert r._clear_native_preview()+'\x1b7' in screen

def test_filter_down_moves_highlight_without_scrolling_until_viewport_edge(monkeypatch,tmp_path):
    r=load_renderer(); files=[]
    for i in range(5):
        p=tmp_path/f'{i}.png'; p.write_bytes(b'x'); files.append(p)
    seq=iter(['','\x1b[B','','\r'])
    monkeypatch.setattr(r,'read_key',lambda timeout=None: next(seq))
    monkeypatch.setattr(r,'_terminal_graphics_format',lambda:'kitty')
    monkeypatch.setattr(r,'_native_preview_block',lambda *args:None)
    monkeypatch.setattr(r.sys,'stdin',TTYIn()); out=TTYOut(); monkeypatch.setattr(r.sys,'stdout',out)
    activated=[]
    def rebuild(q,picked=None,w=None,marked=None):
        return [('>> ' if p==picked else '   ')+p.name for p in files]
    r.pager(['LOOK'],20,120,rebuild=rebuild,filter_context=lambda q,w:['LOOK','---'],
            candidates=lambda q:files,on_activate=lambda p:activated.append(p),force_interactive=True,initial_query='pn')
    screen=out.getvalue()
    # Second frame still contains item 0 above the highlighted item 1; the list did not scroll with selection.
    second=screen.rfind('>> 1.png')
    assert second!=-1
    prior=screen.rfind('0.png',0,second)
    assert prior!=-1 and second-prior < 500
    assert activated==[files[1]]

def test_frame_start_does_not_delete_native_preview_before_replacement_is_ready():
    text=(ROOT/'look'/'look_renderer.py').read_text()
    assert "sys.stdout.write('\\x1b[H')" in text
    assert "sys.stdout.write(_clear_native_preview()+'\\x1b[H')" not in text
    assert "sys.stdout.write(_clear_native_preview()+f'\\x1b7" in text
