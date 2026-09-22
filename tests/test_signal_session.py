import importlib.util
import unittest
import unittest.mock
from pathlib import Path

SERVER=Path(__file__).resolve().parents[1]/'signal-window'/'server.py'
spec=importlib.util.spec_from_file_location('signal_server_test',SERVER)
server=importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)

class SignalSessionTests(unittest.TestCase):
    def setUp(self):
        with server._SESSION_LOCK:
            server._SESSIONS.clear()

    def test_session_is_bounded_and_clearable(self):
        sid='browser-1'
        for i in range(10):
            server._session_append(sid,f'u{i}',f'a{i}')
        history=server._session_history(sid)
        self.assertLessEqual(len(history),12)
        self.assertEqual(history[-1]['content'],'a9')
        server._session_clear(sid)
        self.assertEqual(server._session_history(sid),[])

if __name__=='__main__': unittest.main()

class SignalVisualPolicyTests(unittest.TestCase):
    def test_signal_client_has_fabric_light_display(self):
        root=Path(__file__).resolve().parents[1]
        html=(root/'signal-window/index.html').read_text()
        js=(root/'signal-window/app.js').read_text()
        self.assertIn('id="fabricLight"', html)
        self.assertIn('/api/fabric/lights', js)

    def test_signal_composes_after_answer(self):
        root=Path(__file__).resolve().parents[1]
        js=(root/'signal-window/app.js').read_text()
        self.assertIn("answer:d.text||''", js)
        self.assertNotIn("const visualPromise=text?fetch('/api/visual'", js)

class SignalSceneGuardTests(unittest.TestCase):
    def test_rejects_solid_green_clear(self):
        scene={"clear":"#00ff00","ops":[]}
        self.assertEqual(server._scene_rejection_reason(scene),'solid_clear')

    def test_rejects_full_canvas_filled_rect(self):
        scene={"clear":"#020503","ops":[["rect",0,0,256,256,"#00aa33",True,1]]}
        self.assertEqual(server._scene_rejection_reason(scene),'solid_rect')

    def test_accepts_structured_scene(self):
        scene={"clear":"#020503","ops":[["rect",20,20,216,180,"#284c35",False,2],["text",30,50,"#8fd6a2","OK",12]]}
        self.assertEqual(server._scene_rejection_reason(scene),'')

    def test_weather_fallback_is_structured_and_truthful(self):
        scene,kind=server._deterministic_signal_scene('weather in portland','Current temperature is 63°F with a high of 68°F and low of 53°F.')
        self.assertEqual(kind,'weather_card')
        self.assertEqual(server._scene_rejection_reason(scene),'')
        texts=[op[4] for op in scene['ops'] if op and op[0]=='text']
        self.assertTrue(any('63 F' in t for t in texts))
        self.assertTrue(any('H 68' in t and 'L 53' in t for t in texts))

class SignalMediaSurfaceTests(unittest.TestCase):
    def test_signal_has_shared_media_card(self):
        root=Path(__file__).resolve().parents[1]
        html=(root/'signal-window/index.html').read_text()
        js=(root/'signal-window/app.js').read_text()
        server_text=(root/'signal-window/server.py').read_text()
        self.assertIn('id="mediaPanel"',html)
        self.assertIn("/api/media",js)
        self.assertIn("/api/media/control",js)
        self.assertIn("pollMedia",js)
        self.assertIn("renderMedia",js)
        self.assertIn('self.path=="/api/media"',server_text)
        self.assertIn('self.path=="/api/media/control"',server_text)

    def test_media_state_normalizes_available_flag(self):
        fake=type('CP',(),{'returncode':0,'stdout':'{"active":true,"state":"playing","queue":[],"entry":{}}','stderr':''})()
        with unittest.mock.patch.object(server,'_lk_path',return_value='/tmp/lk'), \
             unittest.mock.patch.object(server.subprocess,'run',return_value=fake):
            state=server._media_state()
        self.assertTrue(state['available'])
        self.assertTrue(state['active'])
