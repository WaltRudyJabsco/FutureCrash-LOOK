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
