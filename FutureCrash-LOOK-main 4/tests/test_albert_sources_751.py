import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(tmp_path,monkeypatch):
    monkeypatch.setenv('HOME',str(tmp_path)); spec=importlib.util.spec_from_file_location('albert751',ROOT/'albert/server.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_saved_objects_are_server_durable_and_editable(tmp_path,monkeypatch):
    m=load(tmp_path,monkeypatch)
    row=m.saved_upsert({'id':'wx1','type':'answer','title':'The weather again','prompt':'the weather again'})
    assert row['title']=='Weather'
    assert m._read_saved()[0]['id']=='wx1'
    row=m.saved_patch('wx1',{'title':'Home Weather','pinned':True})
    assert row['title']=='Home Weather' and row['pinned'] is True
    assert m.saved_delete('wx1') is True and m._read_saved()==[]

def test_place_result_is_sourced_not_model_claim(tmp_path,monkeypatch):
    m=load(tmp_path,monkeypatch)
    monkeypatch.setattr(m,'places_search',lambda q,limit=6:[{'name':'Library','lat':45.5,'lon':-122.6,'address':'Library, Oregon','kind':'library'}])
    r=m.places_result('library in Oregon')
    assert r['type']=='places'
    assert r['evidence']==[{'class':'PLACES','source':'OpenStreetMap · Nominatim','confidence':'DIRECT','verified':True}]
    assert r['places'][0]['lat']==45.5

def test_place_intent_is_conservative(tmp_path,monkeypatch):
    m=load(tmp_path,monkeypatch)
    assert m._place_query('where is Powell Books?')=='Powell Books'
    assert m._place_query('tell me about maps in ancient Rome')==''

def test_browser_has_map_and_saved_management():
    text=(ROOT/'albert/index.html').read_text()
    assert 'renderPlaceMap(f)' in text
    assert "fetch('/api/saved'" in text
    assert 'renameSaved' in text and 'toggleSavedPin' in text and '>delete</button>' in text
