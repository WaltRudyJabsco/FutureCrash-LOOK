import json
from pathlib import Path
from unittest.mock import Mock
import pytest
from look import media_core
from look import media_metadata as metadata
from core import node


@pytest.fixture
def catalog(tmp_path):
    album=tmp_path/'music'/'Album';album.mkdir(parents=True)
    for number in (1,2):(album/f'{number:02d} Song {number}.flac').write_bytes(b'unchanged audio'+bytes([number]))
    path=tmp_path/'catalog.json'
    media_core.update_library(path,lambda current:media_core.scan_root(album,current))
    return path,album


def payload(path,changes):
    rows=json.loads(path.read_text())['entries']
    return {'changes':changes,'entries':[{'id':row['id'],'expected':{key:row.get(key) for key in metadata.EXPECTED}} for row in rows]}


def test_bulk_artist_preserves_titles_audio_and_survives_rescan(catalog):
    path,album=catalog;before={p.name:p.read_bytes() for p in album.glob('*.flac')}
    result=metadata.edit(path,payload(path,{'artist':'Stéphane Grappelli','album':'Just One of Those Things'}))
    assert result['count']==2
    assert [row['title'] for row in result['entries']]==['Song 1','Song 2']
    assert {p.name:p.read_bytes() for p in album.glob('*.flac')}==before
    rescanned=media_core.scan_root(album,json.loads(path.read_text()))
    assert all(row['artist']==row['album_artist']=='Stéphane Grappelli' for row in rescanned['entries'])
    assert all(row['album']=='Just One of Those Things' for row in rescanned['entries'])


def test_bulk_metadata_preserves_sidecar_and_compilation_artist(catalog):
    path,album=catalog
    sidecar=next(album.glob('*.flac')).with_suffix('.info.json')
    sidecar.write_text(json.dumps({'description':'Source details','webpage_url':'https://example.org','album_artist':'Various Artists'}))
    media_core.update_library(path,lambda current:media_core.scan_root(album,current))
    metadata.edit(path,payload(path,{'artist':'Performer'}))
    data=json.loads(sidecar.read_text())
    assert data['description']=='Source details' and data['album_artist']=='Various Artists'


def test_stale_metadata_rejected_before_any_batch_write(catalog):
    path,album=catalog;old=payload(path,{'artist':'First'})
    metadata.edit(path,old)
    before={p.name:p.read_bytes() for p in album.glob('*.info.json')}
    with pytest.raises(ValueError,match='changed since'):metadata.edit(path,{**old,'changes':{'artist':'Second'}})
    assert {p.name:p.read_bytes() for p in album.glob('*.info.json')}==before


def test_invalid_last_sidecar_leaves_entire_batch_untouched(catalog):
    path,album=catalog;sidecar=sorted(album.glob('*.flac'))[-1].with_suffix('.info.json');sidecar.write_text('invalid JSON')
    before=path.read_bytes()
    with pytest.raises(ValueError):metadata.edit(path,payload(path,{'artist':'New Artist'}))
    assert path.read_bytes()==before
    assert len(list(album.glob('*.info.json')))==1 and sidecar.read_text()=='invalid JSON'


def test_failed_catalog_commit_rolls_back_metadata_sidecars(catalog,monkeypatch):
    path,album=catalog;original=metadata.atomic
    def fail(destination,data):
        if destination==path:raise OSError('write failure')
        original(destination,data)
    monkeypatch.setattr(metadata,'atomic',fail)
    with pytest.raises(OSError):metadata.edit(path,payload(path,{'artist':'New Artist'}))
    assert not list(album.glob('*.info.json'))


@pytest.mark.parametrize('changes',[{}, {'unsupported':'value'}, {'artist':''}, {'track':True}, {'disc':0}, {'title':'line\nbreak'}])
def test_metadata_fields_validate_at_edge(catalog,changes):
    path,_=catalog
    with pytest.raises(ValueError):metadata.edit(path,payload(path,changes))


def test_endpoint_rejects_unauthorized_requests_before_edit(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules,'media_metadata',metadata)
    edited=Mock();monkeypatch.setattr(metadata,'edit',edited)
    value=node.API.__new__(node.API);value.path='/v1/media/metadata'
    value._authorized_ingress=lambda path:False
    value.do_POST();edited.assert_not_called()


def test_endpoint_edits_owner_catalog_and_invalidates_cache(monkeypatch,catalog):
    import sys
    path,_=catalog
    monkeypatch.setitem(sys.modules,'media_metadata',metadata)
    monkeypatch.setattr(node,'_look_catalog_modules',lambda:None)
    monkeypatch.setattr(node,'LOOK_MEDIA_LIBRARY',path)
    monkeypatch.setattr(node,'identity',lambda:{'name':'owner'})
    value=node.API.__new__(node.API);value.path='/v1/media/metadata'
    value._authorized_ingress=lambda path:True;value.body=lambda:payload(path,{'artist':'New Artist'});value.sendj=Mock()
    value.do_POST()
    assert value.sendj.call_args.args[0]==200 and value.sendj.call_args.args[1]['count']==2


def test_cli_routes_one_batch_to_owner(monkeypatch,capsys):
    import sys
    routed=Mock(return_value={'ok':True,'count':2});monkeypatch.setattr(node,'_target_post',routed)
    monkeypatch.setattr(sys,'argv',['fcl-node','media-edit','{"changes":{"artist":"New Artist"},"entries":[]}','--node','owner','--json'])
    assert node.main()==0
    assert routed.call_args.args[2:4]==('owner','/v1/media/metadata')


def test_external_sidecar_correction_is_not_overwritten(catalog):
    path,album=catalog;old=payload(path,{'artist':'Older view'})
    sidecar=next(album.glob('*.flac')).with_suffix('.info.json');sidecar.write_text('{"artist":"New external correction"}')
    with pytest.raises(ValueError,match='sidecar changed'):metadata.edit(path,old)
    assert json.loads(sidecar.read_text())['artist']=='New external correction'
