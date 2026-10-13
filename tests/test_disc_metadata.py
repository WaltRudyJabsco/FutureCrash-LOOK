import json
import pytest
from look import disc_metadata,disc_ui,disc_import,media_storage,player_visuals


def test_disc_hint_detects_format_and_keeps_numeric_movie_titles(tmp_path):
    (tmp_path/'VIDEO_TS').mkdir()
    assert disc_metadata.disc_hint({'mount':str(tmp_path),'disc':'PCU43_A'})=={'kind':'dvd','title':'PCU'}
    assert disc_metadata.disc_hint({'disc':'2001_A_SPACE_ODYSSEY'})['title']=='2001 A SPACE ODYSSEY'
    (tmp_path/'VIDEO_TS').rmdir();(tmp_path/'BDMV/META/DL').mkdir(parents=True)
    (tmp_path/'BDMV/META/DL/bdmt_eng.xml').write_text('<root xmlns="urn:disc"><name>Actual Movie</name></root>')
    assert disc_metadata.disc_hint({'mount':str(tmp_path),'disc':'MANUFACTURING_CODE'})=={'kind':'bluray','title':'Actual Movie'}


def test_movie_lookup_excludes_nonfilms_and_retains_provenance(monkeypatch):
    responses=iter([{'search':[{'id':'Q1','label':'PCU','description':'1994 film'},
                              {'id':'Q2','label':'PCU','description':'university'}]},
                    {'entities':{'Q1':{'claims':{'P577':[{'mainsnak':{'datavalue':{'value':{'time':'+1994-01-01T00:00:00Z'}}}}]}}}}])
    monkeypatch.setattr(disc_metadata,'_json',lambda params:next(responses))
    assert disc_metadata.movies('PCU')['matches']==[{'title':'PCU','year':'1994','description':'1994 film','source':'https://www.wikidata.org/wiki/Q1'}]


def test_movie_match_is_confirmed_and_lookup_failure_preserves_name():
    answers=iter(['PCU','y','1'])
    title,metadata=disc_ui.movie_details(lambda *args:{'matches':[{'title':'PCU','year':'1994','source':'Wikidata'}]},lambda *args:next(answers),{})
    assert title=='PCU (1994)' and metadata['year']=='1994'
    answers=iter(['My Movie','y'])
    def failed(*args):raise OSError('offline')
    assert disc_ui.movie_details(failed,lambda *args:next(answers),{})[0]=='My Movie'
    answers=iter(['My Movie','n'])
    assert disc_ui.movie_details(failed,lambda *args:next(answers),{})[0]=='My Movie'


def test_scan_auto_detects_dvd_and_prefills_disc_name(tmp_path,monkeypatch):
    (tmp_path/'VIDEO_TS').mkdir()
    monkeypatch.setattr(disc_import,'selected_drive',lambda identifier:{'mount':str(tmp_path),'disc':'PCU43_A','makemkv_source':'disc:0'})
    monkeypatch.setattr(disc_import,'tool',lambda name:name)
    monkeypatch.setattr(disc_import,'query',lambda *args:'TINFO:0,9,0,"1:20:13"\nTINFO:1,9,0,"0:02:10"')
    scan=disc_import.inspect('drive','bluray')
    assert scan['kind']=='dvd' and scan['metadata']['title']=='PCU'
    assert disc_ui.feature_index(scan['titles'])=='0'


def test_existing_owner_library_is_reused_without_overriding_explicit_preference(tmp_path,monkeypatch):
    monkeypatch.setenv('HOME',str(tmp_path));config=tmp_path/'.config/look';config.mkdir(parents=True)
    (config/'media_library.json').write_text(json.dumps({'root':'/mounted/Library'}))
    assert media_storage.destination('dvd')=='/mounted/Library/movies'
    media_storage.settings({'node':'Tower','root':'/other/Library'})
    assert media_storage.destination('dvd')=='@Tower:/other/Library'


def test_workbench_confirms_movie_and_remembers_chosen_library(tmp_path,monkeypatch):
    import io
    class Terminal(io.StringIO):
        def fileno(self):return 0
    monkeypatch.setenv('HOME',str(tmp_path))
    monkeypatch.setattr(disc_ui.sys,'stdin',Terminal())
    monkeypatch.setattr(disc_ui.sys,'stdout',Terminal())
    monkeypatch.setattr(disc_ui.termios,'tcgetattr',lambda fd:['saved'])
    monkeypatch.setattr(disc_ui.termios,'tcsetattr',lambda *args:None)
    monkeypatch.setattr(disc_ui.tty,'setcbreak',lambda fd:None)
    # Workspace uses the installed top-level module names.
    import sys
    monkeypatch.setitem(sys.modules,'media_storage',media_storage)
    inventory={'drives':[{'id':'one','label':'USB drive','kind':'dvd'}],'tools':{'makemkvcon':'makemkvcon'}}
    started=[]
    def request(action,payload):
        if action=='drives':return inventory
        if action=='jobs':return {'jobs':[]}
        if action=='scan':return {'kind':'dvd','titles':[{'index':'0','duration':'1:20:13'}],'metadata':{'title':'PCU'}}
        if action=='movie-lookup':return {'matches':[{'title':'PCU','year':'1994','source':'https://www.wikidata.org/wiki/Q7118672'}]}
        if action=='start':started.append(payload);return {'ok':True}
        raise AssertionError(action)
    answers=iter(['','','','','','','/mounted/Library/movies','y',''])
    monkeypatch.setattr('builtins.input',lambda prompt:next(answers))
    from look import look_renderer
    monkeypatch.setattr(look_renderer,'prompt_line',lambda caption,**kwargs:(next(answers),False))
    keys=iter(['n','esc'])
    assert disc_ui.workspace(request,lambda *args:next(keys),lambda text,width:text)==0
    assert started[0]['title']=='PCU (1994)' and started[0]['title_index']=='0'
    assert started[0]['destination']=='/mounted/Library/movies'
    assert media_storage.settings()=={'node':'local','root':'/mounted/Library'}


@pytest.mark.parametrize('width,height',[(1,1),(12,4),(100,30)])
def test_firefly_garden_is_bounded_animated_and_pause_stable(width,height):
    mode=player_visuals.NAMES.index('Firefly Garden')+1
    a=player_visuals.frame(mode,width,height,0,True,7)
    b=player_visuals.frame(mode,width,height,2,True,7)
    assert len(a)==height and all(len(line)==width and line.isascii() for line in a)
    if width>1:assert a!=b
    assert player_visuals.frame(mode,width,height,2,False,7)==player_visuals.frame(mode,width,height,8,False,7)
