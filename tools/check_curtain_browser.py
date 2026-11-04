"""Optional isolated browser smoke check; requires Playwright and Google Chrome."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
repo=Path(__file__).resolve().parents[1]
script=(repo/'signal-window/browser-views.js').read_text()
out=repo/'artifacts/curtain';out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1280,'height':800})
    state={'ok':True,'configured':True,'locked':False,'captions':['QUIET WATCH / DISTANT SIGNAL']}
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    def route(request):
        if request.request.url.endswith('/api/curtain'):
            payload=request.request.post_data_json if request.request.method=='POST' else None
            if payload:
                if payload['action']=='lock':state['locked']=True
                elif payload.get('pin')!='1234':return request.fulfill(status=400,json={'error':'Incorrect PIN'})
                else:state['locked']=False
            return request.fulfill(json=state)
        request.fulfill(content_type='text/html',body='<html><head><meta charset="utf-8"></head><body><textarea aria-label="chat"></textarea><script>'+script+'</script></body></html>')
    page.route('http://curtain.test/**',route)
    page.goto('http://curtain.test/')
    page.get_by_role('button',name='Lock Fabric',exact=True).click()
    page.wait_for_function("document.querySelector('#lk-curtain').style.display==='block'")
    field=page.get_by_label('Four-digit PIN',exact=True)
    field.fill('9999');page.get_by_role('button',name='Unlock',exact=True).click()
    page.get_by_role('status').filter(has_text='Incorrect PIN').wait_for()
    assert field.input_value()==''
    page.screenshot(path=str(out/'browser-desktop.png'))
    page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(100)
    page.screenshot(path=str(out/'browser-phone.png'))
    field.fill('1234');page.get_by_role('button',name='Unlock',exact=True).click()
    page.wait_for_function("document.querySelector('#lk-curtain').style.display==='none'")
    page.get_by_label('chat').fill('lk lk');page.get_by_label('chat').press('Enter')
    page.wait_for_function("document.querySelector('#lk-curtain').style.display==='block'")
    state['locked']=False
    page.wait_for_function("document.querySelector('#lk-curtain').style.display==='none'")
    assert not errors,errors
    print('Browser checks passed: wrong PIN, masking/clearing, unlock, shortcut, remote unlock, desktop/mobile rendering')
    browser.close()
