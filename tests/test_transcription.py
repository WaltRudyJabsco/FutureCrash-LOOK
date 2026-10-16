import json
from pathlib import Path
from types import SimpleNamespace
import pytest
import transcription as speech

@pytest.fixture
def audio(tmp_path):
    source=tmp_path/'audio.wav';source.write_bytes(b'original recording');return source


def test_local_file_adapter_is_offline_and_preserves_recording(audio,monkeypatch):
    seen=[]
    monkeypatch.setattr(speech,'settings',lambda:{'model':'custom-model'})
    monkeypatch.setattr(speech,'executable',lambda:'/engine/fermion')
    def run(command,**kwargs):
        seen.append((command,kwargs));return SimpleNamespace(returncode=0,stdout=json.dumps({'text':'Café.\x1b[2J','truncated':False}))
    monkeypatch.setattr(speech.subprocess,'run',run)
    assert speech.transcribe(audio)=='Café.\\x1b[2J'
    command,kwargs=seen[0]
    assert command==['/engine/fermion','transcribe','custom-model',str(audio),'--json']
    assert kwargs['env']['HF_HUB_OFFLINE']=='1'
    assert kwargs['env']['TRANSFORMERS_OFFLINE']=='1'
    assert audio.read_bytes()==b'original recording'


def test_truncated_or_failed_transcript_is_not_reported_as_success(audio,monkeypatch):
    monkeypatch.setattr(speech,'settings',lambda:{})
    monkeypatch.setattr(speech,'executable',lambda:'fermion')
    monkeypatch.setattr(speech.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout='{"text":"partial","truncated":true}'))
    with pytest.raises(ValueError,match='truncated'):speech.transcribe(audio)
    monkeypatch.setattr(speech.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=1,stderr='Model unavailable'))
    with pytest.raises(ValueError,match='Model unavailable'):speech.transcribe(audio)

@pytest.mark.parametrize('url',['https://example.org/v1','http://192.168.1.2/v1','http://user:pass@localhost/v1','file:///tmp/model'])
def test_adapter_rejects_nonlocal_or_credential_urls(url):
    with pytest.raises(ValueError):speech.server_url(url)


def test_local_server_adapter_uses_same_text_contract(audio,monkeypatch):
    monkeypatch.setattr(speech,'settings',lambda:{'server':'http://127.0.0.1:8000/v1','model':'replacement'})
    seen=[]
    class Response:
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def read(self):return b'{"text":"Server transcript"}'
    monkeypatch.setattr(speech.urllib.request,'urlopen',lambda req,**kw:seen.append(req) or Response())
    assert speech.transcribe(audio)=='Server transcript'
    assert seen[0].full_url=='http://127.0.0.1:8000/v1/audio/transcriptions'
    assert b'replacement' in seen[0].data and b'original recording' in seen[0].data


def test_missing_engine_has_setup_path_and_no_automatic_install(audio,monkeypatch):
    monkeypatch.setattr(speech,'settings',lambda:{})
    monkeypatch.setattr(speech,'executable',lambda:None)
    with pytest.raises(ValueError,match='lk transcribe setup'):speech.transcribe(audio)


def test_output_never_overwrites_existing_text(audio,tmp_path,monkeypatch):
    output=tmp_path/'saved.txt';output.write_text('Keep me')
    monkeypatch.setattr(speech,'transcribe',lambda *a:'new words')
    assert speech.main([str(audio),'--output',str(output)])==1
    assert output.read_text()=='Keep me'


def test_setup_and_microphone_are_not_called_by_status(monkeypatch,capsys):
    monkeypatch.setattr(speech,'settings',lambda:{})
    monkeypatch.setattr(speech,'executable',lambda:None)
    monkeypatch.setattr(speech,'setup',lambda:pytest.fail('automatic installation'))
    monkeypatch.setattr(speech,'dictate',lambda *a:pytest.fail('automatic microphone'))
    assert speech.main(['status'])==0
    assert json.loads(capsys.readouterr().out)['installed'] is False


def test_transcript_to_note_uses_existing_notebook_records(audio,tmp_path,monkeypatch,capsys):
    import notebook
    from notebook_core import Notebook
    store=Notebook(tmp_path/'notes',origin='test')
    monkeypatch.setattr(speech,'transcribe',lambda *a:'Spoken words, not shell commands.')
    monkeypatch.setattr(notebook,'Notebook',lambda:store)
    monkeypatch.setattr(notebook,'nudge_sync',lambda:None)
    assert speech.main([str(audio),'--note','Meeting','--json'])==0
    result=json.loads(capsys.readouterr().out)
    row=store.list()[0]
    assert result['note_id']==row['id']
    assert row['project']=='Transcripts' and row['title']=='Meeting'
    assert 'Spoken words, not shell commands.' in row['body']
