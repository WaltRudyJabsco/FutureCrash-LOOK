import json
import sys
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'look'))
import file_catalog, media_core, media_watch, managed_folders, media_open
from look import look_renderer as renderer


def test_download_and_picture_folders_are_repaired_without_manual_roots(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',classmethod(lambda cls:tmp_path))
    monkeypatch.setattr(media_watch,'LIBRARY',tmp_path/'library.json')
    monkeypatch.setattr(media_watch,'STATUS',tmp_path/'status.json')
    download=tmp_path/'Downloads/LOOK/job'; download.mkdir(parents=True)
    video=download/'Lesson.mp4'; video.write_bytes(b'video')
    video.with_suffix('.info.json').write_text(json.dumps({'title':'Chord lesson','description':'Ukulele voicings','tags':['fingerstyle'],'channel':'Teacher','webpage_url':'https://youtu.be/test'}))
    pictures=tmp_path/'Pictures/LOOK'; pictures.mkdir(parents=True)
    image=pictures/'chord-chart.jpg'; image.write_bytes(b'image')
    stage=tmp_path/'Downloads/LOOK/.look-ytd-stage-test'; stage.mkdir(); (stage/'unfinished.mp4').write_bytes(b'part')
    media_watch.refresh_existing({})
    rows=media_watch.load()['entries']
    assert len(rows)==1 and rows[0]['title']=='Chord lesson' and rows[0]['artist']=='Teacher'
    db=tmp_path/'.local/share/look/file_catalog.sqlite3'
    assert any(row['path']==str(video) for row in file_catalog.combined_search(db,'fingerstyle'))
    assert file_catalog.search(db,'chord-chart')[0]['path']==str(image)
    assert not file_catalog.search(db,'unfinished')
    assert str(tmp_path/'Downloads/LOOK') in media_watch.load()['roots']


def test_custom_created_roots_are_discoverable(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',classmethod(lambda cls:tmp_path))
    custom=tmp_path/'Generated images'; custom.mkdir()
    managed_folders.register(custom); managed_folders.register('/')
    assert custom in managed_folders.roots() and Path('/') not in managed_folders.roots()
    assert managed_folders.registry().stat().st_mode&0o777==0o600


def test_manual_move_with_sidecar_restores_metadata_in_both_catalogs(tmp_path):
    folder=tmp_path/'Permanent'; folder.mkdir()
    video=folder/'boring-filename.mp4'; video.write_bytes(b'video')
    video.with_suffix('.info.json').write_text(json.dumps({'title':'Reef diving tutorial','description':'Buoyancy and navigation','channel':'Dive channel','tags':['diving']}))
    library=media_core.scan_root(folder)
    assert library['entries'][0]['title']=='Reef diving tutorial'
    db=tmp_path/'catalog.db'; file_catalog.scan(db,folder)
    result=next(row for row in file_catalog.combined_search(db,'buoyancy') if row['path']==str(video))
    assert result['path']==str(video) and result['provenance']=='source'


def test_bad_sidecar_never_breaks_media_scan(tmp_path):
    video=tmp_path/'video.mp4'; video.write_bytes(b'video')
    video.with_suffix('.info.json').write_text('not json')
    assert media_core.scan_root(tmp_path)['entries'][0]['title']=='video'


def test_mac_browser_honors_vlc_while_system_choice_keeps_normal_open(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',classmethod(lambda cls:tmp_path))
    monkeypatch.setattr(media_open.sys,'platform','darwin')
    prefs=tmp_path/'.local/share/look/apps.json'; prefs.parent.mkdir(parents=True); prefs.write_text(json.dumps({'video':'VLC'}))
    launch=Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr(renderer.subprocess,'run',launch)
    video=tmp_path/'My movie.mp4'
    assert renderer.open_default(video)==(True,'')
    assert launch.call_args.args[0]==['open','-a','VLC',str(video)]
    prefs.write_text(json.dumps({'video':'system'})); renderer.open_default(video)
    assert launch.call_args.args[0]==['open',str(video)]


def test_mac_mpv_preference_works_without_an_app_bundle(tmp_path,monkeypatch):
    monkeypatch.setattr(media_open.sys,'platform','darwin')
    monkeypatch.setattr(media_open,'mpv_binary',lambda:'/opt/homebrew/bin/mpv')
    assert media_open.command(tmp_path/'video.mp4','mpv')[0]=='/opt/homebrew/bin/mpv'
