import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FC_PATH = ROOT / 'future-crash' / 'future_crash.py'


def load_fc():
    name = 'future_crash_test_module'
    spec = importlib.util.spec_from_file_location(name, FC_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FutureCrashChannelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fc = load_fc()
        cls.source = FC_PATH.read_text(encoding='utf-8')

    def test_signal_compile_uses_visible_answer_as_visual_context(self):
        prompt = self.fc._signal_compile_prompt('draw the weather', 'Portland is 67 F and cloudy.')
        self.assertIn('OPERATOR REQUEST:', prompt)
        self.assertIn('VISIBLE ORACLE ANSWER', prompt)
        self.assertIn('Portland is 67 F and cloudy.', prompt)

    def test_model_output_keeps_visible_text_and_signal_separate(self):
        message = {'content': 'Hello there.\n\n[[SIGNAL]]\nCLEAR 0 0 0\n[[/SIGNAL]]'}
        out = self.fc._model_output(message, preserve_signal=True)
        self.assertIn('Hello there.', out)
        self.assertIn('[[SIGNAL]]', out)

    def test_ordinary_oracle_prompt_does_not_embed_signal_language(self):
        # Signal grammar belongs only to signalcompile/signalrepair. Keeping it out
        # of normal ask/work prevents tiny models from answering with render receipts.
        work = self.source[self.source.index('elif kind == "work":'):self.source.index('messages.append({"role": "system", "content": system})')]
        self.assertNotIn('SIGNAL_LANGUAGE +', work)
        self.assertIn('TOOL_LANGUAGE', work)

    def test_submit_never_replaces_conversation_with_signal_compile(self):
        submit = self.source[self.source.index('    def submit(self):'):self.source.index('    def box(', self.source.index('    def submit(self):'))]
        self.assertNotIn('_ask_oracle("signalcompile:ask"', submit)
        self.assertNotIn('_ask_oracle("signalcompile:work"', submit)
        self.assertIn('_ask_oracle("ask", text, history)', submit)
        self.assertIn('_ask_oracle("work", text, history)', submit)

    def test_signal_receipts_are_not_added_to_normal_chat_history(self):
        submit = self.source[self.source.index('    def submit(self):'):self.source.index('    def box(', self.source.index('    def submit(self):'))]
        self.assertNotIn('signal.context_packet()', submit)

    def test_signal_sidecar_does_not_write_signal_updated_into_chat(self):
        poll = self.source[self.source.index('    def poll(self):'):self.source.index('    def update(self):')]
        self.assertNotIn('self.answer = clean.strip() if clean.strip() else "SIGNAL UPDATED"', poll)
        self.assertNotIn('self.work_log.append(("oracle", final))\n                        self.work_history.append({"role":"assistant","content":final})\n                        if self.work_pending_user', poll[poll.index('elif kind.startswith("signalcompile:")'):poll.index('elif kind.startswith("signalrepair:")')])
        self.assertIn('self.work_notice = "SIGNAL UPDATED"', poll)


if __name__ == '__main__':
    unittest.main()
