from pathlib import Path
import importlib.util, io, sys

ROOT=Path(__file__).resolve().parents[1]


def load_renderer():
    p=ROOT/'look'/'look_renderer.py'
    spec=importlib.util.spec_from_file_location('look_renderer_758',p)
    mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
    return mod


class TTYIn(io.StringIO):
    def isatty(self): return True


class TTYOut(io.StringIO):
    def isatty(self): return True


def test_filter_arrow_then_enter_activates_visible_second_match(monkeypatch,tmp_path):
    r=load_renderer()
    a=tmp_path/'a.png'; b=tmp_path/'b.png'; a.write_bytes(b'x'); b.write_bytes(b'x')
    seq=iter(['\x1b[B','\r'])
    monkeypatch.setattr(r,'read_key',lambda timeout=None: next(seq))
    monkeypatch.setattr(r,'preview_rows',lambda *args,**kwargs:['preview'])
    monkeypatch.setattr(r,'_native_preview_block',lambda *args,**kwargs:None)
    monkeypatch.setattr(r.sys,'stdin',TTYIn())
    out=TTYOut(); monkeypatch.setattr(r.sys,'stdout',out)
    activated=[]
    def candidates(q):
        return [p for p in (a,b) if q.casefold() in p.name.casefold()]
    def rebuild(q,picked=None,w=None,marked=None):
        rows=[]
        for p in candidates(q):
            prefix='>> ' if picked and p==picked else '   '
            rows.append(prefix+p.name)
        return rows
    r.pager(['LOOK','rule','a.png','b.png'],20,100,
            rebuild=rebuild,
            filter_context=lambda q,w:['LOOK  ~/Desktop  0 dirs · 2 files','---'],
            candidates=candidates,
            on_activate=lambda p: activated.append(p),
            force_interactive=True,
            initial_query='png')
    assert activated==[b]
    screen=out.getvalue()
    assert 'LOOK  ~/Desktop' in screen
    assert 'FILTER' in screen


def test_typing_filter_resets_selection_to_first_match(monkeypatch,tmp_path):
    r=load_renderer()
    files=[tmp_path/n for n in ('a.txt','b.txt','c.png','d.png')]
    for p in files: p.write_bytes(b'x')
    # Start with an existing query and move down; then type 'g' so result set changes.
    # After the mutation the next Enter must activate the first match, not carry index 1.
    seq=iter(['\x1b[B','g','', '\r'])
    def keys(timeout=None):
        try: return next(seq)
        except StopIteration: return '\r'
    monkeypatch.setattr(r,'read_key',keys)
    monkeypatch.setattr(r,'preview_rows',lambda *args,**kwargs:['preview'])
    monkeypatch.setattr(r,'_native_preview_block',lambda *args,**kwargs:None)
    monkeypatch.setattr(r.sys,'stdin',TTYIn()); monkeypatch.setattr(r.sys,'stdout',TTYOut())
    activated=[]
    def candidates(q): return [p for p in files if q.casefold() in p.name.casefold()]
    def rebuild(q,picked=None,w=None,marked=None): return [p.name for p in candidates(q)]
    r.pager(['LOOK'],20,100,rebuild=rebuild,filter_context=lambda q,w:['LOOK','---'],
            candidates=candidates,on_activate=lambda p:activated.append(p),force_interactive=True,initial_query='pn')
    assert activated and activated[0]==files[2]


def test_native_preview_is_a_dedicated_bounded_viewport(monkeypatch,tmp_path):
    r=load_renderer(); img=tmp_path/'x.png'; img.write_bytes(b'x')
    monkeypatch.setattr(r,'_PREVIEW_MODE','auto')
    monkeypatch.setattr(r,'_terminal_graphics_format',lambda:'kitty')
    monkeypatch.setattr(r.shutil,'which',lambda name:'/usr/bin/chafa' if name=='chafa' else None)
    calls=[]
    class P:
        returncode=0; stdout='PIXELS\n'; stderr=''
    def run(args,**kwargs): calls.append(args); return P()
    monkeypatch.setattr(r.subprocess,'run',run)
    blob=r._native_preview_block(img,80,10)
    assert blob=='PIXELS'
    args=calls[0]
    assert '--view-size' in args and '80x10' in args
    assert '--size' in args and '80x10' in args
    assert '--align' in args and 'bottom,center' in args
    assert '--relative' in args and 'on' in args


def test_embedded_preview_never_uses_native_pixel_protocol(monkeypatch,tmp_path):
    r=load_renderer(); img=tmp_path/'x.png'; img.write_bytes(b'x')
    monkeypatch.setattr(r,'_PREVIEW_MODE','auto')
    monkeypatch.setattr(r,'_terminal_graphics_format',lambda:'kitty')
    monkeypatch.setattr(r.shutil,'which',lambda name:'/usr/bin/chafa' if name=='chafa' else None)
    calls=[]
    class P:
        returncode=0; stdout='row1\nrow2\n'; stderr=''
    monkeypatch.setattr(r.subprocess,'run',lambda args,**kwargs:(calls.append(args) or P()))
    rows=r._chafa_render(img,40,8,allow_native=False)
    assert rows==['row1','row2']
    assert '--format=symbols' in calls[0]


def test_native_preview_stays_in_right_pane_and_frame_does_not_full_clear(monkeypatch,tmp_path):
    r=load_renderer(); a=tmp_path/'a.png'; a.write_bytes(b'x')
    seq=iter(['\r'])
    monkeypatch.setattr(r,'read_key',lambda timeout=None: next(seq))
    monkeypatch.setattr(r,'_native_preview_block',lambda path,w,h:'PIXELS')
    monkeypatch.setattr(r.sys,'stdin',TTYIn()); out=TTYOut(); monkeypatch.setattr(r.sys,'stdout',out)
    def candidates(q): return [a]
    def rebuild(q,picked=None,w=None,marked=None): return [('>> ' if picked==a else '')+'a.png']
    activated=[]
    r.pager(['LOOK'],20,120,rebuild=rebuild,
            filter_context=lambda q,w:['LOOK  ~/Desktop  0 dirs · 1 files','---'],
            candidates=candidates,on_activate=lambda p:activated.append(p),
            force_interactive=True,initial_query='png')
    screen=out.getvalue()
    # 58% of 120 => left pane 69 cols, separator consumes 3; native pane starts at col 73.
    assert '\x1b[3;73HPIXELS' in screen
    assert '\x1b[2J' not in screen
    assert 'LOOK  ~/Desktop' in screen
    assert activated==[a]
