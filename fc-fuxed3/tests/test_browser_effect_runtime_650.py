from pathlib import Path
import importlib.util
import sys

ROOT=Path(__file__).resolve().parents[1]

def load_node():
    spec=importlib.util.spec_from_file_location('fcl_node_650',ROOT/'core/node.py')
    mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod); return mod

def test_browser_effect_receipt_lifecycle():
    node=load_node()
    node.BROWSER_ENDPOINTS.clear(); node.BROWSER_ACTIONS.clear(); node.BROWSER_RECEIPTS.clear()
    # Avoid coupling this unit test to persisted endpoint credentials.
    node.ENDPOINT_AUTH.list=lambda:{'trusted':[{'endpoint_id':'ep-test'}],'sessions':[]}
    node._browser_presence('ep-test','iPad',['audio.speak'],'albert',{})
    item=node._browser_queue('ep-test','audio.speak',{'text':'Dinner is ready'})
    assert node._browser_receipt_get(item['id'])['state']=='queued'
    actions=node._browser_poll('ep-test')
    assert actions[0]['id']==item['id']
    assert node._browser_receipt_get(item['id'])['state']=='delivered'
    node._browser_receipt('ep-test',item['id'],'waiting','waiting for browser audio unlock')
    assert node._browser_receipt_get(item['id'])['state']=='waiting'
    node._browser_receipt('ep-test',item['id'],'started','speech synthesis started')
    node._browser_receipt('ep-test',item['id'],'ended','speech synthesis ended')
    receipt=node._browser_receipt_get(item['id'])
    assert receipt['state']=='ended'
    assert [x['state'] for x in receipt['history']][-3:]==['waiting','started','ended']

def test_surfaces_share_audio_unlock_and_receipts():
    albert=(ROOT/'albert/index.html').read_text()
    signal=(ROOT/'signal-window/app.js').read_text()
    for text in (albert,signal):
        assert 'browserAudioUnlocked' in text
        assert 'pendingBrowserSpeech' in text
        assert '/api/endpoint/receipt' in text
        assert "'waiting'" in text
        assert "'started'" in text
        assert "'ended'" in text
        assert 'touchend' in text

def test_surface_servers_proxy_effect_receipts():
    assert "/api/endpoint/receipt" in (ROOT/'albert/server.py').read_text()
    assert "/v1/endpoints/receipt" in (ROOT/'albert/server.py').read_text()
    assert "/api/endpoint/receipt" in (ROOT/'signal-window/server.py').read_text()
    assert "/v1/endpoints/receipt" in (ROOT/'signal-window/server.py').read_text()
