import importlib.util
import unittest
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
