import contextlib
import importlib.machinery
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from core.browser_presentations import candidates,Presentations
from look import lo_engine

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def core(monkeypatch):
    loader=importlib.machinery.SourceFileLoader('image_delivery_lk',str(ROOT/'look/lk'))
    spec=importlib.util.spec_from_loader(loader.name,loader)
    module=importlib.util.module_from_spec(spec);sys.modules[loader.name]=module;loader.exec_module(module)
    monkeypatch.setattr(module,'_activity',lambda *args:contextlib.nullcontext())
    world=SimpleNamespace(begin_action=lambda *args,**kw:{},record_receipt=Mock())
    monkeypatch.setattr(module,'_world_state',lambda:world)
    monkeypatch.setattr(module,'_audit_receipt',Mock())
    monkeypatch.setattr(module,'_live_state_after_receipt',Mock())
    return module


@pytest.mark.parametrize('receipt',['IMAGE FAILED · timed out','Image generation unavailable: no reachable ComfyUI service.','IMAGE FAILED · Workflow could not be read'])
def test_failed_image_generation_is_not_typed_as_success(core,receipt):
    typed=core._normalize_tool_result('generate_image',receipt)
    assert typed.ok is False and typed.status=='failed'


def test_generated_file_receipt_reaches_native_browser_artifact(core,tmp_path,monkeypatch):
    image=tmp_path/'generated reef 日本語.png';image.write_bytes(b'\x89PNG\r\n\x1a\n')
    receipt='IMAGE OK · 1 image(s) · '+str(image)+' · VRAM released'
    monkeypatch.setattr(core,'_run_capability_tool',lambda *args:receipt)
    class Driver:
        @staticmethod
        def ollama_chat(**kwargs):
            text,ok,_=core._lo_image_turn({'prompt':'a reef'},tmp_path,'workspace',kwargs['events'])
            kwargs['events'].emit('response',text=text)
            kwargs['events'].emit('request_done',status='ok' if ok else 'failed')
            return 0
    monkeypatch.setattr(lo_engine,'_load_core',lambda:Driver())
    monkeypatch.setattr(lo_engine,'_load_web_key',lambda:None)
    response=lo_engine.chat_once('generate an image of a reef',workspace=tmp_path)
    assert response['text']==receipt
    done=next(row for row in response['events'] if row['event']=='tool_done')
    assert done['tool']=='generate_image' and done['status']=='ok' and done['result']==receipt
    paths=candidates(response['text'],response['events'])
    assert paths==[image]
    store=Presentations();artifact=store.present(paths[0])
    assert artifact['type']=='image/png'
    assert store.get(artifact['url'].rsplit('/',1)[-1]).read_bytes()==image.read_bytes()


def test_failed_fast_image_turn_emits_failure_and_original_error(core,tmp_path,monkeypatch):
    monkeypatch.setattr(core,'_run_capability_tool',lambda *args:'IMAGE FAILED · no workflow')
    collector=lo_engine.EventCollector()
    reply,ok,_=core._lo_image_turn({'prompt':'reef'},tmp_path,'workspace',collector)
    assert not ok and reply=='IMAGE FAILED · no workflow'
    assert collector.rows[-1]['status']=='failed'
    assert candidates(reply,collector.rows)==[]


def test_direct_image_answer_uses_real_receipt_instead_of_generic_success():
    source=(ROOT/'look/lk').read_text()
    fast=source[source.index('        image_action=_jev_image_intent(prompt)'):source.index('        # Referential JEV actions')]
    assert 'reply=str(image_result)' in fast and 'Generated the image.' not in fast


@pytest.mark.parametrize('ok',[True,False])
def test_real_lo_image_fast_path_returns_artifact_or_truthful_failure(core,tmp_path,monkeypatch,ok):
    image=tmp_path/'real turn.png';image.write_bytes(b'\x89PNG\r\n\x1a\n')
    receipt='IMAGE OK · 1 image(s) · '+str(image) if ok else 'IMAGE FAILED · worker unavailable'
    monkeypatch.setattr(core,'_run_capability_tool',lambda *args:receipt)
    monkeypatch.setattr(core,'_save_recent_exchange',Mock())
    monkeypatch.setattr(core,'_lo_latest_command_action',lambda:None)
    monkeypatch.setattr(core,'_lo_cognition_route',lambda *args,**kw:(_ for _ in ()).throw(AssertionError('image command reached model inference')))
    collector=lo_engine.EventCollector()
    assert core.ollama_chat.__wrapped__(initial_prompt='generate an image of a reef',access_profile='workspace',workspace_override=tmp_path,one_shot=True,events=collector)==0
    assert next(row['text'] for row in collector.rows if row['event']=='response')==receipt
    assert next(row['status'] for row in collector.rows if row['event']=='request_done')==('ok' if ok else 'failed')
    assert candidates(receipt,collector.rows)==([image] if ok else [])
