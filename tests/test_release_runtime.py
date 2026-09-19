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
