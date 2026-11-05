import base64
import io
import json
import os
from pathlib import Path
from unittest.mock import Mock
import pytest
import printing
import print_desk
import look_renderer as renderer
from test_media_request_regressions import lk


class Terminal(io.StringIO):
    def isatty(self):return True


@pytest.mark.parametrize('key,marked_count,folder,expected',[('N',0,False,True),('N',1,False,True),('N',2,False,False),('N',0,True,False),('n',0,False,False)])
def test_shift_n_prints_single_selection_and_preserves_filer_context(tmp_path,monkeypatch,key,marked_count,folder,expected):
    target=tmp_path/'file $(literal).txt'
    if folder:target.mkdir()
    else:target.write_text('A note')
    marked={target} if marked_count else set()
    if marked_count==2:
        other=tmp_path/'other.txt';other.write_text('Other');marked.add(other)
    original=set(marked)
    terminal=Terminal();monkeypatch.setattr(renderer.sys,'stdin',Terminal());monkeypatch.setattr(renderer.sys,'stdout',terminal)
    monkeypatch.setattr(renderer,'NativePreviewController',Mock())
    monkeypatch.setattr(renderer.shutil,'get_terminal_size',lambda *a:os.terminal_size((80,24)))
    keys=iter([key,'Q']);monkeypatch.setattr(renderer,'read_key',lambda timeout=None,**kw:'' if timeout else next(keys))
    launch=Mock(return_value=Mock(returncode=0));monkeypatch.setattr(renderer.subprocess,'run',launch)
    monkeypatch.setattr(renderer,'preview_rows',lambda *a,**kw:[])
    renderer.pager(['file'],24,80,rebuild=lambda *a:['file'],browse_rebuild=lambda *a:['file'],candidates=lambda query:[target],initial_query='file',marked_set=marked,current_dir=tmp_path,force_interactive=True)
    assert bool(launch.called)==expected
    assert marked==original
    if expected:
        assert launch.call_args.args[0][-2:]==['_print-file',str(target)]
        assert 'N' in terminal.getvalue() and 'print' in terminal.getvalue()


def test_shared_file_pipeline_selects_receipt_text_and_pins_owner(tmp_path,monkeypatch):
    source=tmp_path/'todo.txt';source.write_text('Buy paper')
    destination={'id':'little','label':'Little Printer','routes':[{'name':'usb','node':'tower','status':'idle','profile':{'kind':'escpos'}}]}
    monkeypatch.setattr(printing,'destinations',lambda:{'printers':[destination],'local_node':'mac'})
    execute=Mock(return_value={'id':'a'*32,'node':'tower','state':'prepared'});monkeypatch.setattr(printing,'request',execute)
    result=printing.prepare_file('Little Printer',source)
    assert execute.call_args.args==('prepare','tower')
    assert execute.call_args.kwargs['kind']=='receipt-text'
    assert base64.b64decode(execute.call_args.kwargs['data'])==b'Buy paper'
    assert '--node tower --confirm' in result['send_command']
    source=tmp_path/'novel.pdf';source.write_bytes(b'%PDF-1.4')
    execute.reset_mock()
    with pytest.raises(ValueError,match='document printer'):printing.prepare_file('Little Printer',source)
    execute.assert_not_called()


@pytest.mark.parametrize('answer,cancelled,action',[('p',False,'send'),('',False,'discard'),('',True,'discard')])
def test_file_review_requires_explicit_print_or_discards(tmp_path,monkeypatch,answer,cancelled,action):
    source=tmp_path/'note.txt';source.write_text('note')
    monkeypatch.setattr(print_desk,'pick',lambda ui:{'id':'little'})
    plan={'id':'a'*32,'node':'tower','destination':'Little Printer'}
    monkeypatch.setattr(printing,'prepare_file',lambda *a,**kw:plan)
    monkeypatch.setattr(printing,'display',Mock())
    replies=iter([('',False),(answer,cancelled),('',False)])
    monkeypatch.setattr(renderer,'prompt_line',lambda *a,**kw:next(replies))
    request=Mock(return_value={'state':'queued'});monkeypatch.setattr(printing,'request',request)
    assert printing.selected_file(source,Mock())==0
    request.assert_called_once_with(action,'tower',ident=plan['id'],confirm=True)


def test_unsupported_file_never_opens_picker_or_uploads(tmp_path,monkeypatch):
    source=tmp_path/'project.mercury';source.write_bytes(b'project')
    picker=Mock();monkeypatch.setattr(print_desk,'pick',picker)
    request=Mock();monkeypatch.setattr(printing,'request',request)
    monkeypatch.setattr(renderer,'prompt_line',lambda *a:('',False))
    assert printing.selected_file(source,Mock())==1
    picker.assert_not_called();request.assert_not_called()
