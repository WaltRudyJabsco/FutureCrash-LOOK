import io
import json
import sqlite3
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
import words
import player_visuals
from test_media_request_regressions import lk


@pytest.fixture
def home(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    monkeypatch.setattr(words,'system_wordlists',lambda:[])
    monkeypatch.setattr(words.shutil,'which',lambda name:None)
    monkeypatch.setattr(words,'portable_spelling',Mock(return_value=None))
    return tmp_path


def archive():
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w') as z:
        z.writestr('entries-g.json',json.dumps({'good':{'a':{'form':['better'],'sense':[{'id':'good-id','synset':'good-s','antonym':['bad-id']}]}}}))
        z.writestr('entries-b.json',json.dumps({'bad':{'a':{'sense':[{'id':'bad-id','synset':'bad-s'}]}},'benefit':{'n':{'sense':[{'id':'benefit-id','synset':'benefit-s'}]}}}))
        z.writestr('adj.all.json',json.dumps({'good-s':{'definition':['having desirable qualities'],'members':['good','fine'],'partOfSpeech':'a','example':['a good book'],'similar':['benefit-s']},'bad-s':{'definition':['having undesirable qualities'],'members':['bad'],'partOfSpeech':'a'},'benefit-s':{'definition':['something helpful'],'members':['benefit'],'partOfSpeech':'n'}}))
    return data.getvalue()


@pytest.fixture
def installed(home):
    words.root().mkdir(parents=True)
    words.build_database(io.BytesIO(archive()),words.database())
    return home


def test_offline_definitions_forms_relations_and_readonly_index(installed,monkeypatch):
    monkeypatch.setattr(words.urllib.request,'build_opener',Mock(side_effect=AssertionError('No network during reads')))
    before=words.database().read_bytes()
    result=words.lookup('BETTER')
    assert result['source']==words.EDITION
    assert result['source_url']==words.SOURCE
    row=result['results'][0]
    assert row['lemma']=='good' and row['antonyms']==['bad'] and row['synonyms']==['fine']
    assert row['related']=={'similar':['benefit']} and row['examples']==['a good book']
    assert words.database().read_bytes()==before
    assert words.find('b?d')['matches']==['bad']
    assert words.find('%')['matches']==[]  # SQL wildcard is literal.
    assert not words.lookup('unlisted')['found']


def test_fresh_home_reads_do_not_download_or_create_state(home):
    assert not words.status()['installed']
    assert not words.lookup('good')['found']
    assert words.spell('Unlisted')['words'][0]['recognized'] is None
    assert not words.root().exists()


def test_system_spell_batch_priority_and_no_shell(installed,monkeypatch):
    monkeypatch.setattr(words.shutil,'which',lambda name:'/bin/hunspell' if name=='hunspell' else None)
    run=Mock(return_value=SimpleNamespace(returncode=0,stdout='@ Hunspell\n*\n\n& goood 1 1: good\n\n'))
    monkeypatch.setattr(words.subprocess,'run',run)
    value=words.spell('good goood good',language='en_GB')
    assert [r['recognized'] for r in value['words']]==[True,False]
    assert value['words'][1]['suggestions']==['good']
    run.assert_called_once()
    assert run.call_args.args[0]==['/bin/hunspell','-d','en_GB','-a']
    assert run.call_args.kwargs['input']=='^good\n^goood\n' and 'shell' not in run.call_args.kwargs


def test_personal_words_unicode_and_unknowns_are_not_false_errors(installed):
    words.add_personal('Zoë');words.add_personal('Zoë')
    personal=words.personal_path().read_text()
    assert personal=='Zoë\n'
    value=words.spell('Zoë good goood')
    assert [r['recognized'] for r in value['words']]==[True,True,None]
    assert value['words'][2]['suggestions']==['good']
    assert 'not proof' in value['note']
    with pytest.raises(ValueError):words.add_personal('two\nlines')


def test_portable_spelling_recognizes_affixes_without_native_tools(home,monkeypatch):
    dictionary=Mock();dictionary.lookup.side_effect=lambda value:value in {'the','running'}
    monkeypatch.setattr(words,'portable_spelling',Mock(return_value=(dictionary,'SCOWL en_US · Spylls 0.1.7')))
    assert [r['recognized'] for r in words.spell('the running goood')['words']]==[True,True,False]


def test_setup_failure_preserves_existing_dictionary(installed,monkeypatch):
    before=words.database().read_bytes()
    monkeypatch.setattr(words,'download',Mock(side_effect=ValueError('checksum mismatch')))
    with pytest.raises(ValueError,match='checksum'):words.setup()
    assert words.database().read_bytes()==before
    assert not list(words.root().glob('.setup-*'))


def test_setup_atomically_builds_dictionary_and_spell_package(home,monkeypatch):
    monkeypatch.setattr(words,'download',lambda url,checksum:archive() if url==words.DOWNLOAD else b'spelling')
    def spelling(data,path):
        file=path/'spylls/hunspell/data/en/en_US.dic';file.parent.mkdir(parents=True);file.write_text('good')
    monkeypatch.setattr(words,'install_spelling',spelling)
    value=words.setup()
    assert value['installed'] and value['portable_spelling'] and value['definitions']==3
    assert words.lookup('good')['found']


def test_download_validates_checksum_and_redirect_host(home,monkeypatch):
    monkeypatch.setattr(words.urllib.request,'build_opener',lambda *a:SimpleNamespace(open=lambda *a,**kw:io.BytesIO(b'wrong')))
    with pytest.raises(ValueError,match='checksum'):words.download(words.DOWNLOAD,words.SHA256)
    with pytest.raises(ValueError):words.Redirects().redirect_request(None,None,302,'',{},'http://en-word.net/data')
    with pytest.raises(ValueError):words.Redirects().redirect_request(None,None,302,'',{},'https://evil.example/data')


def test_input_boundaries_and_malicious_package(home):
    for value in ['bad\x1b[31m','bad\x00','x'*201]:
        with pytest.raises(ValueError):words.lookup(value)
    with pytest.raises(ValueError):words.spell('word',language='fr_FR')
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w') as z:z.writestr('../outside','bad')
    with pytest.raises(ValueError,match='path'):words.install_spelling(data.getvalue(),home/'package')
    assert not (home/'outside').exists()


def test_word_tool_is_readonly_and_routed_without_network(lk,installed):
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
    import cognition
    schema=next(v['function'] for v in lk._information_tools() if v['function']['name']=='word_reference')
    assert 'setup' not in schema['parameters']['properties']['action']['enum']
    assert json.loads(lk._word_reference({'action':'lookup','query':'good'}))['found']
    route=cognition.analyze('Find synonyms for good',use_openjev=False)
    assert 'word_reference' in route.allowed_tools


def test_node_setup_needs_explicit_confirmation(home,monkeypatch):
    import node
    monkeypatch.setattr(node,'_look_catalog_modules',lambda:None)
    setup=Mock();monkeypatch.setattr(words,'setup',setup)
    handler=SimpleNamespace(_file_target=lambda:(None,{}),sendj=lambda code,value:(code,value))
    code,value=node.API._words_request(handler,{'action':'setup'})
    assert code==400 and not value['ok'];setup.assert_not_called()
    assert node.API._words_request(handler,{'action':'status'})[0]==200


@pytest.mark.parametrize('size',[(1,1),(20,6),(90,25),(240,80)])
def test_kinetic_mobile_bounded_pause_determinism_and_cycle(size):
    width,height=size;mode=player_visuals.NAMES.index('Kinetic Mobile')+1
    frame=player_visuals.frame(mode,width,height,1.3,True,9)
    assert len(frame)==height and all(len(row)==width for row in frame)
    assert all(ord(c)<128 for row in frame for c in row)
    assert frame==player_visuals.frame(mode,width,height,1.3,True,9)
    assert player_visuals.frame(mode,width,height,1,False,9)==player_visuals.frame(mode,width,height,9,False,9)
    assert mode in {player_visuals.active_mode(player_visuals.CYCLE_MODE,n*10) for n in range(player_visuals.CYCLE_MODE-1)}
    if width>=20:assert frame!=player_visuals.frame(mode,width,height,5,True,9)


def test_system_wordnet_fallback_does_not_claim_missing_entries(home,monkeypatch):
    monkeypatch.setattr(words.shutil,'which',lambda name:'/bin/wn' if name=='wn' else None)
    run=Mock(return_value=SimpleNamespace(returncode=4,stdout='Overview of noun good\n1. something desirable'))
    monkeypatch.setattr(words.subprocess,'run',run)
    value=words.lookup('good')
    assert value['found'] and value['source']=='System WordNet'
    run.return_value=SimpleNamespace(returncode=0,stdout='No information available')
    assert not words.lookup('unlisted')['found']


def test_words_cli_json_and_persistent_desk_dispatch(lk,installed,monkeypatch,capsys):
    assert words.main(['lookup','good','--json'])==0
    assert json.loads(capsys.readouterr().out)['found']
    import words_desk
    monkeypatch.setattr(words.sys.stdout,'isatty',lambda:True)
    monkeypatch.setattr(words.sys.stdin,'isatty',lambda:True)
    desk=Mock(return_value=0);monkeypatch.setattr(words_desk,'desk',desk)
    assert words.main([],lk)==0
    desk.assert_called_with(lk,node=None,language='en_US',initial='',view=0)
    assert words.main(['lookup','good'],lk)==0
    desk.assert_called_with(lk,node=None,language='en_US',initial='good',view=0)
    assert words.main(['spell','good text'],lk)==0
    assert desk.call_args.kwargs['view']==3


def test_cited_examples_keep_text_and_author_without_crashing(installed):
    with sqlite3.connect(words.database()) as db:
        payload=json.loads(db.execute("SELECT payload FROM synsets WHERE id='good-s'").fetchone()[0])
        payload['example']=[{'text':'A good example.','source':'An author'}]
        db.execute("UPDATE synsets SET payload=? WHERE id='good-s'",(json.dumps(payload),))
    value=words.lookup('good')
    assert value['results'][0]['examples']==['A good example. — An author']
    assert 'A good example. — An author' in words.display(value)


def test_launch_words_use_real_entries_without_repeats_until_pool_recycles(installed,monkeypatch):
    monkeypatch.setattr(words,'LAUNCH_WORDS',('good','bad','benefit'))
    before=words.database().read_bytes()
    values=[words.launch_word() for _ in range(6)]
    assert len({v['word'] for v in values[:3]})==3
    assert len({v['word'] for v in values[3:]})==3
    assert values[2]['word']!=values[3]['word']
    assert all(v['definition'] and v['source']==words.EDITION for v in values)
    assert words.database().read_bytes()==before


def test_launch_word_without_installed_data_does_not_create_state(home):
    assert words.launch_word() is None
    assert not words.root().exists()


def test_wd_alias_dispatches_to_words_and_preserves_arguments(lk,monkeypatch):
    import sys
    main=Mock(return_value=0);monkeypatch.setattr(words,'main',main)
    monkeypatch.setattr(sys,'argv',['lk','wd','lookup','obtuse'])
    assert lk.main()==0
    assert main.call_args.args[0]==['lookup','obtuse']
