"""Isolated Signal/Albert playback UI checks; requires Playwright and Chrome."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/browser-movies';OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    for surface in ('signal-window','albert'):
        page=browser.new_page(viewport={'width':1280,'height':900});errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        def route(request):
            from urllib.parse import urlparse
            path=urlparse(request.request.url).path
            if path.startswith('/api/') or path.startswith('/v1/'):
                data={'authorized':True,'endpoint':{'scopes':['lo.use','signal.view']},'actions':[],'entries':[],'outputs':[],'decisions':[],'configured':False,'locked':False,'ok':True}
                return request.fulfill(json=data)
            name=path.lstrip('/') or 'index.html';file=ROOT/surface/name
            if name=='browser-views.js':file=ROOT/'signal-window'/name
            if not file.is_file():return request.fulfill(status=404,body='')
            mime='text/html' if name.endswith('.html') else 'text/javascript' if name.endswith('.js') else 'text/css'
            request.fulfill(content_type=mime,body=file.read_text())
        page.route('http://localhost:18777/**',route);page.goto('http://localhost:18777/');page.wait_for_timeout(200)
        assert not errors,errors
        if surface=='signal-window':
            result=page.evaluate('''async()=>{
              browserMedia={active:true,state:'playing',sourceNode:'test',index:0,queue:[{id:'movie',title:'Test Movie',path:'/movies/test.mp4',media_type:'video/mp4'}]};
              const state={...browserSnapshot(),position:10,duration:100};renderMedia(state,true);
              const head=mediaPanel.querySelector('.media-head'),video=browserVideo,button=mediaPanel.querySelector('[data-media-fullscreen]');
              for(let i=0;i<20;i++)renderMedia({...state,position:10+i});
              if(head!==mediaPanel.querySelector('.media-head')||button!==mediaPanel.querySelector('[data-media-fullscreen]'))throw Error('Playback ticks rebuilt controls');
              if(video!==mediaPanel.querySelector('video'))throw Error('Video replaced');
              return true;
            }''')
            assert result
            page.get_by_role('button',name='Full screen',exact=True).click()
            page.wait_for_function("mediaPanel.classList.contains('media-fullscreen')")
            page.get_by_role('button',name='Exit full screen',exact=True).click()
            page.wait_for_function("!mediaPanel.classList.contains('media-fullscreen')")
            page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(OUT/'signal-phone.png'))
            page.evaluate('''async()=>{
              HTMLMediaElement.prototype.play=async()=>{};HTMLMediaElement.prototype.load=()=>{};
              let release;browserMediaUrl=async(entry)=>entry.id==='old'?new Promise(resolve=>release=()=>resolve('http://localhost:18777/old.mp4')):'http://localhost:18777/new.mp4';
              browserMedia.queue=[{id:'old',path:'/old.mp4'},{id:'new',path:'/new.mp4'}];
              const old=browserPlayIndex(0);await Promise.resolve();await browserPlayIndex(1);release();
              if(await old!==false||!browserVideo.src.endsWith('/new.mp4'))throw Error('Stale ticket replaced new video');
            }''')
        else:
            page.evaluate("addFold({type:'video',title:'Test Movie',src:'http://localhost:18777/test.mp4',note:'Playback controls preview'})")
            button=page.get_by_role('button',name='Full screen',exact=True);button.wait_for()
            assert button.bounding_box()['height']>=44
            button.click();page.wait_for_function("!!document.querySelector('.media-fullscreen')")
            page.get_by_role('button',name='Exit full screen',exact=True).click()
            page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(OUT/'albert-phone.png'))
        assert not errors,errors
        print(surface,'UI checks passed');page.close()
    browser.close()
