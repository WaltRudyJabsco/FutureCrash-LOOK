"""Local synthetic-audio check: no YouTube request and no audible playback."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'look'))
import ytr
import subprocess

with tempfile.TemporaryDirectory(prefix='ytr-check-') as folder:
    root=Path(folder);audio=root/'tone.m4a'
    subprocess.run([shutil.which('ffmpeg'),'-v','error','-f','lavfi','-i','sine=frequency=220:duration=8','-c:a','aac',str(audio)],check=True)
    binary=root/'mpv-null'
    binary.write_text('#!/bin/sh\nexec '+shutil.which('mpv')+' --ao=null "$@"\n');binary.chmod(0o700)
    ytr.book_reader.binary=lambda _:str(binary)
    player=ytr.Player()
    try:
        player.start(audio,2)
        deadline=time.monotonic()+5
        while time.monotonic()<deadline and player.get('time-pos') is None:time.sleep(.05)
        assert player.get('path')==str(audio)
        assert 1.8<float(player.get('time-pos'))<5,player.get('time-pos')
        player.command('set_property','pause',True)
        assert player.get('pause') is True
        player.command('seek',4,'absolute')
        time.sleep(.1)
        assert abs(player.get('time-pos')-4)<.3
        print('mpv audio-only playback, resume, pause and seek verified (null audio output)')
    finally:player.close()
