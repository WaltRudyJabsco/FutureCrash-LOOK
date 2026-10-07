import io
import json
import ssl
import urllib.error

import pytest
from core import fabric_client as client


def setup_workers(monkeypatch, names=('bad', 'good')):
    snap = {'self': {'name': 'origin'}, 'peers': [
        {'name': name, 'url': f'https://{name}.example:7443',
         'node': {'identity': {'name': name}, 'inference': {
             'models': [{'name': 'vision', 'features': {'text': True, 'vision': True}}]}}}
        for name in names]}
    monkeypatch.setattr(client, '_nodes', lambda base: snap)
    def choose(snapshot, **kw):
        for name in names:
            if name not in kw['exclude']:
                return 0, name, name + '.example', [{'name': 'vision'}]
        raise RuntimeError('no eligible workers')
    monkeypatch.setattr(client, '_choose_from_snapshot', choose)
    monkeypatch.setattr(client.time, 'sleep', lambda seconds: None)
    return {'messages': [{'role': 'user', 'content': 'read this chart', 'images': ['aW1hZ2U=']}]}


class Response:
    headers = {}
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def __iter__(self):
        yield b'{"message":{"content":"chart read"},"done":true}\n'


def tls_failure():
    return urllib.error.URLError(ssl.SSLCertVerificationError(1, 'unable to get local issuer certificate'))


@pytest.mark.parametrize('failure', [tls_failure(), TimeoutError('upload timeout')])
def test_image_upload_transport_failure_tries_another_vision_worker(monkeypatch, failure):
    payload = setup_workers(monkeypatch)
    uploads = []
    def stage(url, data, timeout):
        uploads.append((url, data))
        if 'bad.example' in url: raise failure
        return {'artifact': {'digest': 'sha256:' + 'a' * 64}}
    monkeypatch.setattr(client, '_json', stage)
    packets = []
    def open_stream(req, **kw):
        packets.append(json.loads(req.data))
        assert 'good.example' in req.full_url
        return Response()
    monkeypatch.setattr(client, '_open', open_stream)
    route = {}
    events = list(client.stream_infer(payload, requires=['text', 'vision'], route=route))
    assert events[-1]['done']
    assert route['target'] == 'good'
    assert len(uploads) == 2
    assert all(data['base64'] == 'aW1hZ2U=' for _, data in uploads)
    message = packets[0]['packet']['work']['input']['messages'][0]
    assert 'images' not in message
    assert message['image_artifacts'] == ['sha256:' + 'a' * 64]
    assert payload['messages'][0]['images'] == ['aW1hZ2U=']


def test_tls_failure_retains_worker_and_upload_diagnostic(monkeypatch):
    payload = setup_workers(monkeypatch, names=('bad',))
    def fail(*args, **kw): raise tls_failure()
    monkeypatch.setattr(client, '_json', fail)
    with pytest.raises(RuntimeError) as error:
        list(client.stream_infer(payload, requires=['vision']))
    detail = str(error.value)
    assert 'image upload failed on bad' in detail
    assert 'https://bad.example:7443/v1/artifacts' in detail
    assert 'TLS certificate verification failed' in detail
    assert 'aW1hZ2U=' not in detail


def test_upload_authorization_failure_does_not_reroute(monkeypatch):
    payload = setup_workers(monkeypatch)
    calls = []
    def fail(url, *args, **kw):
        calls.append(url)
        raise urllib.error.HTTPError(url, 403, 'denied', {}, io.BytesIO(b'{"error":"denied"}'))
    monkeypatch.setattr(client, '_json', fail)
    with pytest.raises(RuntimeError, match='image upload HTTP 403 on bad'):
        list(client.stream_infer(payload, requires=['vision']))
    assert len(calls) == 1


def test_stream_failure_after_answer_starts_does_not_replay(monkeypatch):
    payload = setup_workers(monkeypatch)
    monkeypatch.setattr(client, '_json', lambda *a, **kw: {'artifact': {'digest': 'sha256:' + 'a' * 64}})
    calls = []
    class Partial(Response):
        def __iter__(self):
            yield b'{"message":{"content":"partial"}}\n'
            raise tls_failure()
    monkeypatch.setattr(client, '_open', lambda *a, **kw: calls.append(kw['url']) or Partial())
    stream = client.stream_infer(payload, requires=['vision'])
    assert next(stream)['_fabric_meta'] == 'route'
    assert next(stream)['message']['content'] == 'partial'
    with pytest.raises(RuntimeError, match='inference stream failed on bad'):
        next(stream)
    assert len(calls) == 1


def test_diagnostics_strip_url_secrets():
    error = client._transport_failure(tls_failure(), target='peer',
        endpoint='https://user:password@peer.example:7443/v1/artifacts?token=secret', stage='image upload')
    assert 'https://peer.example:7443/v1/artifacts' in str(error)
    assert all(value not in str(error) for value in ('password', 'token=', 'secret'))
