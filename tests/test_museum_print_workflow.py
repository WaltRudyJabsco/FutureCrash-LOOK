import json
from unittest.mock import Mock
import pytest
import museum_assistant
import museum_desk
import printing


@pytest.fixture
def client(monkeypatch,tmp_path):
    image=tmp_path/'art.jpg';image.write_bytes(b'image fixture')
    fake=Mock()
    fake.node='owner'
    fake.snapshot.return_value={'items':[{'id':'aic-1','title':'Garden','artist':'Renoir','downloaded':True},{'id':'met-2','title':'Unavailable','downloaded':False}]}
    fake.image.return_value=image
    monkeypatch.setattr(museum_desk,'Client',lambda _:fake)
    monkeypatch.setattr(museum_desk,'preference',lambda:'owner')
    return fake


def test_random_uses_catalog_not_literal_search(client):
    result=json.loads(museum_assistant.run_tool('museum_search',{'query':'random','random':True}))
    client.snapshot.assert_called_once_with('')
    assert [r['id'] for r in result['items']]==['aic-1']


def test_artist_surname_is_passed_to_search(client):
    museum_assistant.run_tool('museum_search',{'query':'Renoir'})
    client.snapshot.assert_called_once_with('Renoir')


def test_artwork_print_uses_existing_image_and_caption_pipeline(client,monkeypatch):
    prepare=Mock(return_value={'id':'plan','node':'owner','destination':'Desk'})
    send=Mock(return_value={'state':'queued'})
    monkeypatch.setattr(printing,'prepare_file',prepare)
    monkeypatch.setattr(printing,'request',send)
    result=printing.quick_artwork('Desk','aic-1')
    assert result['artwork']['artist']=='Renoir'
    assert 'Renoir' in str(prepare.call_args.kwargs['caption'])
    assert prepare.call_args.kwargs['copies']==1
    send.assert_called_once_with('send','owner',ident='plan',confirm=True)
    with pytest.raises(ValueError):printing.quick_artwork('Desk','met-2')
    assert send.call_count==1


def test_artwork_tool_requires_print_authority_and_never_retries(tmp_path,monkeypatch):
    send=Mock(return_value={'state':'queued'})
    monkeypatch.setattr(printing,'quick_artwork',send)
    args={'queue':'Desk','artwork_id':'aic-1'}
    with pytest.raises(ValueError):printing.run_tool('print_artwork',args,tmp_path,'Preview artwork on Desk',{})
    turn={}
    printing.run_tool('print_artwork',args,tmp_path,'Print a Renoir image on Desk',turn)
    with pytest.raises(ValueError):printing.run_tool('print_artwork',args,tmp_path,'Print a Renoir image on Desk',turn)
    send.assert_called_once_with('Desk','aic-1')


def test_museum_print_route_exposes_actual_image_action():
    from core import cognition
    route=cognition.analyze('Print a Renoir image from the museum',use_openjev=False)
    assert {'museum_search','print_artwork'}<=set(route.allowed_tools)
    goal=cognition.new_goal('Print a Renoir image from the museum',route)
    assert cognition.assess(goal,successful_tools=['museum_search','print_artwork'],final_text='Queued')['satisfied']
