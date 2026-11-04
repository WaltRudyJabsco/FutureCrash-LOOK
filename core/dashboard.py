"""Bounded read-only telemetry for the browser observatory; no event payloads."""
import concurrent.futures
import threading
import time
from urllib.error import HTTPError

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



def peer_snapshot(peer, base, fetch):
    """A responding old endpoint is reachable; a timeout alone cannot prove offline."""
    name = peer.get('name', 'Peer')
    partial = {'name': name, 'local': False, 'events': [],
               'observed_at': peer.get('node_seen_at')}
    try:
        row = fetch(base + '/v1/dashboard/local', timeout=PEER_TIMEOUT)
        if not isinstance(row, dict) or not isinstance(row.get('services'), dict):
            return dict(partial, reachable=True, telemetry_status='telemetry_error')
        return dict(row, name=name, reachable=True, local=False, telemetry_status='ready')
    except HTTPError as error:
        status = ('update_required' if error.code in (404, 501) else
                  'authorization_required' if error.code in (401, 403) else 'telemetry_error')
        return dict(partial, reachable=True, telemetry_status=status)
    except Exception:
        # Separate a broken/slow telemetry handler from a machine we cannot contact.
        try:
            health = fetch(base + '/v1/health', timeout=PEER_TIMEOUT)
            if not isinstance(health, dict):
                raise ValueError('invalid health response')
            return dict(partial, reachable=True, telemetry_status='telemetry_error')
        except HTTPError:
            return dict(partial, reachable=True, telemetry_status='telemetry_error')
        except Exception:
            return dict(partial, reachable=False, telemetry_status='unreachable')


def snapshot(local, peers, peer_base, fetch):
    """One shared cache bounds fan-out even with several open browser tabs."""
    with _LOCK:
        if _CACHE and time.monotonic() - _CACHE['at'] < CACHE_SECONDS:
            return _CACHE['value']
        own = local()
        own['reachable'] = True
        own['local'] = True
        own['telemetry_status'] = 'ready'
        targets = [p for p in peers if p.get('trusted') and peer_base(p)][:MAX_PEERS]

        def read(peer):
            return peer_snapshot(peer, peer_base(peer), fetch)

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
