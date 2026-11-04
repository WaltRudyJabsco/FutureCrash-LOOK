"""Exercise browser playback/bookmarks against an isolated, range-capable fixture."""
import io,json,re,sys,wave
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
import radio_web
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/ytr-browser';OUT.mkdir(parents=True,exist_ok=True)
audio=io.BytesIO()
with wave.open(audio,'wb') as output:
    output.setparams((1,2,8000,0,'NONE','not compressed'));output.writeframes(b'\0\0'*8000*90)
blob=audio.getvalue()
rows=[{'id':'a'*32,'title':'A conversation worth keeping','url':'https://youtu.be/abcdefghijk','stage':'complete','duration':90,'position':12,'bookmark_revision':0,'done':False},
      {'id':'b'*32,'title':'The quiet science of deep space','url':'https://youtu.be/12345678901','stage':'complete','duration':90,'position':0,'bookmark_revision':0,'done':False}]
requests=[];errors=[]
def respond(route):
    request=route.request;path=request.url.split('test.local',1)[-1]
    if path=='/ytr':return route.fulfill(content_type='text/html',body=radio_web.PAGE)
    if path=='/browser-views.js':return route.fulfill(content_type='text/javascript',body=(ROOT/'signal-window/browser-views.js').read_text())
    if path.startswith('/api/ytr/config'):return route.fulfill(json={'owner':'studio','owners':['local','studio']})
    if path.startswith('/api/ytr/audio'):
        bounds=re.match(r'bytes=(\d+)-(\d*)',request.headers.get('range',''))
        start=int(bounds[1]) if bounds else 0;end=int(bounds[2]) if bounds and bounds[2] else len(blob)-1
        headers={'Accept-Ranges':'bytes'}
        if bounds:headers['Content-Range']=f'bytes {start}-{end}/{len(blob)}'
        return route.fulfill(status=206 if bounds else 200,content_type='audio/wav',headers=headers,body=blob[start:end+1])
    if path.startswith('/api/ytr?'):
        if request.method=='POST':
            data=request.post_data_json;requests.append(data)
            row=next((x for x in rows if x['id']==data.get('id')),None)
            if data['action']=='progress':
                if data['bookmark_revision']!=row['bookmark_revision']:return route.fulfill(status=400,json={'ok':False,'error':'Bookmark changed on another device'})
                row.update(position=data['position'],done=data['done'],bookmark_revision=row['bookmark_revision']+1)
            elif data['action']=='move':
                i=rows.index(row);rows.pop(i);rows.insert(max(0,min(len(rows),i+data['delta'])),row)
            elif data['action']=='add':rows.append(dict(rows[0],id='c'*32,title='Added episode',url=data['url']))
            elif data['action']=='remove':rows.remove(row)
        return route.fulfill(json={'ok':True,'node':'studio','items':rows})
    return route.fulfill(status=404,body='Not found')
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1000,'height':850})
    page.on('pageerror',lambda err:errors.append(str(err)));page.route('http://test.local/**',respond)
    page.goto('http://test.local/ytr');page.wait_for_selector('#queue li')
    assert page.locator('#owner').input_value()=='studio'
    assert page.evaluate("FabricBrowserViews.radioCommand('/ytr').url")==''
    assert page.evaluate("FabricBrowserViews.radioCommand('/ytr https://youtu.be/abcdefghijk').url").endswith('abcdefghijk')
    assert page.evaluate("FabricBrowserViews.radioCommand('hello')") is None
    page.evaluate("audio.muted=true")
    page.locator('#queue button',has_text=re.compile('^Play$')).first.click()
    page.wait_for_function('!audio.paused && audio.currentTime>=12')
    assert '1:30' in page.locator('#position').inner_text()
    page.evaluate('audio.currentTime=35')
    page.wait_for_function('audio.currentTime>=35')
    page.locator('#play').click();page.wait_for_function('saving===null')
    assert 35<=rows[0]['position']<38
    page.screenshot(path=str(OUT/'desktop.png'),full_page=True)
    page.reload();page.wait_for_selector('#queue li');page.evaluate('audio.muted=true')
    page.locator('#queue button',has_text=re.compile('^Play$')).first.click()
    page.wait_for_function('!loading && audio.currentTime>=35')
    page.evaluate('audio.pause()');page.wait_for_function('saving===null')
    # A competing endpoint advances the bookmark; the browser must not overwrite it.
    rows[0]['bookmark_revision']+=1;rows[0]['position']=50
    page.evaluate('audio.currentTime=40')
    page.evaluate('save()');page.wait_for_selector('#conflict:visible')
    assert rows[0]['position']==50
    page.locator('#remote').click();page.wait_for_function('!loading && audio.currentTime>=50')
    page.locator('#play').click();page.wait_for_function('saving===null')
    page.locator('#next').click();page.wait_for_function("current.id==='"+'b'*32+"' && !loading")
    page.locator('#play').click();page.wait_for_function('saving===null')
    page.locator('#url').fill('https://youtu.be/zzzzzzzzzzz');page.locator('#add-form button').click();page.wait_for_function('items.length===3')
    page.locator('#queue li').last.locator('button',has_text='↑').click();page.wait_for_function("items[1].id==='"+'c'*32+"'")
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(OUT/'phone.png'),full_page=True)
    assert not errors,errors
    browser.close()
print('Browser: shared queue, audio/resume/seek, bookmarks/conflict, next, add/reorder, slash parser, desktop/mobile layout passed')
