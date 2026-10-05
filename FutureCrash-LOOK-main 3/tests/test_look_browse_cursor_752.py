from pathlib import Path
import importlib.util, io, sys

ROOT=Path(__file__).resolve().parents[1]
RENDERER=(ROOT/'look'/'look_renderer.py').read_text(encoding='utf-8')
LK=(ROOT/'look'/'lk').read_text(encoding='utf-8')


def load_renderer():
    p=ROOT/'look'/'look_renderer.py'
    spec=importlib.util.spec_from_file_location('look_renderer_browse_filter',p)
    mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
    return mod


class TTYIn(io.StringIO):
    def isatty(self): return True


class TTYOut(io.StringIO):
    def isatty(self): return True


def run_browse(monkeypatch,tmp_path,keys):
    r=load_renderer()
    files=[tmp_path/f'{i:03}.txt' for i in range(130)]
    for p in files: p.write_text('x')
    seq=iter(keys)
    monkeypatch.setattr(r,'read_key',lambda timeout=None, **kwargs: next(seq))
    monkeypatch.setattr(r,'preview_rows',lambda *args,**kwargs:['preview'])
    monkeypatch.setattr(r.sys,'stdin',TTYIn())
    out=TTYOut(); monkeypatch.setattr(r.sys,'stdout',out)
    activated=[]
    def candidates(q): return [p for p in files if q.casefold() in p.name.casefold()]
    def rebuild(q,picked=None,w=None,marked=None):
        return [('>> ' if picked==p else '   ')+p.name for p in candidates(q)]
    def browse_rebuild(picked=None,marked=None,w=None):
        return [('>> ' if picked==p else '   ')+p.name for p in files]
    r.pager([p.name for p in files],32,100,rebuild=rebuild,browse_rebuild=browse_rebuild,
            filter_context=lambda q,w:['LOOK  test','---'],candidates=candidates,
            on_activate=lambda p:activated.append(p),force_interactive=True)
    return r,files,activated,out.getvalue()


def test_unfiltered_down_enters_filter_then_uses_filter_navigation(monkeypatch,tmp_path):
    _,files,activated,screen=run_browse(monkeypatch,tmp_path,['\x1b[B','\x1b[B','\r'])
    assert activated==[files[1]]
    assert 'FILTER' in screen


def test_unfiltered_up_enters_filter_at_last_item(monkeypatch,tmp_path):
    _,files,activated,screen=run_browse(monkeypatch,tmp_path,['\x1b[A','\r'])
    assert activated==[files[-1]]
    assert 'FILTER' in screen


def test_browse_arrows_never_enter_legacy_cursor_state():
    assert "cursoring=bool(matches)" not in RENDERER
    assert "filtering=True\n                selected=0\n                refresh_filter()" in RENDERER
    assert "filtering=True\n                refresh_filter()\n                selected=max(0,len(matches)-1)" in RENDERER


def test_filter_selection_keeps_one_candidate_per_row_contract():
    assert "interactive_rows=True" in RENDERER
    assert "if interactive_rows:" in RENDERER


def test_nerd_icons_are_default_and_classic_remains_optional():
    assert 'data={"icons":"nerd","preview":"ascii"}' in LK
    assert '("icons","FILES","File icons"' in LK
    assert "if _ICON_MODE!='nerd':" in RENDERER
    assert "return '◆'" in RENDERER
    assert "return '\\uf07b'" in RENDERER
