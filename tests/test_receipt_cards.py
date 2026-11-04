import json
from pathlib import Path
from unittest.mock import Mock
import pytest
from core import receipt_cards,node,recovery
import receipt_desk


def test_cards_immutable_deduplicated_private_and_formatted(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    card=receipt_cards.create('Feature / Museum','Use lk museum\nLeft / Right: next artwork','feature','Test',event_key='release-1')
    assert receipt_cards.create('Changed','Different body',event_key='release-1')==card
    assert len(receipt_cards.listing('museum'))==1
    for width in (32,48):assert all(len(line)<=width for line in receipt_cards.render(card,width).splitlines())
    assert (receipt_cards.root()/(card['id']+'.json')).stat().st_mode&0o777==0o600
    with pytest.raises(ValueError):receipt_cards.get('../other')
    assert receipt_cards.root()/(card['id']+'.json') in recovery.sources(tmp_path)[0]


def test_node_receipt_api(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    api=object.__new__(node.API);api._file_target=lambda:(None,'');api.sendj=lambda code,value:(code,value)
    monkeypatch.setattr(node,'identity',lambda:{'name':'owner'})
    code,result=api._receipts_request({'action':'create','title':'Shopping','body':'Milk\nBread'})
    assert code==200 and 'Milk' in result['text']
    code,result=api._receipts_request({'action':'list'})
    assert len(result['items'])==1


def test_print_only_prepares_saved_card(monkeypatch,tmp_path):
    import printing
    monkeypatch.setattr(receipt_desk,'owner',lambda value=None:'owner')
    monkeypatch.setattr(receipt_desk,'request',lambda *args,**kwargs:{'text':'LOOK / FABRIC\nShopping\nMilk','receipt':{}})
    captured=[]
    def prepare(printer,path):captured.append((printer,path.read_text()));return {'id':'plan'}
    monkeypatch.setattr(printing,'prepare_file',prepare);monkeypatch.setattr(printing,'display',Mock())
    assert receipt_desk.main(['print','card','--printer','Little Printer'])==0
    assert captured==[('Little Printer','LOOK / FABRIC\nShopping\nMilk')]


def test_command_cards_use_reference(monkeypatch):
    call=Mock(return_value={'receipt':{}});monkeypatch.setattr(receipt_desk,'request',call)
    receipt_desk.command_card('ytr')
    assert 'lk ytr' in call.call_args.kwargs['body']
    assert call.call_args.kwargs['kind']=='command'


def test_original_transaction_command_remains_available(monkeypatch):
    import importlib.machinery,importlib.util,sys
    path=Path(__file__).resolve().parents[1]/'look/lk'
    loader=importlib.machinery.SourceFileLoader('receipt_compat_lk',str(path));spec=importlib.util.spec_from_loader(loader.name,loader)
    module=importlib.util.module_from_spec(spec);monkeypatch.setitem(sys.modules,loader.name,module);loader.exec_module(module)
    legacy=Mock(return_value=0);monkeypatch.setattr(module,'receipts',legacy)
    for args in (['lk','receipts','12'],['lk','receipts','transactions','12']):
        monkeypatch.setattr(sys,'argv',args);assert module.main()==0
    assert legacy.call_args.args==('12',) and legacy.call_count==2
