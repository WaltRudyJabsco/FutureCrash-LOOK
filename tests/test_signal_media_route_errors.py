import importlib.util
from pathlib import Path
import sys
import urllib.error
from unittest.mock import Mock

import pytest
from core import ingress

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture
def signal_server(monkeypatch):
    spec=importlib.util.spec_from_file_location('signal_route_test',ROOT/'signal-window/server.py')
    module=importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules,spec.name,module)
    spec.loader.exec_module(module)
    return module


def test_route_timeout_has_explicit_error_but_optional_observations_keep_fallback(signal_server,monkeypatch):
    def failed(*args,**kwargs):raise urllib.error.URLError(TimeoutError('timed out'))
    monkeypatch.setattr(signal_server.urllib.request,'urlopen',failed)
    with pytest.raises(RuntimeError,match='preparation timed out'):
        signal_server._media_play('Ninja Scroll',prepare=True)
    assert signal_server._node_get('/v1/activity') is None


def test_connection_failure_reports_reason(signal_server,monkeypatch):
    def failed(*args,**kwargs):raise urllib.error.URLError(ConnectionRefusedError('connection refused'))
    monkeypatch.setattr(signal_server.urllib.request,'urlopen',failed)
    with pytest.raises(RuntimeError,match='connection refused'):
        signal_server._media_play('Ninja Scroll',prepare=True)


def test_only_queue_preparation_and_play_get_long_gateway_deadline():
    for operation in ('prepare','play'):
        body=('{"operation":"'+operation+'"}').encode()
        assert ingress._request_timeout('/v1/media/route','POST',body,False)==100
    assert ingress._request_timeout('/v1/media/route','POST',b'{"operation":"control"}',False)==12
