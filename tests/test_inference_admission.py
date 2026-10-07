import io
import threading
from unittest.mock import Mock

import pytest
from core import node


@pytest.fixture
def worker(monkeypatch, tmp_path):
    store = node.FabricStore(tmp_path / 'jobs.sqlite3')
    sup = node.Supervisor()
    monkeypatch.setattr(node, 'FABRIC_STORE', store)
    monkeypatch.setattr(node, 'SUP', sup)
    monkeypatch.setattr(node, 'identity', lambda: {'name': 'test-worker'})
    monkeypatch.setattr(node, '_job_authorized', lambda *a: (True, ''))
    monkeypatch.setattr(node, '_requirements_ok', lambda *a: (True, []))
    monkeypatch.setattr(node, 'load_curator_state', lambda: {'mode': 'observe'})
    monkeypatch.setattr(node.MODELS, 'snapshot', lambda: [{'name': 'vision'}])
    return store, sup


def packet(**input_extra):
    return {'work': {'operation': 'model.infer', 'input': {'model': 'vision', **input_extra}},
            'execution': {'priority': 'interactive'}}


class Handler:
    def __init__(self): self.wfile = io.BytesIO()
    def send_response(self, code): assert code == 200
    def send_header(self, *a): pass
    def end_headers(self): pass


class Upstream:
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def __iter__(self):
        yield b'{"message":{"content":"chart"},"done":true}\n'


def test_busy_stream_never_creates_executable_job(worker, monkeypatch):
    store, sup = worker
    active, _ = sup.acquire('real-user')
    prepare = Mock()
    monkeypatch.setattr(node, '_curator_prepare_packet', prepare)
    for _ in range(3):
        with pytest.raises(RuntimeError, match='worker busy'):
            node._stream_model_infer(Handler(), packet())
    assert store.jobs() == []
    prepare.assert_not_called()
    assert sup.status()['active']['id'] == active['id']


def test_stream_reserves_worker_before_submission_and_preparation(worker, monkeypatch):
    store, sup = worker
    submit = store.submit
    observed = []
    def checked_submit(*a, **kw):
        assert sup.status()['active']['priority'] == 'interactive'
        observed.append('submit')
        return submit(*a, **kw)
    monkeypatch.setattr(store, 'submit', checked_submit)
    def prepare(p, lease_id):
        assert not sup.cancelled(lease_id)
        observed.append('prepare')
    monkeypatch.setattr(node, '_curator_prepare_packet', prepare)
    monkeypatch.setattr(node.urllib.request, 'urlopen', lambda *a, **kw: Upstream())
    handler = Handler()
    node._stream_model_infer(handler, packet())
    assert observed == ['submit', 'prepare']
    assert b'chart' in handler.wfile.getvalue()
    assert store.jobs()[0]['status'] == 'ok'
    assert sup.status()['active'] is None


def test_hydration_failure_leaves_terminal_job_and_releases_worker(worker, monkeypatch):
    store, sup = worker
    def fail(digest): raise FileNotFoundError('missing image')
    monkeypatch.setattr(node.ARTIFACTS, 'get', fail)
    with pytest.raises(FileNotFoundError):
        node._stream_model_infer(Handler(), packet(messages=[{'role': 'user', 'image_artifacts': ['missing']}]))
    assert store.jobs()[0]['status'] == 'failed'
    assert sup.status()['active'] is None


def test_duplicate_stream_preserves_original_job(worker):
    store, sup = worker
    p = node.normalize_packet(packet(), origin='test-worker')
    job, _ = store.submit(p, node='test-worker')
    store.finish(job['id'], 'ok', node='test-worker')
    with pytest.raises(ValueError, match='already exists'):
        node._stream_model_infer(Handler(), p)
    assert store.get_job(job['id'])['status'] == 'ok'
    assert sup.status()['active'] is None


def test_curation_lock_rejects_without_waiting_or_queueing(worker, monkeypatch):
    store, sup = worker
    held = threading.Event()
    release = threading.Event()
    lock = threading.RLock()
    monkeypatch.setattr(node, 'CURATOR_LOCK', lock)
    def hold():
        with lock:
            held.set()
            release.wait(5)
    thread = threading.Thread(target=hold)
    thread.start()
    assert held.wait(2)
    try:
        with pytest.raises(RuntimeError, match='curation in progress'):
            node._stream_model_infer(Handler(), packet())
        assert store.jobs() == []
    finally:
        release.set(); thread.join(2)


def test_preempted_background_executor_observes_cancellation():
    sup = node.Supervisor()
    bg, _ = sup.acquire('qualify', 'background')
    human, _ = sup.acquire('lo', 'interactive')
    assert sup.cancelled(bg['id'])
    assert not sup.cancelled(human['id'])
    sup.release(human['id'])
    assert sup.cancelled(human['id'])


def curator_fixture(monkeypatch, worker):
    store, sup = worker
    plan = {'ok': True, 'eligible': ['vision', 'largest'], 'target': ['largest'],
            'current': ['largest'], 'reason': 'deep recommendation', 'budget': {}}
    monkeypatch.setattr(node, 'curator_plan', lambda *a, **kw: plan)
    actions = []
    def action(name, keep):
        assert sup.status()['active'] is not None
        actions.append((name, keep))
    monkeypatch.setattr(node, '_ollama_residency_action', action)
    monkeypatch.setattr(node.MODELS, 'discover', lambda **kw: [])
    monkeypatch.setattr(node, 'refresh_advertisement', lambda: None)
    monkeypatch.setattr(node, 'save_curator_state', lambda s: None)
    return plan, actions


def test_deep_preparation_keeps_the_routed_model(worker, monkeypatch):
    _, sup = worker
    _, actions = curator_fixture(monkeypatch, worker)
    lease, _ = sup.acquire('lo')
    result = node.curator_apply('deep', lease_id=lease['id'], target_model='vision')
    assert result['target'] == ['vision']
    assert actions == [('largest', False)]
    assert result['loaded'] == []  # /api/chat owns the single load at its actual context size
    assert sup.status()['active']['id'] == lease['id']


def test_background_policy_never_cold_loads(worker, monkeypatch):
    plan, actions = curator_fixture(monkeypatch, worker)
    plan['target'] = ['vision']
    result = node.curator_apply(reason='background policy', allow_load=False)
    assert 'deferred' in result
    assert actions == []
    assert worker[1].status()['active'] is None


def test_manual_curation_cannot_touch_an_active_request(worker, monkeypatch):
    _, actions = curator_fixture(monkeypatch, worker)
    worker[1].acquire('lo')
    result = node.curator_apply()
    assert result['skipped'] == 'supervisor busy'
    assert actions == []


def test_background_worker_discards_old_stream_backlog_but_runs_normal_jobs(worker, monkeypatch):
    store, sup = worker
    old = packet()
    old['work']['objective'] = 'stream conversational inference'
    old = node.normalize_packet(old, origin='lo')
    stream_job, _ = store.submit(old, node='test-worker')
    normal = node.normalize_packet(packet(), origin='app')
    normal_job, _ = store.submit(normal, node='test-worker')
    wake = Mock()
    wake.wait.side_effect = [None, KeyboardInterrupt()]
    monkeypatch.setattr(node, 'JOB_WAKE', wake)
    monkeypatch.setattr(node, 'WORKER_HEALTH', {})
    monkeypatch.setattr(node, 'benchmark_guard_active', lambda: False)
    monkeypatch.setattr(node, '_dependencies_ready', lambda p: True)
    execute = Mock(return_value={'ok': True})
    monkeypatch.setattr(node, 'execute_packet', execute)
    with pytest.raises(KeyboardInterrupt):
        node.job_worker_loop()
    assert store.get_job(stream_job['id'])['status'] == 'cancelled'
    assert store.get_job(normal_job['id'])['status'] == 'ok'
    execute.assert_called_once()
    assert execute.call_args.args[1] == normal_job['id']
    assert sup.status()['active'] is None
