import subprocess
import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('words',[['fabric','--help'],['media','--help'],['models','--help'],
                                 ['settings','--help'],['help','fabric'],['notes','--help'],['o','--help']])
def test_help_exits_successfully_without_opening_apps_or_connecting(words):
    result=subprocess.run([sys.executable,str(ROOT/'look/lk'),*words],capture_output=True,text=True,timeout=5)
    assert result.returncode==0,result.stderr
    assert 'help' in result.stdout.casefold()
    assert 'usage' in result.stdout.casefold() or 'COMMAND FORMS' in result.stdout


def test_notebook_help_explains_semantics_and_flags():
    result=subprocess.run([sys.executable,str(ROOT/'look/lk'),'notes','--help'],capture_output=True,text=True,timeout=5)
    for phrase in ('File (P)','Done (C)','Remind (R)','--due','--remind','--project','offline'):
        assert phrase in result.stdout
