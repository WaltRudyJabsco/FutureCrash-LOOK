from pathlib import Path
import importlib.util
import io
import sys

ROOT=Path(__file__).resolve().parents[1]
RENDERER=(ROOT/'look'/'look_renderer.py').read_text(encoding='utf-8')
LK=(ROOT/'look'/'lk').read_text(encoding='utf-8')


def load_renderer():
    path=ROOT/'look'/'look_renderer.py'
    spec=importlib.util.spec_from_file_location('look_renderer_interaction_state',path)
    mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
    return mod


class TTYIn(io.StringIO):
    def isatty(self): return True


class TTYOut(io.StringIO):
    def isatty(self): return True


class NoPreview:
    wakeup_fd=None
    def frame_cleared(self): pass
    def request(self,*_args,**_kwargs): pass
    def invalidate(self): pass
    def paint_ready(self): pass


def _pager_fixture(monkeypatch,tmp_path,keys,initial_select=None):
    r=load_renderer()
    items=[tmp_path/'a.txt',tmp_path/'b.txt',tmp_path/'c.txt']
    for p in items: p.write_text(p.name)
    seq=iter(keys)
    monkeypatch.setattr(r,'read_key',lambda *args,**kwargs: next(seq))
    monkeypatch.setattr(r,'NativePreviewController',NoPreview)
    monkeypatch.setattr(r,'preview_rows',lambda *args,**kwargs:['preview'])
    monkeypatch.setattr(r.sys,'stdin',TTYIn()); out=TTYOut(); monkeypatch.setattr(r.sys,'stdout',out)
    activated=[]
    def candidates(query):
        q=query.casefold()
        return [p for p in items if q in p.name.casefold()]
    def rebuild(query,picked=None,width=None,marked=None):
        return ['LIST '+('>> ' if p==picked else '   ')+p.name for p in candidates(query)]
    r.pager(
        ['a.txt','b.txt','c.txt'],20,100,
        rebuild=rebuild,
        browse_rebuild=lambda picked=None,marked=None,width=None: ['GRID '+p.name for p in items],
        filter_context=lambda q,w:['LOOK  test','---'],
        candidates=candidates,
        on_activate=lambda p: activated.append(p),
        force_interactive=True,
        initial_select=initial_select,
    )
    return items,activated,out.getvalue()


def test_down_from_browse_enters_filter_and_focuses_first(monkeypatch,tmp_path):
    items,activated,screen=_pager_fixture(monkeypatch,tmp_path,['\x1b[B','\r'])
    assert activated==[items[0]]
    assert 'FILTER' in screen


def test_up_from_browse_enters_filter_and_focuses_last(monkeypatch,tmp_path):
    items,activated,screen=_pager_fixture(monkeypatch,tmp_path,['\x1b[A','\r'])
    assert activated==[items[-1]]
    assert 'FILTER' in screen


def test_initial_select_is_filter_focus_not_a_third_state(monkeypatch,tmp_path):
    target=tmp_path/'b.txt'
    items,activated,_screen=_pager_fixture(monkeypatch,tmp_path,['\r'],initial_select=target)
    assert activated==[items[1]]


def test_escape_from_filter_restores_browse_grid(monkeypatch,tmp_path):
    _items,activated,screen=_pager_fixture(monkeypatch,tmp_path,['\x1b[B','\x1b','Q'])
    assert activated==[]
    assert screen.rfind('GRID a.txt') > screen.rfind('LIST ')


def test_lowercase_q_is_filter_text_not_quit(monkeypatch,tmp_path):
    # q is consumed as ordinary FILTER text. Backspace removes it, then Enter
    # activates the original first result. If q were still a quit command,
    # activation could never occur.
    items,activated,_screen=_pager_fixture(monkeypatch,tmp_path,['\x1b[B','q','\x7f','\r'])
    assert activated==[items[0]]


def test_uppercase_q_quits_from_filter(monkeypatch,tmp_path):
    _items,activated,screen=_pager_fixture(monkeypatch,tmp_path,['\x1b[B','Q'])
    assert activated==[]
    assert 'FILTER' in screen


def test_renderer_has_only_browse_and_filter_interaction_states():
    assert 'cursoring' not in RENDERER
    assert 'selecting' not in RENDERER
    assert 'browse <-> filter' in RENDERER


def test_filter_selection_keeps_one_candidate_per_row_contract():
    assert 'interactive_rows=True' in RENDERER
    assert 'if interactive_rows:' in RENDERER


def test_nerd_icons_are_default_and_classic_remains_optional():
    assert 'data={"icons":"nerd","preview":"ascii"}' in LK
    assert '("icons","FILES","File icons"' in LK
    assert "if _ICON_MODE!='nerd':" in RENDERER
    assert "return '◆'" in RENDERER
    assert r"return '\uf07b'" in RENDERER
