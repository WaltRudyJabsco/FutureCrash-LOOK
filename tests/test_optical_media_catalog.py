from pathlib import Path
import pytest
from look import media_core as media


@pytest.mark.parametrize('path',[
 '/run/media/person/DISC/VIDEO_TS/VIDEO_TS.VOB',
 '/run/media/person/DISC/video_ts/VTS_06_3.vob',
 '/Volumes/DISC/BDMV/STREAM/00001.m2ts',
 '/Volumes/DISC/bdmv/stream/00001.MTS',
])
def test_disc_segments_are_excluded_from_old_receipts_and_new_scans(path):
    assert not media.is_media_path(Path(path))
    library=media.normalize_library({'roots':['/Volumes/DISC'],'entries':[{'path':path,'id':'old'}]})
    assert library['entries']==[]


@pytest.mark.parametrize('path',['/movies/Movie.mkv','/movies/Movie.vob','/movies/Movie.m2ts','/movies/VIDEO_TS/Finished.mkv'])
def test_standalone_videos_and_finished_imports_remain(path):
    assert media.is_media_path(Path(path))
    assert len(media.normalize_library({'entries':[{'path':path} ]})['entries'])==1


def test_parent_scan_keeps_finished_movie_but_omits_raw_disc(tmp_path):
    raw=tmp_path/'DVD/VIDEO_TS';raw.mkdir(parents=True)
    (raw/'VTS_01_1.VOB').write_bytes(b'disc')
    movie=tmp_path/'movies/PCU.mkv';movie.parent.mkdir();movie.write_bytes(b'movie')
    result=media.scan_root(tmp_path)
    assert [row['path'] for row in result['entries']]==[str(movie)]
