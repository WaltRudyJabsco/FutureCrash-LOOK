"""Browser UI replay using an isolated collection and locally saved artwork."""
import json,sys
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'core'))
import museum_web
from playwright.sync_api import sync_playwright
OUT=ROOT/'artifacts/museum-browser';OUT.mkdir(parents=True,exist_ok=True)
fixture=ROOT/'artifacts/museum-live';rows=json.loads((fixture/'catalog.json').read_text())['items']
requests=[];errors=[];job={};collections={};offline=False
for index,row in enumerate(rows):row['available_offline']=index<2
def respond(route):
    global job,collections,offline
    request=route.request;url=urlsplit(request.url);path=url.path
    if path=='/museum':return route.fulfill(content_type='text/html',body=museum_web.PAGE)
    if path=='/browser-views.js':return route.fulfill(content_type='text/javascript',body=(ROOT/'signal-window/browser-views.js').read_text())
    if path=='/api/museum/config':return route.fulfill(json={'owner':'archive','owners':['local','archive']})
    if path=='/api/museum/image':
        ident=parse_qs(url.query)['id'][0];ident=rows[0]['id'] if ident=='met-999999999' else ident;return route.fulfill(content_type='image/jpeg',body=(fixture/'collection/images'/(ident+'.jpg')).read_bytes())
    if path in ('/api/museum','/api/museum/search'):
        if request.method=='POST':
            data=request.post_data_json;requests.append(data)
            if data['action']=='collection-create':collections['test-collection']={'name':data['name']}
            if data['action']=='collection-add':next(x for x in rows if x['id']==data['id']).setdefault('collections',[]).append(data['collection'])
            if data['action']=='collection-remove':next(x for x in rows if x['id']==data['id'])['collections'].remove(data['collection'])
            if data['action']=='favorite':
                row=next(x for x in rows if x['id']==data['id']);row['favorite']=not row.get('favorite')
            if data['action']=='mark-removal':
                row=next(x for x in rows if x['id']==data['id'])
                if row.get('removal_due'):row.pop('removal_due')
                else:row['removal_due']=2000000000
            if data['action']=='featured':job={'state':'running','kind':'featured','requested':1000,'saved':2,'counts':{'met':1,'aic':1}}
            if data['action']=='starter':job={'state':'running','requested':data['count'],'saved':2,'theme':'landscape'}
            if data['action']=='cancel':job['state']='cancelled'
        return route.fulfill(json={'ok':True,'node':'archive','items':rows,'job':job,'more':path.endswith('search'),'collections':collections,'active_collection':'test-collection','offline':offline,'offline_count':2})
    return route.fulfill(status=404,body='Not found')
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1280,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('http://test.local/**',respond);page.goto('http://test.local/museum');page.wait_for_selector('.card img')
    page.wait_for_function("[...document.querySelectorAll('.card img')].every(i=>i.complete&&i.naturalWidth>0)")
    assert page.locator('.card').count()==len(rows)
    assert page.evaluate("FabricBrowserViews.museumCommand('/museum')")
    # A finished job must not replace images or refetch no-store artwork on polls.
    job={'state':'partial','requested':1000,'saved':707,'errors':['Source unavailable']}
    page.evaluate("window.firstImage=document.querySelector('.card img');window.firstCard=document.querySelector('.card');window.gridChanges=[];new MutationObserver(events=>gridChanges.push(...events)).observe(document.querySelector('#grid'),{childList:true,subtree:true})")
    image_requests=[]
    page.on('request',lambda request:image_requests.append(request.url) if '/api/museum/image?' in request.url else None)
    for _ in range(3):page.evaluate('pollMuseum()')
    assert page.evaluate("firstImage===document.querySelector('.card img')&&firstCard===document.querySelector('.card')")
    assert page.evaluate('gridChanges.length===0')
    assert not image_requests,image_requests
    assert page.locator('#job progress').count()==0
    assert '707 of 1,000' in page.locator('#job').inner_text()
    assert 'No download is currently running' in page.locator('#job').inner_text()
    # Newly saved work is appended without replacing existing artwork.
    extra=dict(rows[0],id='met-999999999',title='New arrival')
    rows.append(extra);page.evaluate('pollMuseum()')
    assert page.locator('.card').count()==len(rows)
    assert page.evaluate("firstImage===document.querySelector('.card img')")
    rows.pop();page.evaluate('pollMuseum()')
    # A running job has a progress bar and Stop; terminal states have neither.
    job={'state':'running','requested':1000,'saved':707}
    page.evaluate('pollMuseum()');assert page.locator('#job progress').count()==1
    for state in ('cancelled','interrupted','complete','partial'):
        job['state']=state;page.evaluate('pollMuseum()')
        assert page.locator('#job progress').count()==0
        assert page.locator('#job button').count()==0
    page.screenshot(path=str(OUT/'desktop.png'),full_page=True)
    page.locator('.card .view').first.click();page.wait_for_selector('#detail:visible');assert page.locator('#title').inner_text()
    assert page.locator('#detail-actions button',has_text='Favorite').count()==1
    page.locator('#detail-full').click();page.wait_for_function('document.fullscreenElement!==null');page.locator('#detail-full').click();page.wait_for_function('document.fullscreenElement===null')
    page.locator('#detail-actions button',has_text='Thumbs down').click();page.wait_for_selector('#detail-actions button:has-text("Undo removal")')
    page.locator('#detail-actions button',has_text='Undo removal').click();page.wait_for_selector('#detail-actions button:has-text("Thumbs down")')
    page.locator('#close').click()
    page.locator('.card .actions button',has_text='Favorite').first.click();page.locator('#favorites').click();page.wait_for_function("document.querySelectorAll('.card').length===1")
    page.locator('#slideshow').click();page.wait_for_selector('#show:visible');assert '/api/museum/image' in page.locator('#slide-image').get_attribute('src')
    assert page.locator('#slide-actions button',has_text='Favorite').count()==1
    page.locator('#slide-pause').click();assert page.locator('#slide-pause').inner_text()=='Play';page.locator('#slide-next').click();page.locator('#exit').click()
    page.locator('#discover').click();page.wait_for_selector('#source:visible');page.locator('#source').select_option('aic');page.locator('#query').fill('landscape');page.locator('#search button').click();page.wait_for_selector('#next:visible')
    page.locator('#saved').click();page.wait_for_function("document.querySelectorAll('.card').length>1")
    page.once('dialog',lambda d:d.accept('Night Gallery'));page.locator('#new-collection').click();page.wait_for_function("document.querySelector('#collection-choice').options.length===1")
    page.locator('#saved').click();page.wait_for_selector('.card')
    page.once('dialog',lambda d:d.accept('1'));page.locator('.card .actions button',has_text='Add to collection').first.click()
    page.locator('#collections').click();page.wait_for_function("document.querySelectorAll('.card').length===1")
    page.locator('#shuffle').check();page.locator('#slideshow').click();page.wait_for_selector('#show:visible');page.locator('#exit').click()
    assert page.evaluate("new Set(shuffleWorks([{id:'a'},{id:'b'},{id:'c'}]).map(x=>x.id)).size===3")
    page.locator('#saved').click();page.wait_for_selector('.card')
    offline=True;page.locator('#saved').click();page.wait_for_function("document.querySelector('#status').textContent.includes('Owner offline')")
    page.locator('#offline-only').check();assert page.locator('.card').count()==2
    assert page.locator('#new-collection').is_disabled()
    page.locator('#offline-only').uncheck();offline=False;page.locator('#saved').click();page.wait_for_function("!document.querySelector('#new-collection').disabled")
    page.once('dialog',lambda d:d.accept());page.locator('#featured').click();page.wait_for_selector('#job:visible')
    assert any(x.get('action')=='featured' and x['count']==500 and x['source']=='both' for x in requests)
    page.locator('summary').click();page.locator('#count').fill('10');page.once('dialog',lambda d:d.accept());page.locator('#starter').click();page.wait_for_selector('#job:visible')
    assert any(x.get('action')=='starter' and x['count']==10 for x in requests)
    page.locator('#job button').click();page.wait_for_function("document.querySelector('#job').textContent.includes('cancelled')")
    page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(OUT/'phone.png'),full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors
    browser.close()
print('Museum browser: collection, detail, favorites, saved-only slideshow, search, starter/cancel, desktop/mobile layout passed')
