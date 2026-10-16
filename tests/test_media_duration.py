from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace
import shutil
import wave
import pytest
from look import media_duration as duration


@pytest.mark.parametrize('value',[None,'bad',float('nan'),float('inf'),-1,0])
def test_invalid_durations_stay_unknown(value):assert duration.seconds(value) is None


def test_duration_uses_catalog_and_copy_metadata_before_probing(tmp_path):
    preview=duration.DurationPreview(lambda row:pytest.fail('no probe'),tmp_path/'cache.json')
    assert preview.value({'duration_seconds':'245'})==245
    assert preview.value({'sources':[{'duration':65}]})==65
    assert preview.poll([{'duration':245}]) is False
    assert preview.pending is None
    preview.close()


def test_visible_probes_are_bounded_cached_and_invalidated(tmp_path,monkeypatch):
    preview=duration.DurationPreview(lambda row:'/unused',tmp_path/'cache.json')
    preview.ffprobe='ffprobe';futures=[]
    def submit(row):
        future=Future();futures.append((row,future));return future
    monkeypatch.setattr(preview,'submit',submit)
    first={'id':'first','mtime':1};second={'id':'second'}
    assert preview.poll([first,second]) is False
    preview.poll([first,second]);assert len(futures)==1
    futures[0][1].set_result(245)
    assert preview.poll([first,second]) is True and preview.value(first)==245
    assert len(futures)==2 and futures[1][0]==second
    reopened=duration.DurationPreview(lambda row:None,preview.path)
    assert reopened.value(first)==245 and reopened.value(dict(first,mtime=2)) is None
    assert preview.path.stat().st_mode&0o777==0o600
    preview.close();reopened.close()


def test_failed_probe_does_not_loop_or_block_close(tmp_path,monkeypatch):
    preview=duration.DurationPreview(lambda row:None,tmp_path/'cache.json');preview.ffprobe='ffprobe'
    future=Future();monkeypatch.setattr(preview,'submit',lambda row:future)
    preview.poll([{'id':'bad'}]);future.set_exception(ValueError('offline'))
    assert preview.poll([{'id':'bad'}]) is False and preview.pending is None
    preview.close();assert preview.poll([{'id':'new'}]) is False and preview.pending is None


def test_probe_reads_generated_wav_duration_without_playback(tmp_path):
    if not shutil.which('ffprobe'):pytest.skip('ffprobe not installed')
    path=tmp_path/'tone.wav'
    with wave.open(str(path),'wb') as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(8000);audio.writeframes(b'\0\0'*8000)
    preview=duration.DurationPreview(lambda row:path,tmp_path/'cache.json')
    assert preview.probe({'path':str(path)})==pytest.approx(1)
    preview.close()
