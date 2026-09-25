from pathlib import Path
import importlib.util, sys

ROOT=Path(__file__).resolve().parents[1]


def load_node():
    sys.path.insert(0,str(ROOT/'core'))
    spec=importlib.util.spec_from_file_location('fcl_node_649',ROOT/'core/node.py')
    mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod); return mod


def test_browser_endpoint_registry_and_audio_queue(monkeypatch):
    node=load_node()
    monkeypatch.setattr(node.ENDPOINT_AUTH,'list',lambda:{'trusted':[{'endpoint_id':'ep-test'}],'sessions':[]})
    node.BROWSER_ENDPOINTS.clear(); node.BROWSER_ACTIONS.clear()
    row=node._browser_presence('ep-test','iPad',['audio.speak','audio.output'],'albert',{'device':'iPad'})
    assert row['label']=='iPad'
    assert node._endpoint_match('ipad',row)
    item=node._browser_queue('ep-test','audio.speak',{'text':'Dinner is ready'})
    assert item['action']=='audio.speak'
    actions=node._browser_poll('ep-test')
    assert actions[0]['payload']['text']=='Dinner is ready'
    assert node._browser_poll('ep-test')==[]


def test_surfaces_advertise_and_execute_browser_speech():
    signal=(ROOT/'signal-window/app.js').read_text()
    albert=(ROOT/'albert/index.html').read_text()
    aserver=(ROOT/'albert/server.py').read_text()
    sserver=(ROOT/'signal-window/server.py').read_text()
    for text in (signal,albert):
        assert "audio.speak" in text
        assert 'SpeechSynthesisUtterance' in text
        assert '/api/endpoint/poll' in text
    assert 'EndpointAuth' in aserver
    assert '/v1/endpoints/presence' in aserver
    assert '/v1/endpoints/presence' in sserver


def test_release_649_contract():
    assert (ROOT/'VERSION').read_text().strip()=='6.5.0'
    node=(ROOT/'core/node.py').read_text()
    assert 'VERSION = "6.5.0"' in node
    assert 'RELEASE_NAME = "LAST MILE"' in node
