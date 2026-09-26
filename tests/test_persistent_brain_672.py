import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LOOK=ROOT/'look'/'lk'

class PersistentBrain672Tests(unittest.TestCase):
    def test_brain_state_survives_processes(self):
        with tempfile.TemporaryDirectory() as td:
            env=dict(os.environ); env['HOME']=td
            clear=subprocess.run(['python3',str(LOOK),'brain','clear'],env=env,text=True,capture_output=True)
            self.assertEqual(clear.returncode,0,clear.stderr)
            show=subprocess.run(['python3',str(LOOK),'brain'],env=env,text=True,capture_output=True)
            self.assertEqual(show.returncode,0,show.stderr)
            self.assertIn('persistent working state',show.stdout)
            self.assertIn('models may sleep; goals stay alive',show.stdout)
            self.assertTrue((Path(td)/'.local/share/look/brain_state.json').exists())

    def test_weather_home_slot_is_persistent_and_resumable(self):
        text=LOOK.read_text()
        self.assertIn('slot="home.location"',text)
        self.assertIn('slot="weather.location"',text)
        self.assertIn('_brain_clear_pending("weather"',text)
        self.assertIn('weather_location=_lo_learned_home_location(_load_memory())',text)

    def test_context_budget_keeps_more_history_but_retrieves_bounded_context(self):
        text=LOOK.read_text()
        self.assertIn('LO_RECENT_EXCHANGES=48',text)
        self.assertIn('LO_RECENT_MAX_CHARS=64000',text)
        self.assertIn('LO_RECENT_CONTEXT_CHARS=14000',text)
        self.assertIn('MEMORY_RETRIEVED_ATOMS=18',text)

if __name__=='__main__': unittest.main()
