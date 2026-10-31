"""Authenticated browser gateway shared by Signal and Albert."""
import json
import urllib.parse
import urllib.request
import urllib.error

PAGE='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LOOK Books</title>
<style>body{background:#f5f0e5;color:#233342;font:18px/1.6 Georgia,serif;max-width:850px;margin:auto;padding:20px}button,select,input{font:16px system-ui;padding:10px;margin:4px;border:1px solid #aaa;border-radius:7px;background:#fff;color:#233342}button{cursor:pointer}#items button{display:block;text-align:left;width:100%}#items button:nth-child(even){background:#ece8df}audio{width:100%}#cover{float:right;max-width:130px;max-height:190px;margin:10px}#passage{white-space:pre-wrap}#status{color:#8c452b;min-height:2em}nav{display:flex;flex-wrap:wrap}#reader{border-top:1px solid #b8b1a5;margin-top:20px}button:focus-visible{outline:3px solid #b38a13}small{color:#566473}</style>
<main id="books-app"><h1>Books</h1><nav><button id="shelf">My shelf</button><button id="continue">Continue reading</button><button data-mode="popular">Popular</button><button data-mode="new">New arrivals</button><button data-mode="subjects">Subjects</button><button data-mode="surprise">Surprise me</button></nav><form id="search"><input id="query" aria-label="Search your shelf" placeholder="Find a book on your shelf"><button>Search shelf</button></form><p id="status" role="status"></p><div id="items"></div><section id="reader" hidden><img id="cover" alt="Book cover" hidden><h2 id="title"></h2><p id="where"></p><select id="chapters" aria-label="Chapter"></select><nav><button id="previous">Previous paragraph</button><button id="next">Next paragraph</button><button id="retry">Retry narration</button></nav><audio id="audio" controls preload="none"></audio><p><small>Press Play to listen on this device. Progress is saved to the book owner; another device can continue there.</small></p><p id="passage"></p></section></main><script src="/browser-views.js"></script></html>'''


def handle(handler,node_url,payload=None):
    """Caller has checked lo.use; never accept an arbitrary proxy destination."""
    parsed=urllib.parse.urlsplit(handler.path)
    action=parsed.path.removeprefix('/api/books').strip('/')
    query=urllib.parse.parse_qs(parsed.query)
    allowed={'target','id','chapter','paragraph','mode','subject'}
    query={k:v[0] for k,v in query.items() if k in allowed}
    route={'':'/v1/books/fabric','read':'/v1/books/read','audio':'/v1/books/audio','cover':'/v1/books/cover','discover':'/v1/books/discover','discovery-cover':'/v1/books/discovery-cover'}.get(action)
    if payload is not None:
        if action not in {'progress','fetch'}:raise ValueError('Unknown Books action')
        route='/v1/books'
        payload=dict(payload,action=action)
    if route is None:raise ValueError('Unknown Books route')
    headers={'Content-Type':'application/json'}
    if handler.headers.get('Range'):headers['Range']=handler.headers['Range']
    url=node_url+route+('?' + urllib.parse.urlencode(query) if query else '')
    request=urllib.request.Request(url,data=json.dumps(payload).encode() if payload is not None else None,headers=headers)
    try:
        with urllib.request.urlopen(request,timeout=185 if action=='audio' else 60) as response:
            handler.send_response(response.status)
            for key in ('Content-Type','Content-Length','Content-Range','Accept-Ranges'):
                if response.headers.get(key):handler.send_header(key,response.headers[key])
            handler.send_header('Cache-Control','private, no-store');handler.end_headers()
            while block:=response.read(65536):handler.wfile.write(block)
    except urllib.error.HTTPError as exc:
        body=exc.read(65536)
        handler.send_response(exc.code);handler.send_header('Content-Type','application/json');handler.send_header('Content-Length',str(len(body)));handler.end_headers();handler.wfile.write(body)
