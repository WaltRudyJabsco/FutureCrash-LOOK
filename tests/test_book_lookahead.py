from pathlib import Path
import subprocess


def test_browser_narration_lookahead_lifecycle():
    root=Path(__file__).resolve().parents[1]
    subprocess.run(['node',str(root/'tests/browser/book_lookahead.cjs'),str(root/'signal-window/browser-views.js')],check=True)
