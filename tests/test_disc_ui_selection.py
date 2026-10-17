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


def test_tv_setup_uses_tv_destination_all_titles_and_review_edit(monkeypatch):
    monkeypatch.setattr(media_storage,'settings',lambda:{'node':'local','root':'~/Media'})
    inventory={'drives':[{'id':'drive','kind':'dvd','disc':'BOOSH'}],'tools':{'makemkvcon':'mk'}}
    request=Mock(return_value={'kind':'dvd','engine':'makemkv','titles':[{'index':'0','duration':'30:00'}],'metadata':{'title':'Boosh'}})
    visits={}
    def prompt(label,default=''):
        visits[label]=visits.get(label,0)+1
        if label.startswith('Search TVmaze'):return 'n'
        if label.startswith('Library category'):return 'tv'
        if label.startswith('Series'):return 'Boosh Season 1 Disc 1' if visits[label]==1 else 'The Mighty Boosh S1 Disc 1'
        if label=='Start or edit':return 'm' if visits[label]==1 else 'y'
        return default
    destinations=[]
    result=disc_ui.import_options(request,inventory,'drive',prompt,lambda label,default:destinations.append(default) or default)
    assert result['category']=='tv' and result['title_index']=='all'
    assert result['title']=='The Mighty Boosh S1 Disc 1'
    assert destinations==['~/Media/tv','~/Media/tv']
    assert request.call_count==1 and request.call_args.args[0]=='scan'


def test_escape_goes_back_and_cancels_before_submission(monkeypatch):
    monkeypatch.setattr(media_storage,'settings',lambda:{'node':'local','root':'~/Media'})
    inventory={'drives':[{'id':'drive','kind':'dvd'}],'tools':{'makemkvcon':'mk'}}
    request=Mock(return_value={'kind':'dvd','engine':'makemkv','titles':[{'index':'0'}],'metadata':{'title':'Film'}})
    visits=[]
    def prompt(label,default=''):
        visits.append(label)
        if label.startswith('Library category'):raise disc_ui.ImportBack()
        if label.startswith('Disc kind') and len(visits)>1:raise disc_ui.ImportBack()
        return default
    assert disc_ui.import_options(request,inventory,'drive',prompt,Mock()) is None
    assert not request.called
    assert len(visits)==3


def test_destination_escape_returns_to_name_then_accepts_manual_folder(monkeypatch):
    monkeypatch.setattr(media_storage,'settings',lambda:{'node':'local','root':'~/Media'})
    inventory={'drives':[{'id':'drive','kind':'dvd'}],'tools':{'makemkvcon':'mk'}}
    request=Mock(return_value={'kind':'dvd','engine':'makemkv','titles':[{'index':'0'}],'metadata':{'title':'Show'}})
    labels=[];paths=[]
    def prompt(label,default=''):
        labels.append(label)
        if label.startswith('Search TVmaze'):return 'n'
        if label.startswith('Library category'):return 'tv'
        return default
    def path_prompt(label,default):
        paths.append(default)
        if len(paths)==1:raise disc_ui.ImportBack()
        return '/Volumes/My Library/tv'
    result=disc_ui.import_options(request,inventory,'drive',prompt,path_prompt)
    assert result['destination']=='/Volumes/My Library/tv'
    assert sum(label.startswith('Series') for label in labels)==2
    assert result['preferences'] is None


def test_failed_scan_does_not_retry_without_explicit_choice(monkeypatch):
    inventory={'drives':[{'id':'drive','kind':'dvd'}],'tools':{'makemkvcon':'mk'}}
    request=Mock(side_effect=RuntimeError('scan timeout'))
    def prompt(label,default=''):return default
    assert disc_ui.import_options(request,inventory,'drive',prompt,Mock()) is None
    assert request.call_count==1


def test_failed_scan_retries_only_on_r(monkeypatch):
    monkeypatch.setattr(media_storage,'settings',lambda:{'node':'local','root':'~/Media'})
    inventory={'drives':[{'id':'drive','kind':'dvd'}],'tools':{'makemkvcon':'mk'}}
    request=Mock(side_effect=[RuntimeError('scan timeout'),{'kind':'dvd','engine':'makemkv',
        'titles':[{'index':'0','duration':'30:00'}],'metadata':{'title':'My disc'}}])
    def prompt(label,default=''):
        if label.startswith('r retry'):return 'r'
        if label.startswith('Library category'):return 'tv'
        if label.startswith('Search TVmaze'):return 'n'
        return default
    result=disc_ui.import_options(request,inventory,'drive',prompt,lambda label,default:default)
    assert result['title']=='My disc' and request.call_count==2


def test_columns_keep_progress_and_time_visible_with_long_titles():
    import re
    row=job(1,'A long Cousteau title '*15,'running');row.update(percent=4.5,elapsed_seconds=123,stage='saving MKV')
    lines=disc_ui.workbench_lines({'drives':[],'tools':{}},[row],0,80,30,True,disc_ui.interface_colors())
    plain=[re.sub(r'\x1b\[[0-9;]*m','',line) for line in lines]
    selected=next(line for line in plain if line.startswith('› '))
    assert 'running' in selected and '4.5%' in selected and '2:03' in selected
    assert any('SELECTED ·' in line for line in plain)
    assert all(len(line)<80 for line in plain if line.startswith('› '))


def test_zero_elapsed_does_not_restart_failed_clock(monkeypatch):
    row=job(1,state='failed');row.update(created=1,elapsed_seconds=0,percent=4,estimated_remaining_seconds=999)
    monkeypatch.setattr(disc_ui.time,'time',lambda:100000)
    assert disc_ui.elapsed_seconds(row)==0
    assert 'ETA' not in disc_ui.summary(row)


def test_import_workbench_pane_keeps_jobs_untouched(monkeypatch,capsys):
    import textwrap
    from pathlib import Path
    monkeypatch.setattr(disc_ui.sys,'stdin',Mock(fileno=lambda:0))
    monkeypatch.setattr(disc_ui.termios,'tcgetattr',lambda *a:[])
    monkeypatch.setattr(disc_ui.termios,'tcsetattr',lambda *a:None)
    monkeypatch.setattr(disc_ui.tty,'setcbreak',lambda *a:None)
    pane=Mock(return_value='Shell opened beside LOOK');monkeypatch.setattr(disc_ui.terminal_style,'open_pane',pane)
    def request(action,payload):
        assert action in {'drives','jobs'}
        return {'drives':[],'tools':{}} if action=='drives' else {'jobs':[]}
    keys=iter(['W','esc'])
    assert disc_ui.workspace(request,lambda *a:next(keys),lambda text,width:'\n'.join(textwrap.wrap(text,width-1)))==0
    pane.assert_called_once_with(Path.cwd())
    assert 'close focused pane' in ' '.join(capsys.readouterr().out.split())


def test_cd_review_carries_toc_and_manual_disc_number(monkeypatch,capsys):
    monkeypatch.setattr(media_storage,'settings',lambda:{'node':'local','root':'~/Media'})
    toc={'disc_id':'inserted','toc':'1 2 300 150 225','count':2}
    inventory={'drives':[{'id':'drive','kind':'cd'}],'tools':{}}
    release={'title':'Box set','artist':'Band','disc':2,'disc_count':4,'disc_match':True,'tracks':['One','Two']}
    def request(action,payload):
        assert action=='scan'
        return {'kind':'cd','tracks':2,'toc':toc,'metadata':{},'releases':[release]}
    result=disc_ui.import_options(request,inventory,'drive',lambda label,default='':default,lambda label,default:default)
    assert result['toc']==toc
    assert result['metadata']['disc']==2 and result['metadata']['disc_count']==4
    text=capsys.readouterr().out
    assert 'Disc 2 of 4' in text and 'disc ID matched' in text and 'One / Two' in text
