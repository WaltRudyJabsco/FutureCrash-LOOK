import json
from unittest.mock import Mock
import pytest
from core import dashboard
from test_browser_fabric_views import load


def local():
    return dashboard.local_snapshot({'identity':{'name':'host'},'runtime':{'ok':True},
        'inference':{'models':[{'name':'small-model','resident':True,'prompt':'secret'}]},
        'supervisor':{'active':{'phase':'inference','detail':'private chat'}},
        'maintenance':{'commit':'abc'}}, {'signal':{'state':'running','argv':'secret path'}},
        [{'seq':1,'ts':20,'type':'progress','phase':'inference','detail':'private prompt','data':{'token':'secret'}}])


def test_snapshot_omits_private_payloads():
    data=local();encoded=json.dumps(data)
    assert 'secret' not in encoded and 'private' not in encoded and 'argv' not in encoded
    assert data['events']==[{'seq':1,'ts':20,'type':'progress','phase':'inference'}]
    assert data['models'][0]['resident']


def test_fanout_trust_offline_cache_and_event_source():
    dashboard._CACHE.clear()
    calls=[]
    def fetch(url,timeout):
        calls.append(url)
        if url.startswith('offline'):raise OSError('private connection detail')
        return dict(local(),name='peer')
    peers=[{'name':'peer','trusted':True,'url':'peer'}, {'name':'offline','trusted':True,'url':'offline'},
           {'name':'stranger','trusted':False,'url':'stranger'}]
    result=dashboard.snapshot(local,peers,lambda p:p['url'],fetch)
    assert len(result['nodes'])==3 and not result['nodes'][2]['reachable']
    assert len(result['events'])==2 and len({e['id'] for e in result['events']})==2
    assert all('stranger' not in call for call in calls)
    assert dashboard.snapshot(lambda:pytest.fail('cache missed'),[],lambda p:'',fetch)==result
    assert len(calls)==2
    dashboard._CACHE.clear()


@pytest.mark.parametrize('surface',['signal-window','albert'])
@pytest.mark.parametrize('authorized',[True,False])
def test_dashboard_requires_browser_authorization(surface,authorized,monkeypatch):
    server=load(surface);handler=server.Handler.__new__(server.Handler)
    handler.path='/api/fabric/dashboard';handler._require_endpoint=Mock(return_value=authorized)
    handler._media_ticket_allows=Mock(return_value=False)
    send=Mock();setattr(handler,'json' if surface=='signal-window' else 'send_json',send)
    fetch=Mock(return_value={'host':'host','nodes':[],'events':[]})
    monkeypatch.setattr(server,'_node_get' if surface=='signal-window' else 'node_json',fetch)
    handler.do_GET()
    handler._require_endpoint.assert_called_once_with('lo.use')
    if authorized:
        fetch.assert_called_once_with('/v1/dashboard',timeout=10)
        assert send.call_args.args[1]['host']=='host'
    else:fetch.assert_not_called()

@pytest.mark.parametrize('surface',['signal-window','albert'])
def test_short_dashboard_url_redirects_to_shared_page(surface):
    server=load(surface);handler=server.Handler.__new__(server.Handler)
    handler.path='/dash';handler.send_response=Mock();handler.send_header=Mock();handler.end_headers=Mock()
    handler.do_GET()
    handler.send_response.assert_called_once_with(302)
    handler.send_header.assert_called_once_with('Location','/fabric.html')
