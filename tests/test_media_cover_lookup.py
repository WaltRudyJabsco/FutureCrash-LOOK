import io
import json
import threading
from pathlib import Path
from look import media_cover_lookup as covers,media_art

GROUP='48140466-cff6-3222-bd55-63c27e43190d'


def match(group=GROUP,artist='Talking Heads',album='Remain in Light',score=100):
    return {'id':group,'title':album,'score':score,'artist-credit':[{'name':artist}]}


def test_album_match_requires_exact_artist_title_and_unique_group():
    assert covers.choose_group({'release-groups':[match()]},'Talking Heads','Remain in Light')==(GROUP,'matched')
    assert covers.choose_group({'release-groups':[match(artist='Another artist')]},'Talking Heads','Remain in Light')==(None,'missing')
    assert covers.choose_group({'release-groups':[match(score=75)]},'Talking Heads','Remain in Light')==(None,'missing')
    assert covers.choose_group({'release-groups':[match(),match(group='11111111-1111-1111-1111-111111111111')]},'Talking Heads','Remain in Light')==(None,'ambiguous')


def test_download_is_cached_and_leaves_album_files_and_tags_untouched(tmp_path,monkeypatch):
    monkeypatch.setattr(covers,'root',lambda:tmp_path/'cache')
    monkeypatch.setattr(covers,'rate_limit',lambda:None)
    calls=[];jpg=b'\xff\xd8\xfffake-cover'
    def read(url,limit):
        calls.append(url)
        return json.dumps({'release-groups':[match()]}).encode() if 'musicbrainz.org' in url else jpg
    monkeypatch.setattr(covers,'read_url',read)
    row={'artist':'Talking Heads','album':'Remain in Light'};token,artist,album=covers.album_key(row)
    result=covers.lookup(token,artist,album)
    assert result['state']=='ready' and covers.cached(token).read_bytes()==jpg
    assert '/release-group/'+GROUP+'/front-500' in calls[1]
    assert covers.lookup(token,artist,album)==result and len(calls)==2
    assert not (tmp_path/'cover.jpg').exists()


def test_provider_errors_and_bad_images_retry_without_poisoning_cache(tmp_path,monkeypatch):
    monkeypatch.setattr(covers,'root',lambda:tmp_path/'cache');monkeypatch.setattr(covers,'rate_limit',lambda:None)
    monkeypatch.setattr(covers,'read_url',lambda url,limit:json.dumps({'release-groups':[match()]}).encode() if 'musicbrainz.org' in url else b'<html>not a cover</html>')
    token,artist,album=covers.album_key({'artist':'Talking Heads','album':'Remain in Light'})
    result=covers.lookup(token,artist,album)
    assert result['state']=='error' and result['retry_at']>result['checked_at']
    assert covers.cached(token) is None


def test_existing_sidecar_art_never_schedules_online_lookup(tmp_path,monkeypatch):
    song=tmp_path/'song.mp3';song.write_bytes(b'audio');cover=tmp_path/'cover.jpg';cover.write_bytes(b'cover')
    monkeypatch.setattr(media_art,'_embedded',lambda path:None)
    monkeypatch.setattr(covers,'request',lambda *args:(_ for _ in ()).throw(AssertionError('should not look up existing art')))
    assert media_art.artwork_for(song)==cover


def test_request_returns_immediately_and_deduplicates_pending_album(tmp_path,monkeypatch):
    monkeypatch.setenv('LOOK_MEDIA_ARTWORK_LOOKUP','1')
    monkeypatch.setattr(covers,'root',lambda:tmp_path/'cache')
    song=tmp_path/'song.mp3';song.write_bytes(b'audio')
    entered=threading.Event();release=threading.Event();finished=threading.Event();calls=[]
    def lookup(*args):
        calls.append(args);entered.set();release.wait(2);finished.set()
    monkeypatch.setattr(covers,'lookup',lookup)
    row={'artist':'A Test Artist','album':'Test Album'}
    assert covers.request(song,row) is None
    assert entered.wait(1)
    assert covers.request(song,row) is None and len(calls)==1
    release.set();assert finished.wait(1);covers._JOBS.join()


def test_lookup_uses_bounded_download_and_user_agent(monkeypatch):
    seen=[]
    def open_url(request,timeout):
        seen.append((request,timeout));return io.BytesIO(b'x'*20)
    monkeypatch.setattr(covers.urllib.request,'urlopen',open_url)
    try:covers.read_url('https://coverartarchive.org/image',10)
    except ValueError:pass
    else:raise AssertionError('oversized image accepted')
    assert seen[0][0].get_header('User-agent')==covers.USER_AGENT


def test_lookup_toggle_persists_for_ui_and_daemon_and_defaults_off(tmp_path,monkeypatch):
    monkeypatch.setattr(covers.Path,'home',lambda:tmp_path)
    monkeypatch.delenv('LOOK_MEDIA_ARTWORK_LOOKUP',raising=False)
    assert not covers.enabled()
    covers.configure(True);assert covers.enabled()
    covers.configure(False);assert not covers.enabled()
    monkeypatch.setenv('LOOK_MEDIA_ARTWORK_LOOKUP','1');assert covers.enabled()
