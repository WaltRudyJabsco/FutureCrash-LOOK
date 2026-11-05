"""Manual browser regression: run with Playwright and installed Chrome; uses mock data only."""
import sys,json,time
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[2]
import os
os.chdir(ROOT)
sys.path[:0]=[str(ROOT/'core'),str(ROOT/'look')]
import book_web
from playwright.sync_api import sync_playwright
rows=[{'id':'a','title':'Persuasion','author':'Jane Austen','node':'3090','starter_managed':True,'collections':[]},{'id':'b','title':'My own manuscript','author':'Local author','node':'3090','collections':[]},{'id':'c','title':'A book to reconsider','author':'An author','node':'3090','starter_managed':True,'collections':[],'removal_due':time.time()+172800}]
collections=[];calls=[]
def route(r):
 path=urlsplit(r.request.url).path
 if path=='/reader':return r.fulfill(body=book_web.PAGE,content_type='text/html')
 if path=='/browser-views.js':return r.fulfill(body=Path('signal-window/browser-views.js').read_text(),content_type='application/javascript')
 if path=='/api/books':return r.fulfill(json={'entries':rows,'collections':collections})
 if path=='/api/books/voices':return r.fulfill(json={'voices':[]})
 if path=='/api/books/read':return r.fulfill(json={'chapter':0,'paragraph':0,'chapters':[{'title':'Chapter 1','paragraphs':1}],'text':'A book to read.','reading':{},'content':{'paragraphs':['A book to read.'],'images':[],'start':0}})
 if r.request.method=='POST':
  d=r.request.post_data_json;calls.append((path,d));row=next((x for x in rows if x['id']==d.get('id')),None)
  if path.endswith('/collection'):collections.append(d['name'])
  if path.endswith('/collect'):
   if d.get('selected',True):row['collections'].append(d['name'])
   else:row['collections'].remove(d['name'])
  if path.endswith('/favorite'):row['favorite']=d['selected']
  if path.endswith('/reject'):row['removal_due']=time.time()+172800
  if path.endswith('/restore'):row.pop('removal_due',None)
  return r.fulfill(json={'ok':True})
 return r.fulfill(status=404,body='')
with sync_playwright() as p:
 browser=p.chromium.launch(channel="chrome",headless=True);page=browser.new_page(viewport={'width':1200,'height':950});page.route('**/*',route)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('https://reader.test/reader');page.wait_for_selector('.book-card')
 assert page.locator('.book-card').count()==2
 assert page.get_by_role('button',name='Thumbs down',exact=True).count()==1 # manual imports have no discard control
 card=page.locator('.book-card').filter(has_text='Persuasion')
 card.get_by_role('button',name='Add to Favorites',exact=True).click()
 page.wait_for_function("document.querySelectorAll('.book-card').length===1")
 page.locator('#collection-filter').select_option('favorites')
 assert page.locator('.book-card').count()==1
 page.locator('.book-card').get_by_role('button',name='Remove from Favorites',exact=True).click()
 page.wait_for_function("document.querySelectorAll('.book-card').length===0")
 page.locator('#collection-filter').select_option('pool')
 page.once('dialog',lambda d:d.accept('Weekend'));page.locator('#collection-new').click()
 page.wait_for_function("document.querySelector('#collection-filter').value==='c:Weekend'")
 page.locator('#collection-filter').select_option('all');page.locator('.book-card').filter(has_text='Persuasion').locator('summary').click()
 page.get_by_label('Weekend',exact=True).check();page.wait_for_function("Array.from(document.querySelectorAll('.book-card summary')).some(x=>x.textContent.includes('Weekend'))")
 page.locator('#collection-filter').select_option('c:Weekend');assert page.locator('.book-card').count()==1
 page.once('dialog',lambda d:d.accept());page.locator('.book-card').get_by_role('button',name='Thumbs down',exact=True).click()
 page.wait_for_function("document.querySelectorAll('.book-card').length===0")
 page.locator('#collection-filter').select_option('rejected');assert page.locator('.book-card').count()==2
 page.locator('.book-card').first.get_by_role('button',name='Undo removal').click();page.wait_for_function("document.querySelectorAll('.book-card').length===1")
 page.locator('#collection-filter').select_option('all')
 out=Path('artifacts/reader-curation');out.mkdir(parents=True,exist_ok=True)
 page.screenshot(path=str(out/'desktop.png'),full_page=True)
 page.set_viewport_size({'width':820,'height':1180});page.screenshot(path=str(out/'ipad.png'),full_page=True)
 page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'phone.png'),full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 page.locator('.book-card').filter(has_text='A book to reconsider').locator('button').first.click()
 page.wait_for_selector('.reading-paragraph')
 assert not page.locator('#book-collect').is_visible()
 page.locator('#controls-toggle').click()
 assert page.locator('#book-collect').is_visible() and page.locator('#book-reject').is_visible()
 page.locator('#controls-close').click()
 page.screenshot(path=str(out/'phone-reader.png'))
 assert not errors,errors
 assert any(x[0].endswith('/reject') for x in calls) and any(x[0].endswith('/restore') for x in calls)
 print('Browser create/filter/assign/reject/undo and mobile overflow checks passed')
 browser.close()
