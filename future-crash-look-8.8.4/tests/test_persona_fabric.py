import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
LO=ROOT/'look'/'lo_engine.py'
FC=ROOT/'future-crash'/'future_crash.py'


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod


class PersonaFabricTests(unittest.TestCase):
    def test_oracle_and_pirate_are_registered(self):
        source=(ROOT/'look'/'lk').read_text(encoding='utf-8')
        self.assertIn('"oracle","pirate"',source)
        self.assertTrue((ROOT/'look'/'personalities'/'oracle.md').exists())
        self.assertTrue((ROOT/'look'/'personalities'/'pirate.md').exists())

    def test_native_lo_persona_override_is_restored(self):
        lo=load(LO,'lo_engine_persona_test')
        class Core:
            def ollama_chat(self,**kwargs):
                self.seen=os.environ.get('LOOK_LO_PERSONALITY')
                kwargs['events'].emit('response',text='ok')
                return 0
        core=Core()
        old=os.environ.get('LOOK_LO_PERSONALITY')
        os.environ['LOOK_LO_PERSONALITY']='max'
        try:
            with mock.patch.object(lo,'_load_core',return_value=core), mock.patch.object(lo,'_load_web_key'):
                result=lo.chat_once('hi',persona='oracle')
            self.assertEqual(core.seen,'oracle')
            self.assertEqual(os.environ.get('LOOK_LO_PERSONALITY'),'max')
            self.assertEqual(result['persona'],'oracle')
        finally:
            if old is None: os.environ.pop('LOOK_LO_PERSONALITY',None)
            else: os.environ['LOOK_LO_PERSONALITY']=old

    def test_future_crash_ask_and_work_use_shared_lo(self):
        source=FC.read_text(encoding='utf-8')
        self.assertIn('if kind in {"ask","work"}:',source)
        self.assertIn('_shared_lo_chat(prompt, history, mode=kind)',source)
        self.assertIn('persona="oracle"',source)
        self.assertIn('ORACLE · FABRIC:AUTO',source)

if __name__=='__main__': unittest.main()
