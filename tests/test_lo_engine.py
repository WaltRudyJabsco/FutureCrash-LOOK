import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from look import lo_engine


class FakeCore:
    def __init__(self):
        self.kwargs=None
    def ollama_chat(self, **kwargs):
        self.kwargs=kwargs
        kwargs['events'].emit('tool_start', tool='weather')
        kwargs['events'].emit('source_receipt', edge='WEATHER', source='Open-Meteo', confidence='DIRECT')
        kwargs['events'].emit('response', text='Hello from LO')
        kwargs['events'].emit('request_done', status='ok')
        return 0


class NativeLoEngineTests(unittest.TestCase):
    def test_structured_response_and_history(self):
        fake=FakeCore()
        with tempfile.TemporaryDirectory() as td, patch.object(lo_engine,'_load_core',return_value=fake), patch.object(lo_engine,'_load_web_key'):
            result=lo_engine.chat_once(
                'and in los angeles', profile='workspace', workspace=td,
                history=[{'role':'user','content':'weather in portland'}, {'role':'assistant','content':'Portland weather'}],
                interface_context='Signal browser',
            )
        self.assertEqual(result['text'],'Hello from LO')
        self.assertEqual(fake.kwargs['conversation_history'][0]['content'],'weather in portland')
        self.assertEqual(fake.kwargs['interface_context'],'Signal browser')
        self.assertEqual(result['events'][0]['tool'],'weather')
        self.assertEqual(result['events'][1]['edge'],'WEATHER')
        self.assertEqual(result['events'][1]['source'],'Open-Meteo')

    def test_presentation_environment_is_restored(self):
        fake=FakeCore()
        old=os.environ.pop('LOOK_PRESENTATION',None)
        try:
            with tempfile.TemporaryDirectory() as td, patch.object(lo_engine,'_load_core',return_value=fake), patch.object(lo_engine,'_load_web_key'):
                lo_engine.chat_once('hi',workspace=td)
            self.assertNotIn('LOOK_PRESENTATION',os.environ)
        finally:
            if old is not None: os.environ['LOOK_PRESENTATION']=old


if __name__=='__main__': unittest.main()


def test_direct_youtube_download_returns_receipt_without_inference(monkeypatch):
    import ytd
    calls=[]
    def request(action,**args):
        calls.append((action,args))
        return {'ok':True,'node':args['node'],'job':{'id':'job123','stage':'queued'}}
    monkeypatch.setattr(ytd,'request',request)
    monkeypatch.setattr(lo_engine,'_load_core',lambda:(_ for _ in ()).throw(AssertionError('must not need inference')))
    result=lo_engine.chat_once('Download this YouTube video to tower and add it to my media library: https://youtu.be/abc?si=share')
    assert calls==[('download',{'node':'tower','url':'https://youtu.be/abc?si=share'})]
    assert 'job123' in result['text'] and 'not ready to play' in result['text']
    assert result['events'][-1]['event']=='response'


def test_download_failure_has_actionable_response(monkeypatch):
    import ytd
    def fail(*a,**kw):raise RuntimeError('Unknown node 390')
    monkeypatch.setattr(ytd,'request',fail)
    result=lo_engine.chat_once('Download https://youtu.be/abc to 390')
    assert 'Unknown node 390' in result['text'] and 'not confirmed' in result['text']


def test_receipt_survives_model_missing_final_response(monkeypatch):
    class Core:
        def ollama_chat(self,**kwargs):
            kwargs['events'].emit('tool_done',tool='video_download',result='{"ok":true,"node":"tower","job":{"id":"saved-job","stage":"queued"}}')
            return 0
    monkeypatch.setattr(lo_engine,'_load_core',lambda:Core())
    monkeypatch.setattr(lo_engine,'_load_web_key',lambda:None)
    assert 'saved-job' in lo_engine.chat_once('a richer request')['text']


def test_accepted_download_survives_subsequent_inference_error(monkeypatch):
    class Core:
        def ollama_chat(self,**kwargs):
            kwargs['events'].emit('tool_done',tool='video_download',result='{"ok":true,"node":"tower","job":{"id":"durable-job","stage":"queued"}}')
            kwargs['events'].emit('error',error='inference timed out after tool')
            return 1
    monkeypatch.setattr(lo_engine,'_load_core',lambda:Core())
    monkeypatch.setattr(lo_engine,'_load_web_key',lambda:None)
    result=lo_engine.chat_once('a richer request')
    assert 'durable-job' in result['text'] and result['provenance']['edge']=='FABRIC'
    assert result['events'][-1]['event']=='response'


def test_conservative_profile_cannot_take_download_shortcut(monkeypatch):
    import ytd
    monkeypatch.setattr(ytd,'request',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('unauthorized write')))
    fake=FakeCore()
    monkeypatch.setattr(lo_engine,'_load_core',lambda:fake)
    monkeypatch.setattr(lo_engine,'_load_web_key',lambda:None)
    lo_engine.chat_once('download https://youtu.be/abc',profile='conservative')
    assert fake.kwargs['access_profile']=='conservative'
