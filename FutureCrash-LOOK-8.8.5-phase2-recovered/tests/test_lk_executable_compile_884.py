from pathlib import Path
import py_compile

ROOT = Path(__file__).resolve().parents[1]

def test_lk_executable_compiles():
    py_compile.compile(str(ROOT / "look" / "lk"), doraise=True)
