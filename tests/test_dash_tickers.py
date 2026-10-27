import pytest
from test_dash_activity import node,_dash_fixture


@pytest.fixture(autouse=True)
def reset_tickers(monkeypatch):
    node._DASH_TICKER_STARTS.clear()
    monkeypatch.setattr(node,'_DASH_TICKER_PAUSED_AT',None)


def test_ticker_dwell_travel_end_and_static_snapshot():
    text='abcdefghij'
    assert node._dash_ticker(text,5,True,elapsed=0)=='abcde'
    assert node._dash_ticker(text,5,True,elapsed=3)=='abcde'
    assert node._dash_ticker(text,5,True,elapsed=4)=='cdefg'
    assert node._dash_ticker(text,5,True,elapsed=6)=='fghij'
    assert node._dash_ticker(text,5,True,elapsed=8)=='fghij'
    assert node._dash_ticker(text,5,True,elapsed=8.5)=='abcde'
    assert node._dash_ticker(text,5,False,elapsed=4)=='abcde'
    assert node._dash_ticker('short',10,True,elapsed=100)=='short     '


def test_new_text_and_resize_start_from_beginning(monkeypatch):
    clock=[0.0];monkeypatch.setattr(node.time,'monotonic',lambda:clock[0])
    assert node._dash_ticker('abcdefghij',5,True)=='abcde'
    clock[0]=4
    assert node._dash_ticker('abcdefghij',5,True)=='cdefg'
    assert node._dash_ticker('new event detail',5,True)=='new e'
    assert node._dash_ticker('abcdefghij',6,True)=='abcdef'


def test_pause_and_resume_preserve_offset(monkeypatch):
    clock=[0.0];monkeypatch.setattr(node.time,'monotonic',lambda:clock[0])
    node._dash_ticker('abcdefghij',5,True);clock[0]=4
    node._dash_toggle_tickers();clock[0]=40
    assert node._dash_ticker('abcdefghij',5,True)=='cdefg'
    node._dash_toggle_tickers()
    assert node._dash_ticker('abcdefghij',5,True)=='cdefg'
    clock[0]=41
    assert node._dash_ticker('abcdefghij',5,True)=='efghi'


def test_unicode_cells_and_control_characters_never_escape_viewport():
    text='\033[31mCafé 中文 e\u0301\033[0m\n\033[2J'
    for elapsed in range(20):
        rendered=node._dash_ticker(text,7,True,elapsed=elapsed)
        assert node._dash_visible_len(rendered)==7
        assert '\033' not in rendered and '\n' not in rendered
    assert '\u0301' in node._dash_ticker('e\u0301',2,True)


@pytest.mark.parametrize('width,height',[(40,18),(82,18),(92,28),(120,22),(120,28),(92,70)])
def test_all_layouts_keep_geometry_and_controls_when_tickers_move(monkeypatch,width,height):
    data=_dash_fixture();data['nodes']['self']['inference']['preferred_model']='very-long-model-name-'+('x'*150)
    data['events']['events'][0]['detail']='A very long observed task '+('detail '*40)
    clock=[100.0];monkeypatch.setattr(node.time,'monotonic',lambda:clock[0])
    first=node._dash_render(data,width,height=height,ansi=True)
    clock[0]=105
    later=node._dash_render(data,width,height=height,ansi=True)
    assert first!=later
    assert len(first.splitlines())==len(later.splitlines())<=height
    assert all(node._dash_visible_len(line)<=width for line in later.splitlines())
    assert '[q] quit' in later


def test_recent_event_columns_stay_fixed(monkeypatch):
    event={'type':'progress','phase':'inference','node':'local','ts':node.now(),'detail':'abcdefghij'*10}
    clock=[0.0];monkeypatch.setattr(node.time,'monotonic',lambda:clock[0])
    first=node._dash_recent_line(event,'local',60,True)
    clock[0]=4
    later=node._dash_recent_line(event,'local',60,True)
    import re
    strip=lambda text:re.sub(r'\x1b\[[0-9;]*m','',text)
    prefix=strip(first).split('abcdefgh')[0]
    assert strip(later).startswith(prefix) and first!=later
    assert '[t] pause tickers' in node._dash_controls(150)
    node._dash_toggle_tickers()
    assert '[t] resume tickers' in node._dash_controls(150)


def test_qualification_age_change_does_not_restart_model_ticker(monkeypatch):
    clock=[0.0];monkeypatch.setattr(node.time,'monotonic',lambda:clock[0])
    label=['abcdefghij · Q 1m']
    monkeypatch.setattr(node,'_dash_model',lambda row:label[0])
    row={'inference':{'resident':['abcdefghij']}}
    assert node._dash_model_ticker('host',row,5,True)=='abcde'
    clock[0]=4;label[0]='abcdefghij · Q 2m'
    assert node._dash_model_ticker('host',row,5,True)=='cdefg'
    label[0]='new model · Q 0m'
    assert node._dash_model_ticker('host',row,5,True)=='new m'


def test_wide_node_names_and_phases_keep_their_columns():
    data=_dash_fixture()
    data['nodes']['self']['name']='电脑'*20
    data['events']['events'][0]['phase']='工作'*20
    for width,height in ((40,18),(92,28),(120,22),(92,70)):
        body=node._dash_render(data,width,height=height,ansi=True)
        # The title/identity header may wrap; node and event viewports cannot.
        for line in body.splitlines():
            if 'Q ' in line or 'LOCAL' in line or 'REMOTE' in line:
                assert node._dash_visible_len(line)<=width
