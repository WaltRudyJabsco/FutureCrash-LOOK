import os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class ReleaseRuntimeTests(unittest.TestCase):
    def test_installer_ships_conductor(self):
        text=(ROOT/"install.sh").read_text()
        self.assertIn('core/conductor.py', text)
        self.assertIn('import conductor, fabric_client', text)

    def test_flat_runtime_import_contract(self):
        text=(ROOT/"core/fabric_client.py").read_text()
        self.assertIn('from conductor import classify', text)
        self.assertNotIn('from .conductor import', text)


    def test_release_contains_beacon_and_fast_edge(self):
        node_text=(ROOT/"core/node.py").read_text()
        look_text=(ROOT/"look/lk").read_text()
        self.assertIn('"/v1/beacon"', node_text)
        self.assertIn('FABRIC BEACON', node_text)
        self.assertIn('FAST EDGE:', look_text)
        self.assertIn('just a little longer', look_text)

    def test_installed_layout_imports_together(self):
        with tempfile.TemporaryDirectory() as td:
            dest=Path(td)
            shutil.copy2(ROOT/"core/conductor.py", dest/"conductor.py")
            shutil.copy2(ROOT/"core/fabric_client.py", dest/"fabric_client.py")
            env=dict(os.environ)
            env["PYTHONPATH"]=str(dest)
            subprocess.run([sys.executable,"-c",
                "import conductor, fabric_client; assert conductor.classify('ping').tier == 'reflex'; assert callable(fabric_client.stream_infer)"],
                env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == '__main__': unittest.main()

class Test511Reliability(unittest.TestCase):
    def test_dashboard_hotkeys_use_daemon_control_plane(self):
        text=(ROOT/'core'/'node.py').read_text()
        dash=text[text.index('def _dashboard('):text.index('def _settings_view(') if 'def _settings_view(' in text else len(text)]
        self.assertIn('_daemon_url(host, port, "/v1/beacon")', dash)
        self.assertIn('_daemon_url(host, port, "/v1/lights")', dash)

    def test_weather_preflight_has_bounded_read_retry(self):
        text=(ROOT/'look'/'lk').read_text()
        self.assertIn('for weather_attempt in range(2):', text)
        self.assertIn('reason="transient_read_failure"', text)
        self.assertIn('read-only/idempotent edge', text)

class Test520PersonaMemory(unittest.TestCase):
    def test_installer_ships_fabric_memory(self):
        install=(ROOT/'install.sh').read_text(encoding='utf-8')
        self.assertIn('core/memory_store.py', install)
        self.assertIn('import conductor, fabric_client, memory_store', install)

    def test_node_exposes_memory_api(self):
        source=(ROOT/'core'/'node.py').read_text(encoding='utf-8')
        self.assertIn('if path == "/v1/memory":', source)
        self.assertIn('_memory_sync()', source)
