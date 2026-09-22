import json
import sys
import tempfile
import time
import unittest
from unittest import mock
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'core'))

import decision
from fabric_packet import FabricStore


class DecisionPolicyTests(unittest.TestCase):
    def test_power_can_continue_only_low_risk_reversible_uncertainty(self):
        plan=decision.plan(profile='power',confidence=.65,consequence='low',reversible=True)
        self.assertEqual(plan.action,'ask')
        self.assertEqual(plan.timeout_action,'continue')
        self.assertFalse(plan.requires_confirmation)

    def test_workspace_defers_ambiguous_work(self):
        plan=decision.plan(profile='workspace',confidence=.65,consequence='low',reversible=True)
        self.assertEqual(plan.action,'ask')
        self.assertEqual(plan.timeout_action,'defer')

    def test_irreversible_never_auto_continues(self):
        for profile in ('conservative','workspace','power','unsafe'):
            plan=decision.plan(profile=profile,confidence=.99,consequence='low',reversible=False)
            self.assertEqual(plan.timeout_action,'cancel')
            self.assertTrue(plan.requires_confirmation)

    def test_request_default_fallback_follows_profile(self):
        workspace=decision.new_request(question='Use it?',choices=[{'value':'yes'},{'value':'no'}],profile='workspace',preferred='yes')
        power=decision.new_request(question='Use it?',choices=[{'value':'yes'},{'value':'no'}],profile='power',preferred='yes',confidence=.5)
        self.assertEqual(workspace['fallback'],'defer')
        self.assertEqual(power['fallback'],'yes')


class DecisionStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=FabricStore(Path(self.tmp.name)/'fabric.sqlite3')

    def tearDown(self):
        self.tmp.cleanup()

    def test_answer_is_single_resolution(self):
        req=decision.new_request(question='A or B?',choices=[{'value':'a'},{'value':'b'}],profile='workspace')
        self.store.add_decision(req,node='test')
        answered=self.store.resolve_decision(req['id'],'b',source='test',node='test')
        self.assertEqual(answered['selected'],'b')
        self.assertEqual(answered['status'],'answered')
        late=self.store.resolve_decision(req['id'],'a',source='late',node='test')
        self.assertEqual(late['selected'],'b')

    def test_timeout_records_fallback_without_blocking(self):
        req=decision.new_request(question='A or B?',choices=[{'value':'a'},{'value':'b'}],profile='power',preferred='a',confidence=.5,deadline_seconds=5)
        req['expires']=time.time()-1
        self.store.add_decision(req,node='test')
        expired=self.store.expire_decisions(node='test')
        self.assertEqual(len(expired),1)
        self.assertEqual(expired[0]['status'],'timed_out')
        self.assertEqual(expired[0]['selected'],'a')


class OpenJevShadowTests(unittest.TestCase):
    def test_choice_normalizes_typed_answer(self):
        body=b'{"model":"openjev","answers":{"decision":{"choice":"media.play","probabilities":{"media.play":0.91,"web.search":0.09},"confidence":0.91}}}'

        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self): return body

        with mock.patch.object(decision.urllib.request,'urlopen',return_value=Response()):
            result=decision.OpenJevShadow('http://example.invalid').choice(
                state='play talking heads',
                question='Which capability?',
                candidates=['media.play','web.search'],
            )
        self.assertTrue(result['ok'])
        self.assertEqual(result['choice'],'media.play')
        self.assertAlmostEqual(result['confidence'],0.91)
        self.assertAlmostEqual(result['probabilities']['web.search'],0.09)

    def test_choice_omits_model_for_zefancai_openjev_server(self):
        body=b'{"answers":{"decision":{"choice":"a","probabilities":{"a":0.8,"b":0.2},"confidence":0.6}}}'

        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self): return body

        captured={}
        def fake_urlopen(req, timeout=None):
            captured.update(json.loads(req.data.decode('utf-8')))
            return Response()

        with mock.patch.object(decision.urllib.request,'urlopen',side_effect=fake_urlopen):
            result=decision.OpenJevShadow('http://example.invalid').choice(
                state='x', question='pick', candidates=['a','b'])
        self.assertTrue(result['ok'])
        self.assertNotIn('model', captured)
        self.assertEqual(captured['questions']['decision']['criteria'], {'a': None, 'b': None})

    def test_http_error_preserves_provider_detail(self):
        import io
        err=decision.urllib.error.HTTPError(
            'http://example.invalid/v1/systemone', 422, 'Unprocessable Content', {},
            io.BytesIO(b'{"detail":"bad model"}'))
        with mock.patch.object(decision.urllib.request,'urlopen',side_effect=err):
            result=decision.OpenJevShadow('http://example.invalid').try_choice(
                state='x', question='pick', candidates=['a','b'])
        self.assertFalse(result['ok'])
        self.assertEqual(result['detail']['detail'], 'bad model')

    def test_choice_derives_confidence_from_probability_when_missing(self):
        body=b'{"answers":{"decision":{"choice":"a","probabilities":{"a":0.73,"b":0.27}}}}'

        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self): return body

        with mock.patch.object(decision.urllib.request,'urlopen',return_value=Response()):
            result=decision.OpenJevShadow('http://example.invalid').choice(
                state='x', question='pick', candidates=['a','b'])
        self.assertAlmostEqual(result['confidence'],0.73)


class DecisionSurfaceTests(unittest.TestCase):
    def test_signal_has_fabric_decision_surface(self):
        server=(ROOT/'signal-window'/'server.py').read_text(encoding='utf-8')
        app=(ROOT/'signal-window'/'app.js').read_text(encoding='utf-8')
        self.assertIn('/api/fabric/decisions',server)
        self.assertIn('/v1/decisions/fabric',server)
        self.assertIn('pollDecisions',app)
        self.assertIn('answerDecision',app)

    def test_installer_ships_decision_plane(self):
        install=(ROOT/'install.sh').read_text(encoding='utf-8')
        self.assertIn('core/decision.py',install)
        self.assertIn('import conductor, fabric_client, memory_store, decision',install)


if __name__=='__main__':
    unittest.main()
