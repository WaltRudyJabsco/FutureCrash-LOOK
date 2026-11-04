"""Exercise the real dashboard assets with an isolated telemetry fixture."""
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts/dashboard'
OUT.mkdir(parents=True, exist_ok=True)
fixture = OUT / 'snapshot.json'
DATA = json.loads(fixture.read_text()) if fixture.exists() else {
    'host': 'Studio', 'observed_at': time.time(), 'nodes': [
        {'name': 'Studio', 'local': True, 'reachable': True, 'platform': 'darwin',
         'services': {'signal': {'state': 'running'}}, 'models': [{'name': 'Local model', 'resident': True}],
         'activity': {'phase': 'idle'}}],
    'events': [{'id': 'studio:1', 'source': 'Studio', 'type': 'result', 'phase': 'ok', 'ts': time.time()}]}

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1050}, reduced_motion='reduce')
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    state = {'fail': False, 'requests': 0}

    def route(request):
        path = request.request.url.split('18777', 1)[-1]
        if path == '/api/fabric/dashboard':
            state['requests'] += 1
            return request.fulfill(status=503, json={'error': 'offline'}) if state['fail'] else request.fulfill(json=DATA)
        if path == '/api/fabric/care':
            return request.fulfill(json={'nodes': [], 'releases_match': False})
        file = ROOT / 'signal-window' / path.lstrip('/')
        request.fulfill(body=file.read_text(), content_type='text/javascript' if file.suffix == '.js' else 'text/html')

    page.route('http://localhost:18777/**', route)
    page.goto('http://localhost:18777/fabric.html')
    page.wait_for_function("document.querySelectorAll('.node-card').length>0")
    assert not errors, errors
    page.screenshot(path=str(OUT / 'desktop.png'), full_page=True)
    source = DATA['nodes'][0]['name']
    page.locator('#filter').select_option(source)
    assert all(name == source for name in page.locator('#events strong').all_text_contents())
    page.locator('#filter').select_option('')
    page.get_by_role('button', name='Pause live').click()
    count = state['requests']
    page.get_by_role('button', name='Refresh now').click()
    page.wait_for_timeout(100)
    assert state['requests'] == count
    page.get_by_role('button', name='Resume live').click()
    page.get_by_role('button', name='Full screen', exact=True).click()
    page.wait_for_function('!!document.fullscreenElement')
    page.get_by_role('button', name='Exit full screen').click()
    page.set_viewport_size({'width': 390, 'height': 844})
    page.screenshot(path=str(OUT / 'phone.png'), full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal overflow'
    # Remote names are text, even when they look like markup.
    DATA['nodes'].append({'name': '<img src=x onerror=alert(1)>', 'reachable': False})
    page.get_by_role('button', name='Refresh now').click()
    page.get_by_text('Telemetry unavailable.', exact=False).wait_for()
    assert page.locator('#nodes img').count() == 0
    state['fail'] = True
    page.wait_for_timeout(100)
    page.get_by_role('button', name='Refresh now').click()
    page.get_by_text('Host returned 503', exact=False).wait_for()
    assert page.locator('.node-card').count() > 0, 'Failed refresh lost last snapshot'
    assert not errors, errors
    print('Dashboard: desktop/phone, fullscreen, pause, offline state, and safe text checks passed')
    browser.close()
