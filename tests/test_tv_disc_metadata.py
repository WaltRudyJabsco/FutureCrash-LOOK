import json
from pathlib import Path
from unittest.mock import Mock
import pytest
from look import disc_metadata as metadata, disc_ui, disc_import, media_core


def test_tv_provider_preserves_specials_without_inventing_episode_numbers(monkeypatch):
    rows=[{'id':12,'name':'Pilot','season':1,'number':1,'runtime':28},
          {'id':13,'name':'Behind the scenes','season':1,'number':None},
          {'id':14,'name':'Bad','season':'1','number':2}]
    monkeypatch.setattr(metadata,'_tv_json',lambda route: rows)
    episodes=metadata.tv_episodes(10)['episodes']
    assert len(episodes)==2
    assert episodes[0]['source']=='https://www.tvmaze.com/episodes/12'
    assert episodes[1]['content_kind']=='special' and episodes[1]['episode'] is None
    with pytest.raises(ValueError):metadata.tv_episodes('../bad')


def test_tv_review_keeps_unnamed_titles_and_labels_extras():
    episodes=[{'title':'Pilot','season':1,'episode':1,'content_kind':'episode','source':'https://www.tvmaze.com/episodes/12'}]
    request=Mock(side_effect=[{'matches':[{'id':10,'title':'Series','source':'https://www.tvmaze.com/shows/10'}]}, {'episodes':episodes}])
    answers=iter(['Disc one','','y','Series','1','1','x Interview','0'])
    title,data=disc_ui.tv_details(request,lambda *args:next(answers),{},[
        {'index':'0','filename':'title_t00.mkv'}, {'index':'1','filename':'title_t01.mkv'}, {'index':'2','filename':'title_t02.mkv'}],'all')
    assert title=='Disc one'
    assert data['tv_titles']['0']['episode']==1
    assert data['tv_titles']['1']['content_kind']=='extra'
    assert '2' not in data['tv_titles']


def test_tv_lookup_failure_keeps_labels():
    title,data=disc_ui.tv_details(Mock(side_effect=OSError('offline')),lambda label,default='':default,
                                 {'title':'My disc'},[],'all')
    assert title=='My disc' and 'tv_titles' not in data


def test_mapping_rejects_invalid_numbers_and_paths():
    base={'series':'Series','title':'Pilot','content_kind':'episode','season':1,'episode':1}
    for changes in ({'filename':'../outside.mkv'},{'episode':False},{'series':''}):
        with pytest.raises(ValueError):metadata.validate_tv_titles({'0':dict(base,**changes)})


def test_worker_matches_scanned_filenames_not_sorted_episode_order(tmp_path,monkeypatch):
    import sys,uuid,time
    monkeypatch.setenv('HOME',str(tmp_path))
    monkeypatch.setattr(disc_import,'ROOT',tmp_path/'jobs')
    monkeypatch.setattr(disc_import,'LIBRARY',tmp_path/'library.json')
    tool=tmp_path/'reader'
    tool.write_text('#!'+sys.executable+'\nfrom pathlib import Path\nfor name in ("z_t00.mkv","a_t01.mkv","extra.mkv"):Path(name).write_bytes(b"media")\n')
    tool.chmod(0o755)
    monkeypatch.setattr(disc_import,'tool',lambda name:str(tool))
    monkeypatch.setattr(disc_import,'query',lambda *args:json.dumps({'streams':[{'codec_type':'video'}],'format':{'duration':'28'}}))
    identifier=uuid.uuid4().hex;dest=tmp_path/'TV';dest.mkdir()
    mapping={'0':{'series':'Series','title':'First','content_kind':'episode','season':1,'episode':1,'filename':'z_t00.mkv'},
             '1':{'series':'Series','title':'Second','content_kind':'episode','season':1,'episode':2,'filename':'a_t01.mkv'}}
    disc_import.atomic(disc_import.job_path(identifier),{'id':identifier,'kind':'dvd','category':'tv','state':'queued',
        'created':time.time(),'drive':{'id':'fixture','makemkv_source':'disc:0'},'title':'Disc one','title_index':'all',
        'destination':str(dest),'metadata':{'tv_titles':mapping},'cancel_requested':False})
    disc_import.worker(identifier)
    job=disc_import.read_job(identifier)
    assert job['state']=='complete',job
    folder=Path(job['output'])
    assert (folder/'Series - S01E01 - First.mkv').exists()
    assert (folder/'Series - S01E02 - Second.mkv').exists()
    assert (folder/'extra.mkv').exists()
    rows=json.loads(disc_import.LIBRARY.read_text())['entries']
    assert [(r['season'],r['episode']) for r in rows if r.get('series')]==[(1,1),(1,2)]


def test_barcode_lookup_requires_exact_digits_and_preserves_release_choice(monkeypatch):
    response={'releases':[{'id':'a','title':'My album','barcode':'012345678905'},
                          {'id':'b','title':'Wrong edition','barcode':'999999999999'}]}
    request=Mock(return_value=response)
    monkeypatch.setattr(metadata,'_music_json',request)
    assert [r['title'] for r in metadata.cd_barcode('0123 4567 8905')['releases']]==['My album']
    with pytest.raises(ValueError):metadata.cd_barcode('hello')
    assert request.call_count==1


def test_cd_barcode_fallback_confirms_release_and_matching_disc(monkeypatch):
    from look import media_storage
    monkeypatch.setattr(media_storage,'settings',lambda:{'node':'local','root':'~/Media'})
    monkeypatch.setattr('time.sleep',lambda seconds:None)
    inventory={'drives':[{'id':'drive','kind':'cd'}],'tools':{}}
    def request(action,payload):
        if action=='scan':return {'kind':'cd','tracks':2,'metadata':{},'releases':[]}
        if action=='cd-barcode':return {'releases':[{'title':'Album','release_id':'fixture'}]}
        if action=='cd-release':return {'releases':[{'title':'Album','artist':'Band','disc':1,'tracks':['One','Two']},
                                                  {'title':'Album','disc':2,'tracks':['Other']}]}
        raise AssertionError(action)
    def prompt(label,default=''):
        if label.startswith('Release number'):return '1'  # Track-count-only matches require review.
        return '012345678905' if label.startswith('CD barcode') else default
    payload=disc_ui.import_options(request,inventory,'drive',prompt,lambda label,default:default)
    assert payload['metadata']['tracks']==['One','Two'] and payload['metadata']['disc']==1


def test_series_search_separates_physical_disc_label():
    assert metadata.series_query('The Mighty Boosh Special Edition Disc 3')=='The Mighty Boosh'
    assert metadata.series_query('THE_MIGHTY_BOOSH_DISC2')=='THE MIGHTY BOOSH'
    assert metadata.series_query('2001 A Space Odyssey')=='2001 A Space Odyssey'


def test_discogs_release_preserves_positions_and_typo_without_guessing_seasons(monkeypatch):
    data={'title':'Box','artists':[{'name':'Series'}],'tracklist':[
        {'type_':'heading','title':'Seires Two'},
        {'type_':'track','position':'3-1','title':'Episode','duration':'28:25'},
        {'type_':'track','position':'3-2','title':'Interview','duration':''}]}
    monkeypatch.setattr(metadata,'_discogs_json',lambda *args:data)
    result=metadata.discogs_release('https://www.discogs.com/release/123-Box')['release']
    assert result['tracks'][0]['heading']=='Seires Two'
    assert result['tracks'][0]['position']=='3-1' and 'season' not in result['tracks'][0]
    assert result['tracks'][1]['content_kind']=='unclassified'
    with pytest.raises(ValueError):metadata.discogs_reference('https://evil.example/release/123')
    assert metadata.discogs_reference('[m2626853]')==('masters',2626853)


def test_duration_is_only_a_unique_review_suggestion():
    assert metadata.duration_suggestion({'duration':'0:28:25'},[{'duration':'28:25'}])=='1'
    assert metadata.duration_suggestion({'duration':'28:25'},[{'duration':'28:25'},{'duration':'28:26'}]) is None
    assert metadata.duration_suggestion({'duration':'28:25'},[{'duration':'28:30'}]) is None


def test_discogs_edition_then_disc_then_tv_enrichment(monkeypatch):
    release={'id':123,'artist':'Series','title':'Special Edition','year':'2008','country':'UK','source':'Discogs',
             'tracks':[{'title':'Pilot','position':'1-1','duration':'28:25','source':'Discogs','content_kind':'unclassified'},
                       {'title':'Extra','position':'2-1','duration':'','source':'Discogs','content_kind':'unclassified'}]}
    def request(action,payload):
        if action=='discogs-release':
            if payload['id']=='m1':return {'master':{'title':'Box'},'editions':[{'id':123,'country':'UK','year':'2008','title':'Box','format':'DVD'}]}
            return {'release':release}
        if action=='tv-lookup':return {'matches':[{'id':10,'title':'Series','source':'TVmaze'}]}
        if action=='tv-episodes':return {'episodes':[{'title':'Pilot','season':1,'episode':1,'content_kind':'episode','source':'TVmaze'}]}
        raise AssertionError(action)
    answers=iter(['Series Disc 1','m1','1','y','1','y','Series','1','1'])
    title,data=disc_ui.tv_details(request,lambda *args:next(answers),{},[{'index':'0','duration':'28:25','filename':'t00.mkv'}],'all')
    assert data['discogs_release']['id']==123
    assert data['tv_titles']['0']['episode']==1 and data['tv_titles']['0']['filename']=='t00.mkv'


def test_confirmed_box_set_suggestion_stays_with_its_series(monkeypatch):
    monkeypatch.setattr(disc_import,'list_jobs',lambda **kwargs:[{'category':'tv','title':'Series Special Edition Disc 1',
        'metadata':{'series':'Series','discogs_release':{'id':123}}}])
    assert disc_import.video_metadata('Series Special Edition Disc 2')['discogs_release']['id']==123
    assert 'discogs_release' not in disc_import.video_metadata('Another Show Disc 1')
