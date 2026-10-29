"""Only a real Escape key may become an escape action."""
import os
import pytest
from test_media_request_regressions import lk


@pytest.mark.parametrize('packet,expected',[
    (b'\x1b','esc'),(b'\x1b[A','up'),(b'\x1b[1;2A','shiftup'),
    (b'\x1b[99;2u','C'),(b'\x1b[99;2:3u',''),(b'\x1b[97u','a'),
    (b'\x1b[105;1:2u','i'),(b'\x1b[114u','r'),(b'\x1b[111u','o'),
    (b'\x1b[97;2;65u','A'),(b'\x1b[0;;229u','å'),
    (b'\x1b[13u','enter'),(b'\x1b[27u','esc'),
    (b'\x1b[?1;2c',''),(b'\x1b[8;20;100t',''),
    (b'\x1b_Gi=42;OK\x1b\\',''),(b'\x1b]10;rgb:aaaa/bbbb/cccc\x07',''),
])
def test_terminal_packets_are_not_escape_presses(lk,packet,expected):
    read,write=os.pipe()
    try:
        os.write(write,packet+b'z') if packet!=b'\x1b' else os.write(write,packet)
        assert lk._read_tty_key(read,.1)==expected
        if packet!=b'\x1b':assert lk._read_tty_key(read,.1)=='z'
    finally:os.close(read);os.close(write)
