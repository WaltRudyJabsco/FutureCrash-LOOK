"""Direct download requests never depend on model prose or filesystem guards."""
from unittest.mock import Mock

from look import lo_engine
import ytd
from test_media_request_regressions import lk


class Events:
    def __init__(self):self.rows=[]
    def emit(self,event,**fields):self.rows.append(dict(event=event,**fields))


def test_terminal_initial_prompt_uses_receipt_before_inference(lk,monkeypatch):
    monkeypatch.setattr(lk,'_save_recent_exchange',lambda *a:None)
    monkeypatch.setattr(lk,'_ollama_base',lambda *a:'http://local')
    monkeypatch.setattr(lk,'_ensure_ollama_server',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('must not infer')))
    calls=[]
    def request(action,**args):
        calls.append((action,args));return {'ok':True,'node':args['node'],'job':{'id':'terminal-job','stage':'queued'}}
    monkeypatch.setattr(ytd,'request',request)
    events=Events()
    assert lk.ollama_chat(initial_prompt='download this to the 3090 https://youtu.be/example',access_profile='workspace',one_shot=True,events=events)==0
    assert calls==[('download',{'node':'3090','url':'https://youtu.be/example'})]
    assert any(e.get('event')=='response' and 'terminal-job' in e['text'] for e in events.rows)


def test_interactive_terminal_and_browser_share_direct_handler(lk,monkeypatch):
    monkeypatch.setattr(ytd,'request',lambda *a,**kw:{'ok':True,'node':'tower','job':{'id':'same-receipt','stage':'queued'}})
    prompt='donwload this youtube video -- https://www.youtube.com/watch?v=example'
    events=Events()
    text=lk._lo_download_direct(prompt,'workspace',events)
    reply=lo_engine.chat_once(prompt)
    assert reply['text']==text and 'same-receipt' in text
    assert 'filesystem' not in text
    assert lk._lo_download_direct(prompt,'conservative',events) is None


def test_specialized_download_does_not_require_filesystem_mutation(lk):
    assert not lk._lo_requires_filesystem_action('save this youtube video to tower https://youtu.be/example')
    assert lk._lo_requires_filesystem_action('create a file at /tmp/example.txt')
