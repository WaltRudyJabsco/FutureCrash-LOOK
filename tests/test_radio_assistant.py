import json
from unittest.mock import Mock
import pytest
import radio_assistant,museum_assistant,player_visuals,ytr
from test_media_request_regressions import lk

URL='https://youtu.be/abcdefghijk'
@pytest.mark.parametrize('text',['add this to YouTube Radio '+URL,URL+' add this to YTR','Can you please queue '+URL+' in our YouTube Radio?'])
def test_intent(text):assert radio_assistant.intent(text)=={'action':'add','url':URL}
@pytest.mark.parametrize('text',['do not add '+URL+' to YTR','how do I add a link to YouTube Radio?',URL,'play '+URL])
def test_unrelated_or_negated(text):assert radio_assistant.intent(text) is None

def test_add_tool_has_receipt_no_playback(monkeypatch,lk):
    request=Mock(return_value={'node':'owner','items':[{'id':'item','title':'Talk'}],'radio_added':{'id':'item','already_present':False}})
    monkeypatch.setattr(ytr,'Client',lambda owner:Mock(node=owner,request=request))
    answer=lk._lo_radio_direct('add '+URL+' to YTR','workspace')
    assert 'Talk' in answer and 'Playback has not started' in answer
    assert request.call_args.args==('add',)
    assert request.call_args.kwargs=={'url':URL}
    assert not lk._lo_requires_filesystem_action('save '+URL+' to YouTube Radio')
    with pytest.raises(ValueError):radio_assistant.run_tool('radio_add',{'url':URL},'summarize '+URL)
    request.return_value={'items':[]}
    assert 'verified add receipt' in lk._lo_radio_direct('add '+URL+' to YTR','workspace')

def test_tools_are_registered_and_routed(lk):
    names={row['function']['name'] for row in lk._lo_tools('workspace')}
    assert {'radio_add','radio_queue','museum_search'}<=names
    assert 'radio_add' not in {row['function']['name'] for row in lk._lo_tools('conservative')}
    route=lk._lo_cognition_route('add '+URL+' to YTR',use_openjev=False)
    assert 'radio_add' in route.allowed_tools
    route=lk._lo_cognition_route('show our museum paintings',use_openjev=False)
    assert 'museum_search' in route.allowed_tools

def test_new_visuals_bounded_and_pause():
    for name in ('Number Station','Prism Grid'):
        mode=player_visuals.NAMES.index(name)+1
        for width,height in ((1,1),(20,8),(120,40)):
            rows=player_visuals.frame(mode,width,height,12)
            assert len(rows)==height and all(len(row)==width for row in rows)
        assert player_visuals.frame(mode,80,24,0,False)==player_visuals.frame(mode,80,24,30,False)


def test_bridge_uses_direct_queue_tool_without_model(monkeypatch,lk):
    from look import lo_engine
    monkeypatch.setattr(lo_engine,'_load_core',lambda:lk)
    monkeypatch.setattr(lo_engine,'_load_web_key',lambda:None)
    monkeypatch.setattr(lk,'_save_recent_exchange',Mock())
    monkeypatch.setattr(lk,'_ensure_ollama_server',Mock(side_effect=AssertionError('No model needed')))
    monkeypatch.setattr(radio_assistant,'run_tool',lambda *args:json.dumps({'node':'owner','item':{'title':'Talk'},'already_present':False}))
    result=lo_engine.chat_once('add '+URL+' to YTR',profile='workspace')
    assert 'Playback has not started' in result['text']
    assert result['receipts'][0]['edge']=='YTR'
    assert result['route']['family']=='radio'


def test_museum_tool_returns_owner_scoped_image_link(monkeypatch):
    import museum_desk
    monkeypatch.setattr(museum_desk,'preference',lambda:'owner')
    monkeypatch.setattr(museum_desk.Client,'snapshot',lambda self,query:{'items':[{'id':'aic-1','title':'Landscape'}]})
    result=json.loads(museum_assistant.run_tool('museum_search',{'query':'landscape'}))
    assert result['owner']=='owner' and 'target=owner' in result['items'][0]['image_path']


def test_queue_noun_is_not_an_add_request():
    assert radio_assistant.intent('show my YouTube Radio queue')=={'action':'list'}
    assert radio_assistant.intent('what is in our YTR queue?')=={'action':'list'}
