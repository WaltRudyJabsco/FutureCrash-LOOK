import io
import json
import socket
from types import SimpleNamespace
from unittest.mock import Mock

from core import ingress


def test_only_disc_scan_gets_long_control_deadline():
    scan = json.dumps({'action': 'scan', 'payload': {'drive': '/dev/sr0'}}).encode()
    assert ingress._request_timeout('/v1/media/import', 'POST', scan, False) == 320
    for body in (b'{', b'[]', b'{"action":"start"}', b'{"action":"jobs"}', b'\xff'):
        assert ingress._request_timeout('/v1/media/import', 'POST', body, False) == 12
    assert ingress._request_timeout('/v1/media/import', 'GET', scan, False) == 12
    assert ingress._request_timeout('/v1/media/catalog', 'GET', None, True) == 45
    assert ingress._request_timeout('/v1/media/item', 'GET', None, True) == 240


def test_relay_keeps_scan_deadline_and_returns_timeout_error(monkeypatch):
    body = b'{"action":"scan","payload":{}}'
    handler = object.__new__(ingress.Handler)
    handler.path = '/v1/media/import'
    handler.command = 'POST'
    handler.headers = {'Content-Length': str(len(body))}
    handler.rfile = io.BytesIO(body)
    handler.connection = Mock()
    handler.server = SimpleNamespace(backend_host='127.0.0.1', backend_port=7332)
    handler._authorized = Mock(return_value=True)
    handler._send_json = Mock()
    connection = Mock()
    connection.getresponse.side_effect = socket.timeout('waiting for disc')
    factory = Mock(return_value=connection)
    monkeypatch.setattr(ingress.http.client, 'HTTPConnection', factory)
    meter = ingress.Metrics()
    monkeypatch.setattr(ingress, 'METRICS', meter)
    handler._relay()
    factory.assert_called_once_with('127.0.0.1', 7332, timeout=320)
    handler.connection.settimeout.assert_called_once_with(320)
    assert handler._send_json.call_args.args[0] == 504
    assert 'before retrying' in handler._send_json.call_args.args[1]['error']
    assert meter.public()['active'] == 0
    assert meter.public()['errors'] == 1
    connection.close.assert_called_once()
