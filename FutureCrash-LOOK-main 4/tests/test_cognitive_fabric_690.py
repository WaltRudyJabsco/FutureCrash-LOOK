import ast
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LOOK=ROOT/'look'/'lk'
COG=ROOT/'core'/'cognition.py'


def helper_namespace():
    tree=ast.parse(LOOK.read_text())
    wanted={
        '_extract_audio_pseudocall','_lo_requires_speech','_answer_claims_memory_write',
        '_normalize_weather_location','_lo_learned_home_location','_lo_store_home_location',
        '_lo_store_default_location','_lo_location_memory_directive','_merge_machine_atoms',
    }
    body=[]
    for node in tree.body:
        if isinstance(node,ast.Assign):
            names=[x.id for x in node.targets if isinstance(x,ast.Name)]
            if '_US_STATE_ABBREVIATIONS' in names: body.append(node)
        elif isinstance(node,ast.FunctionDef) and node.name in wanted:
            body.append(node)
    ns={'re':re,'time':__import__('time')}
    exec(compile(ast.Module(body=body,type_ignores=[]),str(LOOK),'exec'),ns)
    return ns

class CognitiveFabric690Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.h=helper_namespace()

    def test_speech_pseudocall_is_recoverable_but_not_a_receipt(self):
        row=self.h['_extract_audio_pseudocall']('audiospeak(text="Signal clear. Ready.", voiceprofile="default")')
        self.assertEqual(row['text'],'Signal clear. Ready.')
        self.assertEqual(row['voice_profile'],'default')
        self.assertTrue(self.h['_lo_requires_speech']('say something again'))
        text=LOOK.read_text()
        self.assertIn('no audio_speak receipt exists',text)
        self.assertIn('I did not execute the speech tool',text)

    def test_anaphoric_location_memory_requires_verified_home(self):
        mem={'atoms':[{'k':'preference','s':'home','r':'weather_location','v':'Portland, Oregon','c':100,'u':1,'t':1}]}
        row=self.h['_lo_location_memory_directive']('make a point to remember that i live there and default to there for ambiguous location related subjects',mem)
        self.assertEqual(row,{'home':'Portland, Oregon','default':True})
        self.assertIsNone(self.h['_lo_location_memory_directive']('remember that i live there',{'atoms':[]}))

    def test_memory_success_language_needs_receipt(self):
        self.assertTrue(self.h['_answer_claims_memory_write']('I have logged this directive.'))
        self.assertTrue(self.h['_answer_claims_memory_write']("I'll remember that."))
        self.assertFalse(self.h['_answer_claims_memory_write']('That sounds useful.'))

    def test_named_model_set_cli_is_real(self):
        text=LOOK.read_text()
        self.assertIn('def ollama_set(args):',text)
        self.assertIn('return ollama_set(rest[1:])',text)
        self.assertIn('"models","test","curate","set","warm"',text)
        with tempfile.TemporaryDirectory() as td:
            env=dict(os.environ); env['HOME']=td
            p=subprocess.run(['python3',str(LOOK),'ollama','set','list'],env=env,text=True,capture_output=True)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn('LOOK MODEL SETS',p.stdout)

    def test_cognition_has_evidence_authority_and_goal_lifecycle(self):
        text=COG.read_text()
        self.assertIn('class EvidenceReceipt',text)
        self.assertIn('SOURCE_AUTHORITY',text)
        self.assertIn('waiting_human',text)
        self.assertIn('cancelled',text)


    def test_model_benchmark_contains_real_fabric_fit_probes(self):
        text=LOOK.read_text()
        self.assertIn('def _benchmark_fabric_fit(',text)
        self.assertIn('speech_primitive',text)
        self.assertIn('fabric_fit_total',text)
        node=(ROOT/'core'/'node.py').read_text()
        self.assertIn('fabric_ratio',node)

    def test_persistent_goals_name_wake_and_close_conditions(self):
        text=LOOK.read_text()
        self.assertIn('"wake_on":"operator_input"',text)
        self.assertIn('"close_when":"completed_failed_or_cancelled"',text)

if __name__=='__main__': unittest.main()
