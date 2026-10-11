import importlib.machinery
import importlib.util
import io
import json
from pathlib import Path
import struct
from unittest.mock import Mock
import pytest
from look import archive_tv as a, media_protection as protection

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def lk(monkeypatch,tmp_path):
    monkeypatch.setenv('HOME',str(tmp_path))
    loader=importlib.machinery.SourceFileLoader('lk_archive',str(ROOT/'look/lk'))
    spec=importlib.util.spec_from_loader(loader.name,loader);module=importlib.util.module_from_spec(spec);loader.exec_module(module)
    return module


def metadata():
    files=[{'name':f'SEASON {s}/S{s:02}E{e:02} - Episode {e}.mp4','format':'MPEG4','size':'20'} for s,count in ((2,6),(1,12)) for e in range(count,0,-1)]
    files += [{'name':'Big Greasy Musical.mp4','size':'20'},{'name':'Dream Of The Dead.mp4','size':'20'},
              {'name':'EXTRAS/Promo.mp4','size':'20'},
              {'name':'SEASON 1/S01E01 - Episode 1.ia.mp4','format':'h.264 IA','size':'20'}]
    return {'metadata':{'title':'Mr. Meaty'},'files':files}


def test_meaty_order_deduplicates_derivatives_and_keeps_extras_separate():
    rows=a.meaty_queue(metadata())
    assert len(rows)==20
    assert 'S01E01' in rows[0]['title'] and rows[0]['archive_file'].endswith('.ia.mp4')
    assert 'S01E12' in rows[11]['title'] and 'S02E01' in rows[12]['title'] and 'S02E06' in rows[17]['title']
    assert [r['title'] for r in rows[-2:]]==['Special · Big Greasy Musical','Special · Dream Of The Dead']
    assert len(a.meaty_queue(metadata(),extras=True))==21


def test_meaty_missing_episode_is_reported():
    data=metadata();data['files']=[r for r in data['files'] if 'S02E03' not in r['name']]
    with pytest.raises(ValueError,match='S02E03'):a.meaty_queue(data)


def test_archive_file_paths_and_titles_are_safe():
    data={'metadata':{'title':'Movie'},'files':[{'name':'folder/a b.mp4','size':'10'}, {'name':'../bad.mp4'}, {'name':'x\n.mp4'}, {'name':'secret.mp4','private':'true'}, {'name':'sound.m4a'}]}
    rows=a.videos('fixture',data)
    assert len(rows)==1 and rows[0]['path'].endswith('folder/a%20b.mp4')
    assert a.label('hello\x1b\nworld')=='helloworld'
    with pytest.raises(ValueError):a.identifier('https://evil.test/details/foo')


def test_channel_skips_unavailable_and_keeps_mtv_first(monkeypatch):
    monkeypatch.setattr(a,'search',lambda *args:['missing',a.MTV])
    def queue(item):
        if item=='missing':raise ValueError('unavailable')
        return [{'title':item}]
    monkeypatch.setattr(a,'item_queue',queue)
    rows,errors=a.channel_queue('mtv')
    assert rows==[{'title':a.MTV}] and len(errors)==1


def box(kind,payload=b''):return struct.pack('>I4s',8+len(payload),kind)+payload

def sample(kind):
    data=box(b'stsd',b'\0'*4+struct.pack('>I',1)+box(kind))
    for name in (b'stbl',b'minf',b'mdia',b'trak',b'moov'):data=box(name,data)
    return data

@pytest.mark.parametrize('kind',[b'encv',b'enca',b'drmi',b'drms'])
def test_encrypted_sample_entry_blocks_generic_playback(tmp_path,kind):
    path=tmp_path/'purchase.m4v';path.write_bytes(sample(kind))
    assert protection.protected(path)
    with pytest.raises(ValueError,match='authorized provider'):protection.require_generic_playback(path)


def test_plain_m4v_and_payload_text_are_not_protection(tmp_path):
    path=tmp_path/'plain.m4v';path.write_bytes(box(b'mdat',b'encv drmi drms')+sample(b'avc1'))
    assert not protection.protected(path)
    path.write_bytes(b'\0\0\0\x01moov\0')
    assert not protection.protected(path)


def test_open_with_uses_only_source_owned_local_file(lk,tmp_path,monkeypatch):
    path=tmp_path/'movie.m4v';path.write_bytes(b'fixture')
    monkeypatch.setattr(lk,'_media_local_node_names',lambda:{'mac'})
    monkeypatch.setattr(lk.sys,'platform','darwin')
    run=Mock(return_value=Mock(returncode=0));monkeypatch.setattr(lk.subprocess,'run',run)
    opened,message=lk._media_open_with({'node':'3090','path':str(path)},'TV')
    assert not opened;run.assert_not_called()
    opened,message=lk._media_open_with({'node':'3090','path':'/remote','locations':[{'node':'mac','path':str(path)}]},'TV')
    assert opened and 'authorization' in message
    assert run.call_args.args[0]==['open','-a','/System/Applications/TV.app',str(path)]


def test_stream_queue_pinning_preserves_http_without_fabric_head(lk,monkeypatch):
    row={'path':'https://archive.org/download/item/movie.mp4','media_type':'video/mp4'}
    assert lk._media_pin_playable_entry(row)==row
    with pytest.raises(ValueError):lk._media_pin_playable_entry({'path':'https://archive.org/\nfile'})


def test_meaty_dispatch_uses_looping_existing_player(lk,monkeypatch):
    rows=[{'path':'https://archive.org/download/item/movie.mp4','media_type':'video/mp4','title':'episode'}]
    monkeypatch.setattr(a,'meaty_queue',lambda **kwargs:rows)
    # LK imports installed-style modules; bind the fixture adapter explicitly.
    monkeypatch.setitem(__import__('sys').modules,'archive_tv',a)
    start=Mock(return_value=0);monkeypatch.setattr(lk,'_media_launch_session',start)
    monkeypatch.setattr(lk.sys,'stdin',Mock(isatty=lambda:False))
    assert lk._media_archive_command([],meaty=True)==0
    session=start.call_args.args[0]
    assert session['repeat']=='all' and session['queue'][0]['path']==rows[0]['path']


def test_explicit_download_is_complete_and_does_not_overwrite(tmp_path,monkeypatch):
    response=io.BytesIO(b'video');monkeypatch.setattr(a.urllib.request,'urlopen',lambda *args,**kw:response)
    row={'archive_file':'folder/clip.mp4','path':'https://archive.org/download/item/clip.mp4','bytes':5}
    target=a.download(row,tmp_path)
    assert target.read_bytes()==b'video'
    with pytest.raises(ValueError,match='already exists'):a.download(row,tmp_path)


def test_incomplete_download_removes_partial_file(tmp_path,monkeypatch):
    monkeypatch.setattr(a.urllib.request,'urlopen',lambda *args,**kw:io.BytesIO(b'vid'))
    with pytest.raises(ValueError,match='Incomplete'):a.download({'archive_file':'clip.mp4','path':'https://archive.org/download/x/y','bytes':5},tmp_path)
    assert not list(tmp_path.iterdir())


def test_owner_protection_guard_blocks_head_and_body_before_range(tmp_path,monkeypatch):
    from core import node
    monkeypatch.setenv('HOME',str(tmp_path))
    folder=tmp_path/'.local/share/look';folder.mkdir(parents=True)
    (folder/'media_protection.py').write_text((ROOT/'look/media_protection.py').read_text())
    file=tmp_path/'purchase.m4v';file.write_bytes(sample(b'drmi'))
    monkeypatch.setattr(node,'identity',lambda:{'name':'owner'})
    monkeypatch.setattr(node,'_local_media_entry',lambda *args:({'media_type':'video/mp4'},file))
    handler=Mock()
    node.API._serve_media_item(handler,'owner','entry',head=True)
    handler.send_response.assert_called_once_with(409)
    handler.send_header.assert_any_call('X-LOOK-Media-Playback','requires-provider-app')
    handler._serve_file_range.assert_not_called()
    handler.reset_mock()
    node.API._serve_media_item(handler,'owner','entry')
    assert handler.sendj.call_args.args[0]==409
    handler._serve_file_range.assert_not_called()
    file.write_bytes(sample(b'avc1'));handler.reset_mock()
    node.API._serve_media_item(handler,'owner','entry')
    handler._serve_file_range.assert_called_once()


def test_selector_open_preserves_query_cursor_and_reserved_shortcut(lk,monkeypatch):
    from tests.test_hidden_and_player_visuals import terminal
    terminal(monkeypatch,lk)
    keys=iter(['down','O','T','\r']);monkeypatch.setattr(lk,'_read_tty_key',lambda *args:next(keys))
    rows=[{'title':str(i),'path':f'/movie{i}.mp4','id':str(i)} for i in range(2)]
    queries=[]
    monkeypatch.setattr(lk,'_media_filter_rows',lambda rows,query:(queries.append(query) or rows))
    monkeypatch.setattr(lk,'_media_collapse',lambda rows,**kw:rows)
    handoff=Mock(return_value=(True,'opened'));monkeypatch.setattr(lk,'_media_open_with',handoff)
    action,payload=lk._media_selector(rows,initial_query='movie')
    assert action=='play' and payload==[rows[1]]
    assert handoff.call_args_list[0].args==(rows[1],None)
    assert handoff.call_args_list[1].args==(rows[1],'TV')
    assert queries==['movie']


def test_download_on_filesystem_without_hardlinks(tmp_path,monkeypatch):
    import errno
    monkeypatch.setattr(a.urllib.request,'urlopen',lambda *args,**kwargs:io.BytesIO(b'video'))
    def no_links(*args):raise OSError(errno.EPERM,'hard links unsupported')
    monkeypatch.setattr(a.os,'link',no_links)
    row={'archive_file':'clip.mp4','path':'https://archive.org/download/item/clip.mp4','bytes':5}
    assert a.download(row,tmp_path).read_bytes()==b'video'
    assert sorted(p.name for p in tmp_path.iterdir())==['clip.mp4']
