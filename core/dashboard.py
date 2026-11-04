"""Bounded read-only telemetry for the browser observatory; no event payloads."""
import concurrent.futures
import threading
import time

CACHE_SECONDS = 8
PEER_TIMEOUT = 2
MAX_PEERS = 16
MAX_EVENTS = 80
_LOCK = threading.Lock()
_CACHE = {}


def local_snapshot(ad, services, events):
    models = ad.get('inference', {}).get('models', [])
    active = ad.get('supervisor', {}).get('active') or {}
    return {
        'name': ad.get('identity', {}).get('name', 'This host'),
        'platform': ad.get('platform', {}).get('system', 'unknown'),
        'architecture': ad.get('platform', {}).get('architecture', ''),
        'version': ad.get('version', ''), 'observed_at': time.time(),
        'runtime_ok': ad.get('runtime', {}).get('ok'),
        'models': [{'name': m.get('name'), 'resident': bool(m.get('resident'))} for m in models],
        'activity': {'phase': active.get('phase', 'idle'), 'started': active.get('started')},
        'services': {k: {'state': v.get('state', 'unknown')} for k, v in services.items()},
        'release': {k: ad.get('maintenance', {}).get(k) for k in ('commit', 'state')},
        'backup_configured': bool(ad.get('backup', {}).get('destination')),
        # Details can contain prompts, filenames or tool output. Only operational
        # event labels cross into the dashboard, which people use for demos.
        'events': [{k: e.get(k) for k in ('seq', 'ts', 'type', 'phase')} for e in events[-MAX_EVENTS:]],
    }


def snapshot(local, peers, peer_base, fetch):
    """One shared cache bounds fan-out even with several open browser tabs."""
    with _LOCK:
        if _CACHE and time.monotonic() - _CACHE['at'] < CACHE_SECONDS:
            return _CACHE['value']
        own = local()
        own['reachable'] = True
        own['local'] = True
        targets = [p for p in peers if p.get('trusted') and peer_base(p)][:MAX_PEERS]

        def read(peer):
            name = peer.get('name', 'Peer')
            try:
                row = fetch(peer_base(peer) + '/v1/dashboard/local', timeout=PEER_TIMEOUT)
                if not isinstance(row, dict) or not isinstance(row.get('services'), dict):
                    raise ValueError('unsupported telemetry')
                return dict(row, name=name, reachable=True, local=False)
            except Exception:
                # An old node or transport failure is unknown, never a healthy idle node.
                return {'name': name, 'reachable': False, 'local': False,
                        'observed_at': peer.get('node_seen_at'), 'events': []}

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            nodes = [own, *pool.map(read, targets)]
        events = []
        for row in nodes:
            for event in row.pop('events', []):
                events.append(dict(event, source=row['name'], id=f"{row['name']}:{event.get('seq')}"))
        events.sort(key=lambda e: float(e.get('ts') or 0))
        value = {'observed_at': time.time(), 'host': own['name'], 'nodes': nodes,
                 'events': events[-MAX_EVENTS:], 'refresh_seconds': CACHE_SECONDS,
                 'omitted_peers': max(0, sum(bool(p.get('trusted') and peer_base(p)) for p in peers) - MAX_PEERS)}
        _CACHE.update(at=time.monotonic(), value=value)
        return value
