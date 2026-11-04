import os,pty,select,subprocess,sys,time
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]

def test_fourth_digit_submits_without_enter_and_restores_terminal():
    master,slave=pty.openpty()
    code="import curtain_client; a=curtain_client.read_pin('First: '); b=curtain_client.read_pin('Again: '); print('MATCH' if a==b=='1234' else 'FAIL')"
    proc=subprocess.Popen([sys.executable,'-c',code],stdin=slave,stdout=slave,stderr=slave,env=dict(os.environ,PYTHONPATH=str(ROOT/'look')))
    def until(marker):
        output=b'';deadline=time.monotonic()+5
        while marker not in output and time.monotonic()<deadline:
            if select.select([master],[],[],.1)[0]:output+=os.read(master,4096)
        assert marker in output,output
        return output
    try:
        until(b'First: ');os.write(master,b'12x9\x7f34')
        assert b'1234' not in until(b'Again: ')
        os.write(master,b'1234');assert b'1234' not in until(b'MATCH')
        assert proc.wait(timeout=3)==0
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
        os.close(master);os.close(slave)
