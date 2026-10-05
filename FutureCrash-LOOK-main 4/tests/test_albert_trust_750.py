import importlib.util
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def load_server(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME',str(tmp_path))
    spec=importlib.util.spec_from_file_location('albert_server_750',ROOT/'albert/server.py')
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_trust_evidence_never_marks_model_verified(tmp_path,monkeypatch):
    m=load_server(tmp_path,monkeypatch)
    ev=m._trust_evidence({'provenance':{'edge':'MODEL','source':'model','confidence':'INFERRED'}})
    assert ev==[{'class':'MODEL','source':'model','confidence':'INFERRED','verified':False}]


def test_direct_receipt_is_visibly_verified(tmp_path,monkeypatch):
    m=load_server(tmp_path,monkeypatch)
    ev=m._trust_evidence({'receipts':[{'edge':'WX','source':'Open-Meteo','confidence':'DIRECT'}]})
    assert ev[0]['class']=='WX'
    assert ev[0]['verified'] is True


def test_thread_survives_memory_reload(tmp_path,monkeypatch):
    m=load_server(tmp_path,monkeypatch)
    m._session_append('main','hello','hi')
    assert m.THREAD_FILE.exists()
    m._SESSIONS.clear()
    m._SESSIONS.update(m._load_threads())
    assert m._session_history('main')[-2:]==[{'role':'user','content':'hello'},{'role':'assistant','content':'hi'}]


def test_albert_browser_uses_shared_main_thread_and_no_startup_fold():
    text=(ROOT/'albert/index.html').read_text()
    assert "||'main'" in text
    assert "fetch('/api/thread?session='" in text
    assert "Albert 5 is awake" not in text
    assert 'renderTrust(f.evidence)' in text
    assert 'renderChoices(f)' in text
