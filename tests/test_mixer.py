import importlib.util
import io
import json
from pathlib import Path
from unittest.mock import Mock
import pytest
from core import mixer_web,maintenance

ROOT=Path(__file__).resolve().parents[1]
ASSETS=list(mixer_web.ASSETS)


def test_catalog_exposes_audio_references_without_paths_or_hidden_items():
    data={'entries':[{'id':'one','node':'music owner','path':'/private/music/something.flac','tags':{'title':'A <record>','artist':'An artist'},'duration':123},
                     {'id':'two','node':'music owner','path':'/private/a.webm','media_type':'video'},
                     {'id':'three','path':'/private/a.mp3','offline':True},
                     {'id':'four','path':'/private/a.wav','fabric_hidden_by':['user']},
                     {'id':'one','node':'music owner','path':'/duplicate.flac'}]}
    result=mixer_web.catalog(data)
    assert result['total']==1 and result['entries'][0]['title']=='A <record>'
    assert 'private/' not in json.dumps(result)
    assert result['entries'][0]['audio_url']=='/api/media/browser?node=music+owner&id=one'


def test_asset_paths_are_allowlisted_and_all_assets_exist():
    for asset in ASSETS:assert mixer_web.asset(asset)
    with pytest.raises(ValueError):mixer_web.asset('../../.ssh/config')
    with pytest.raises(ValueError):mixer_web.asset('/etc/passwd')


@pytest.mark.parametrize('surface',['signal-window','albert'])
@pytest.mark.parametrize('path',['/mix','/mix/assets/mercury-mix-worklet.js','/api/mix/library'])
def test_every_mixer_route_requires_the_existing_endpoint_authorization(surface,path,monkeypatch):
    spec=importlib.util.spec_from_file_location('mix_host_'+surface,ROOT/surface/'server.py');server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)
    handler=(server.App if surface=='signal-window' else server.Handler).__new__(server.App if surface=='signal-window' else server.Handler)
    handler.path=path;handler._require_endpoint=Mock(return_value=False)
    get=Mock();monkeypatch.setattr(mixer_web,'handle',get)
    handler.do_GET();handler._require_endpoint.assert_called_once_with('lo.use');get.assert_not_called()


def test_gateway_serves_local_worklet_with_security_headers():
    handler=Mock();handler.path='/mix/assets/mercury-mix-worklet.js';handler.wfile=io.BytesIO()
    mixer_web.handle(handler,'http://127.0.0.1:7332')
    assert b"registerProcessor" in handler.wfile.getvalue() and b"mercury-deck" in handler.wfile.getvalue()
    assert ('Content-Type','text/javascript; charset=utf-8') in [c.args for c in handler.send_header.call_args_list]
    assert any(c.args[0]=='Content-Security-Policy' for c in handler.send_header.call_args_list)


def test_installers_and_managed_updates_include_shared_assets_and_launcher():
    for name in ASSETS:
        for surface in ['signal-window','albert']:
            assert name in (ROOT/surface/'install.sh').read_text()
            assert maintenance.allowed('.local/share/'+surface+'/'+name)
    assert 'look/mixer.py' in (ROOT/'install-look.sh').read_text()


def test_assistant_catalog_is_read_only_and_uses_actual_track_references(monkeypatch):
    import mixer,fabric_files
    monkeypatch.setattr(fabric_files,'request',lambda *a,**k:{'entries':[{'path':'/music/tune.mp3','node':'owner','id':'track','title':'Evening'}]})
    value=json.loads(mixer.run_tool({'query':'evening'}))
    assert value['mixer_path']=='/mix' and value['entries'][0]['id']=='track'
    with pytest.raises(ValueError):mixer.run_tool({'action':'play'})


def test_search_and_paging_cover_items_beyond_the_first_page():
    rows=[{'id':str(i),'node':'owner','path':'/music/'+str(i)+'.mp3','title':'Track '+str(i)} for i in range(350)]
    rows.append({'id':'last','node':'owner','path':'/music/z.mp3','title':'Zebra Song'})
    value=mixer_web.catalog({'entries':rows},'zebra')
    assert value['total']==1 and value['entries'][0]['id']=='last'
    page=mixer_web.catalog({'entries':rows},offset=200)
    assert len(page['entries'])==151 and not page['has_more']


def test_launcher_recognizes_an_authenticated_running_host(monkeypatch):
    import mixer
    from urllib.error import HTTPError
    def authenticated(*args,**kwargs):
        raise HTTPError('http://localhost',401,'Sign in',{},None)
    monkeypatch.setattr(mixer.urllib.request,'urlopen',authenticated)
    assert mixer.origin('signal')==mixer.HOSTS['signal']


def test_library_gateway_passes_query_and_offset_and_rejects_invalid_input(monkeypatch):
    mixer_web._CACHE.clear()
    data={'entries':[{'id':str(i),'node':'owner','path':'/music/record.mp3','artist':'Artist'} for i in range(220)]}
    response=Mock();response.__enter__=Mock(return_value=io.BytesIO(json.dumps(data).encode()));response.__exit__=Mock(return_value=False)
    monkeypatch.setattr(mixer_web.urllib.request,'urlopen',lambda *a,**k:response)
    handler=Mock();handler.path='/api/mix/library?q=artist&offset=200';handler.wfile=io.BytesIO()
    mixer_web.handle(handler,'http://test-node')
    value=json.loads(handler.wfile.getvalue())
    assert len(value['entries'])==20 and value['total']==220 and value['offset']==200
    handler.path='/api/mix/library?offset=-1'
    with pytest.raises(ValueError):mixer_web.handle(handler,'http://test-node')
    mixer_web._CACHE.clear()


def test_installer_audio_assets_are_individual_existing_source_arguments():
    import shlex
    for surface,variable in [('signal-window','SOURCE_DIR'),('albert','SRC')]:
        line=next(line for line in (ROOT/surface/'install.sh').read_text().splitlines() if line.startswith('install ') and 'mercury-mix.html' in line)
        args=shlex.split(line)
        sources=args[3:-1]
        assert len(sources)==len(ASSETS)
        for source in sources:
            path=Path(source.replace('$'+variable,str(ROOT/surface)))
            assert path.is_file(),source
