import io
import time
from unittest.mock import Mock

import pytest
from look import disc_ui, media_storage


def job(number,title='Album',state='complete',delivery=None):
    row={'id':f'{number:032x}','title':title,'kind':'cd','state':state,'stage':state,'created':time.time(),'metadata':{'artist':'Band'}}
    if delivery:row['delivery']={'state':delivery}
    return row


def test_workbench_separates_inserted_disc_from_history_and_colors_states(monkeypatch):
    import re
    monkeypatch.setenv('LOOK_TERMINAL_THEME','paper')
    colors=disc_ui.interface_colors()
    inventory={'node':'Tower','drives':[{'id':'/dev/sr0','label':'Blu-ray drive','disc':'FRENCH_KISS'}],
               'tools':{'makemkvcon':'/bin/makemkvcon'}}
    rows=disc_ui.workbench_lines(inventory,[job(1,'PCU'),job(2,'Old failure','failed')],0,100,30,True,colors)
    rendered='\n'.join(rows);plain=re.sub(r'\x1b\[[0-9;]*m','',rendered)
    assert plain.index('FRENCH KISS')<plain.index('IMPORT JOBS')<plain.index('PCU')
    assert 'complete · complete' not in plain
    assert colors['GREEN']+'complete' in rendered and colors['RED']+'failed' in rendered
    assert '38;2;' in colors['GREEN'] and 'Shift' not in plain


@pytest.mark.parametrize('theme',('paper','neon','slate'))
def test_selected_row_uses_theme_background_readable_inks_and_resets(monkeypatch,theme):
    import re
    from look import terminal_style
    monkeypatch.setenv('LOOK_TERMINAL_THEME',theme)
    colors=disc_ui.interface_colors()
    def hex_color(code):
        channels=re.search(r';2;(\d+);(\d+);(\d+)m',code).groups()
        return '#'+''.join(f'{int(value):02x}' for value in channels)
    background=hex_color(colors['SELECT_BG'])
    assert background==terminal_style.settings(theme)['selection_background']
    for role in ('FG','GRAY','GREEN','RED','YELLOW'):
        assert terminal_style.contrast(background,hex_color(colors['SELECT_'+role]))>=4.5
    rows=disc_ui.workbench_lines({'drives':[],'tools':{}},[job(1,'Film'),job(2,'Other')],0,60,30,True,colors)
    selected=next(row for row in rows if colors['SELECT_BG'] in row)
    assert len(re.sub(r'\x1b\[[0-9;]*m','',selected))==59
    assert selected.endswith('\033[0m') and '› ' in selected
    assert colors['SELECT_BG'] not in next(row for row in rows if 'Other' in row)


@pytest.fixture
def plain(monkeypatch):
    monkeypatch.setattr(disc_ui.sys,'stdin',io.StringIO())


def test_deliver_uses_remembered_destination_and_single_undelivered_album(plain,monkeypatch,capsys):
    monkeypatch.setattr(media_storage,'settings',lambda:{'node':'3090','root':'/media/Library'})
    request=Mock(side_effect=[{'jobs':[job(1,delivery='complete'),job(2,'New Album')]},{'ok':True}])
    assert disc_ui.main(['deliver'],lambda node:request,None,None)==0
    assert request.call_args.args==('deliver',{'drive':None,'kind':'cd','id':f'{2:032x}','destination':'@3090:/media/Library'})
    output=capsys.readouterr().out
    assert '3090' in output and f'{2:032x}' not in output and '/media/Library' not in output


def test_multiple_deliveries_require_choice_before_mutating(plain,capsys):
    request=Mock(return_value={'jobs':[job(1,'First'),job(2,'Second')]})
    assert disc_ui.main(['deliver'],lambda node:request,None,None)==1
    assert request.call_count==1
    assert 'First' in capsys.readouterr().err


@pytest.mark.parametrize('selector,expected',[('second',2),('Band',None),('latest',1),('00000000000000000000000000000002',2)])
def test_job_names_latest_and_full_ids(plain,selector,expected):
    request=Mock(return_value={'jobs':[job(1,'First'),job(2,'Second')]})
    if expected is None:
        with pytest.raises(ValueError,match='More than one'):disc_ui.resolve_job(request,selector,'deliver')
    else:assert disc_ui.resolve_job(request,selector,'deliver')==f'{expected:032x}'


def test_multiword_album_selector_and_retry(plain,monkeypatch):
    request=Mock(side_effect=[{'jobs':[job(2,'New Album',delivery='failed')]},{'ok':True}])
    assert disc_ui.main(['deliver','New','Album','--destination','@3090:/media'],lambda node:request,None,None)==0
    assert request.call_args.args[1]['id']==f'{2:032x}'


def test_watch_without_id_reports_all_active_work(plain,capsys):
    request=Mock(return_value={'jobs':[job(1,'Rip',state='running'),job(2,'Transfer',delivery='running'),job(3,'Old')]})
    assert disc_ui.main(['watch'],lambda node:request,None,None)==0
    output=capsys.readouterr().out
    assert 'Rip' in output and 'Transfer' in output and 'Old' not in output


def test_default_watch_uses_fabric_and_explicit_node_stays_scoped(plain):
    factory=Mock(return_value=Mock(return_value={'jobs':[]}))
    assert disc_ui.main(['watch'],factory,None,None)==0
    factory.assert_called_with('fabric')
    assert disc_ui.main(['watch','--node','local'],factory,None,None)==0
    factory.assert_called_with('local')


def test_fabric_watch_labels_owners_and_unavailable_nodes(plain,capsys):
    first=dict(job(1,'Remote film','running'),node='Tower')
    request=Mock(return_value={'fabric':True,'jobs':[first,job(2,'Old')],'unavailable':[{'node':'Sleeping laptop'}]})
    assert disc_ui.main(['watch'],lambda node:request,None,None)==0
    output=capsys.readouterr().out
    assert 'Tower · Remote film' in output and 'Sleeping laptop' in output and 'Old' not in output


def test_fabric_jobs_collect_trusted_owners_and_isolate_failures(monkeypatch):
    from core import node
    peers=[{'name':'Tower','trusted':True},{'name':'Tower','trusted':True},
           {'name':'Sleeping','trusted':True},{'name':'Stranger','trusted':False}]
    monkeypatch.setattr(node,'_daemon_get',lambda host,port,path:{'self':{'name':'Laptop'},'peers':peers} if path=='/v1/nodes' else {'jobs':[job(1)]})
    calls=[]
    def remote(peer,path):
        calls.append(peer['name'])
        if peer['name']=='Sleeping':raise TimeoutError('offline')
        return {'jobs':[job(2,'Remote film','running')]}
    monkeypatch.setattr(node,'_file_peer_json',remote)
    result=node._fabric_import_jobs('localhost',7332)
    assert sorted(calls)==['Sleeping','Tower']
    assert {row['node'] for row in result['jobs']}=={'Laptop','Tower'}
    assert result['unavailable']==[{'node':'Sleeping','error':'offline'}]


def test_watch_without_active_work_shows_latest_result(plain,capsys):
    request=Mock(return_value={'jobs':[job(1,'Latest Album'),job(2,'Older Album')]})
    assert disc_ui.main(['watch'],lambda node:request,None,None)==0
    assert 'Latest Album' in capsys.readouterr().out


def test_cancel_needs_explicit_selection(plain,capsys):
    request=Mock()
    assert disc_ui.main(['cancel'],lambda node:request,None,None)==1
    request.assert_not_called()
    assert 'requires an album name' in capsys.readouterr().err


def test_interactive_album_picker_returns_chosen_album(monkeypatch):
    monkeypatch.setattr(disc_ui.sys.stdin,'isatty',lambda:True)
    monkeypatch.setattr(disc_ui.sys.stdout,'isatty',lambda:True)
    monkeypatch.setattr('builtins.input',lambda prompt:'2')
    request=Mock(return_value={'jobs':[job(1,'First'),job(2,'Second')]})
    assert disc_ui.resolve_job(request,'','deliver')==f'{2:032x}'


def test_interactive_watch_renders_all_active_work_and_restores_terminal(monkeypatch):
    class Terminal(io.StringIO):
        def fileno(self):return 0
    incoming=Terminal();outgoing=Terminal()
    monkeypatch.setattr(disc_ui.sys,'stdin',incoming)
    monkeypatch.setattr(disc_ui.sys,'stdout',outgoing)
    monkeypatch.setattr(disc_ui.termios,'tcgetattr',lambda fd:['saved'])
    restore=Mock();monkeypatch.setattr(disc_ui.termios,'tcsetattr',restore)
    monkeypatch.setattr(disc_ui.tty,'setcbreak',lambda fd:None)
    request=Mock(return_value={'jobs':[job(1,'Ripping',state='running'),job(2,'Delivering',delivery='running')]})
    assert disc_ui.watch_all(request,lambda fd,timeout:'esc',lambda text,width:text)==0
    assert 'Ripping' in outgoing.getvalue() and 'Delivering' in outgoing.getvalue()
    restore.assert_called_once_with(0,disc_ui.termios.TCSADRAIN,['saved'])


def test_idle_fabric_monitor_sees_reconnecting_work(monkeypatch):
    class Terminal(io.StringIO):
        def fileno(self):return 0
    monkeypatch.setattr(disc_ui.sys,'stdin',Terminal())
    output=Terminal();monkeypatch.setattr(disc_ui.sys,'stdout',output)
    monkeypatch.setattr(disc_ui.termios,'tcgetattr',lambda fd:['saved'])
    monkeypatch.setattr(disc_ui.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(disc_ui.tty,'setcbreak',lambda fd:None)
    request=Mock(side_effect=[{'fabric':True,'jobs':[]},
                             {'fabric':True,'jobs':[dict(job(1,'Reconnected film','running'),node='Tower')]}])
    keys=iter([None,'esc'])
    assert disc_ui.watch_all(request,lambda *args:next(keys),lambda text,width:text)==0
    assert request.call_count==2 and 'Tower · Reconnected film' in output.getvalue()


@pytest.mark.parametrize('theme',('paper','neon','slate'))
def test_wrapped_progress_preserves_metrics_and_logical_row_inks(monkeypatch,theme):
    import re
    monkeypatch.setenv('LOOK_TERMINAL_THEME',theme)
    colors=disc_ui.interface_colors()
    first=dict(job(1,'A very long movie title with many words','running'),
               stage='Saving available titles to MKV files',percent=52.3,
               elapsed_seconds=120,estimated_remaining_seconds=180)
    second=dict(first,title='Another long title with several words')
    for width in (20,40,80):
        rows=disc_ui.progress_lines([first],width,colors)
        plain=[re.sub(r'\x1b\[[0-9;]*m','',row) for row in rows]
        assert all(len(row)<=width-1 for row in plain)
        assert '52.3%' in ' '.join(plain) and 'ETA ~3:00' in ' '.join(plain)
        inks=[re.findall(r'\x1b\[38;2;[0-9;]+m',row)[0] for row in rows]
        assert len(set(inks))==1
        following=disc_ui.progress_lines([first,second],width,colors)[len(rows):]
        assert len(set(re.findall(r'\x1b\[38;2;[0-9;]+m',row)[0] for row in following))==1
        assert re.findall(r'\x1b\[38;2;[0-9;]+m',following[0])[0]!=inks[0]


def test_wrapping_uses_cells_and_handles_paths_controls_and_newlines():
    import unicodedata
    text='电影e\u0301 /a/very/long/unbroken/path\nnext\x1bline'
    rows=disc_ui.wrapped_lines(text,9)
    for row in rows:
        cells=sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in {'W','F'} else 1 for c in row)
        assert cells<=8 and '\x1b' not in row
    assert '电影e\u0301/a/very/long/unbroken/pathnext?line'==''.join(rows).replace(' ','')


def test_progress_viewport_keeps_header_footer_and_scrolls_to_metrics(monkeypatch):
    monkeypatch.setenv('LOOK_TERMINAL_THEME','paper')
    colors=disc_ui.interface_colors();lines=[f'line {n}' for n in range(20)]
    offset=disc_ui.progress_scroll('shiftdown',0,4)
    frame,offset=disc_ui.progress_frame(lines,'IMPORT',40,6,offset,lambda text,width:text,colors)
    assert len(frame)==6 and frame[1:5]==lines[4:8] and '5–8/20' in frame[0]
    assert disc_ui.progress_scroll('shiftup',offset,4)==0
    assert disc_ui.progress_frame(lines,'IMPORT',40,6,999,lambda text,width:text,colors)[1]==16


@pytest.mark.parametrize('single',(False,True))
def test_watch_wraps_in_a_narrow_terminal_and_scrolls(monkeypatch,single):
    class Terminal(io.StringIO):
        def fileno(self):return 0
    output=Terminal()
    monkeypatch.setattr(disc_ui.sys,'stdin',Terminal())
    monkeypatch.setattr(disc_ui.sys,'stdout',output)
    monkeypatch.setattr(disc_ui.termios,'tcgetattr',lambda fd:['saved'])
    monkeypatch.setattr(disc_ui.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(disc_ui.tty,'setcbreak',lambda fd:None)
    monkeypatch.setattr(disc_ui.shutil,'get_terminal_size',lambda default:(32,6))
    row=dict(job(1,'An exceptionally long film title','running'),
             stage='Saving available titles to MKV files',percent=67.8,
             elapsed_seconds=300,estimated_remaining_seconds=60)
    request=Mock(return_value={'job':row} if single else {'jobs':[row],'fabric':True})
    keys=iter(['shiftdown','esc'])
    reader=lambda *args:next(keys)
    assert (disc_ui.watch(row['id'],request,reader,lambda text,width:text) if single else
            disc_ui.watch_all(request,reader,lambda text,width:text))==0
    assert request.call_count==2 and '67.8%' in output.getvalue() and 'ETA ~1:00' in output.getvalue()
