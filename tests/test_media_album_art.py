from pathlib import Path
from look import media_art
from test_media_art_840 import _fixture


def test_artless_track_reuses_embedded_album_cover(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    album = tmp_path / 'album'
    album.mkdir()
    sibling = _fixture(album)
    track = album / 'Lola.mp3'
    track.write_bytes(b'no attached picture')
    art = media_art.artwork_for(track)
    assert art and art.is_file()
    assert art == media_art.artwork_for(sibling)


def test_current_cover_and_sidecar_take_priority(monkeypatch, tmp_path):
    track = tmp_path / 'song.mp3'
    track.touch()
    own = tmp_path / 'own.jpg'
    sidecar = tmp_path / 'cover.jpg'
    own.touch(); sidecar.touch()
    monkeypatch.setattr(media_art, '_album_art', lambda path: (_ for _ in ()).throw(AssertionError('unexpected borrow')))
    monkeypatch.setattr(media_art, '_embedded', lambda path: own)
    assert media_art.artwork_for(track) == own
    monkeypatch.setattr(media_art, '_embedded', lambda path: None)
    assert media_art.artwork_for(track) == sidecar


def test_folder_isolation_and_repeat_miss_cache(monkeypatch, tmp_path):
    album = tmp_path / 'album'
    other = tmp_path / 'other'
    album.mkdir(); other.mkdir()
    track = album / 'song.mp3'; track.touch()
    sibling = album / 'second.mp3'; sibling.touch()
    (other / 'cover.jpg').touch()
    calls = []
    monkeypatch.setattr(media_art, '_embedded', lambda path, **kw: calls.append(path))
    assert media_art._album_art(track) is None
    assert media_art._album_art(track) is None
    assert calls == [sibling]


def test_cached_sibling_survives_new_process_cache(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    track = tmp_path / 'song.mp3'; track.touch()
    sibling = tmp_path / 'second.mp3'; sibling.touch()
    cached = media_art._embedded_cache(sibling)
    cached.parent.mkdir(parents=True); cached.write_bytes(b'cover')
    monkeypatch.setattr(media_art, '_embedded', lambda *a, **kw: (_ for _ in ()).throw(AssertionError('unexpected decode')))
    assert media_art._album_art(track) == cached
    sibling.unlink()
    assert media_art._album_art(track) is None


def test_probe_count_and_timeouts_are_bounded(monkeypatch, tmp_path):
    track = tmp_path / 'song.mp3'; track.touch()
    for i in range(100): (tmp_path / f'{i}.mp3').touch()
    calls = []
    monkeypatch.setattr(media_art, '_embedded', lambda path, **kw: calls.append((path, kw['timeout'])))
    assert media_art._album_art(track) is None
    assert len(calls) == media_art.ALBUM_PROBE_LIMIT
    assert all(0 < timeout <= media_art.ALBUM_PROBE_SECONDS for _, timeout in calls)


def test_decoder_misses_retry_after_file_changes(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    track = tmp_path / 'song.mp3'; track.write_bytes(b'bad')
    calls = []
    monkeypatch.setattr(media_art.shutil, 'which', lambda name: 'ffmpeg')
    class Failure:
        returncode = 1
    monkeypatch.setattr(media_art.subprocess, 'run', lambda *a, **kw: calls.append(a) or Failure())
    assert media_art._embedded(track) is None
    assert media_art._embedded(track) is None
    assert len(calls) == 1
    import os
    stamp = track.stat().st_mtime_ns
    os.utime(track, ns=(stamp + 1, stamp + 1))
    assert media_art._embedded(track) is None
    assert len(calls) == 2
