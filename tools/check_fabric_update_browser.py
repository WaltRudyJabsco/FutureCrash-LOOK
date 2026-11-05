"""Offline browser replay of the reviewed Fabric update panel."""
import json,time
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/fabric-update';OUT.mkdir(parents=True,exist_ok=True)
requests=[];started=False
plan={'review':'a'*32,'source':{'kind':'node','node':'archive','commit':'a'*40},'github':{'state':'checked'},'scope':'Runtime, configured library sync and verified backups','nodes':[{'node':'desk','release':{'commit':'b'*40}},{'node':'archive','release':{'commit':'a'*40}}]}
def route(r):
 global started
 url=urlsplit(r.request.url)
 if url.path in {'/fabric.html','/fabric-dashboard.js'}:return r.fulfill(body=(ROOT/'signal-window'/url.path[1:]).read_text(),content_type='text/html' if url.path.endswith('html') else 'text/javascript')
 if url.path=='/api/fabric/dashboard':return r.fulfill(json={'observed_at':time.time(),'host':'desk','nodes':[],'events':[]})
 if url.path=='/api/fabric/care':return r.fulfill(json={'releases_match':False,'nodes':[]})
 if url.path=='/api/fabric/update':
  if r.request.method=='POST':
   requests.append(r.request.post_data_json);started=True
   return r.fulfill(json={'state':'queued','id':'job','steps':[]})
  if 'plan=1' in url.query:return r.fulfill(json=plan)
  return r.fulfill(json={'state':'complete' if started else 'idle','steps':[{'label':'desk libraries and backups','state':'verified'}] if started else []})
 return r.fulfill(status=404,body='')
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True);page=browser.new_page(viewport={'width':1280,'height':1000});page.route('**/*',route)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('https://fabric.test/fabric.html?update=1');page.wait_for_function("!document.querySelector('#updateRun').disabled")
 assert 'Plan: archive' in page.locator('#updateReceipt').inner_text()
 page.wait_for_timeout(5200);assert 'Plan: archive' in page.locator('#updateReceipt').inner_text()
 page.locator('#updateReceipt').scroll_into_view_if_needed();page.screenshot(path=str(OUT/'plan.png'))
 page.once('dialog',lambda d:d.accept());page.locator('#updateRun').click()
 page.wait_for_function("document.querySelector('#updateReceipt').textContent.includes('complete')")
 assert requests==[{'confirm':True,'review':'a'*32}]
 page.set_viewport_size({'width':390,'height':844});page.locator('#updateReceipt').scroll_into_view_if_needed();page.screenshot(path=str(OUT/'phone.png'))
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 assert not errors,errors
 browser.close()
print('Reviewed plan, pinned submission, receipt polling and mobile layout passed')
