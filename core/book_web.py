"""Authenticated browser gateway shared by Signal and Albert."""
import json
import urllib.parse
import urllib.request
import urllib.error

PAGE='''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mercury Reader</title>
<style>
:root{color-scheme:light;--paper:#f5f0e5;--panel:#ece8df;--ink:#233342;--muted:#566473;--line:#b8b1a5;--button:#fff;--accent:#315c80;--highlight:#e5dcc1;--reading-size:21px}

:root[data-theme=dark]{color-scheme:dark;--paper:#191d21;--panel:#22282e;--ink:#e6e0d3;--muted:#a8b2bc;--line:#46515b;--button:#292f36;--accent:#a9cce9;--highlight:#303d48}

*{box-sizing:border-box}
body{background:var(--paper);color:var(--ink);font:18px/1.6 Georgia,serif;max-width:900px;margin:auto;padding:20px}
button,select,input{font:15px system-ui;padding:9px 12px;margin:3px 0;border:1px solid var(--line);border-radius:7px;background:var(--button);color:var(--ink)}
button{cursor:pointer}
button:disabled{opacity:.5;cursor:default}
button:focus-visible,select:focus-visible,input:focus-visible,[tabindex]:focus-visible{outline:3px solid var(--accent);outline-offset:3px}
button[aria-pressed=true]{background:var(--highlight);border-color:var(--accent)}
nav,.preferences,.masthead{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.masthead{justify-content:space-between;margin-bottom:12px}
.masthead h1{font-size:25px;margin:0}
.brand{font-family:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;font-weight:700;letter-spacing:.04em}.brand em{font-style:normal;color:#795716}:root[data-theme=dark] .brand em{color:#d6b36a}
.preferences{font:14px system-ui;color:var(--muted)}
#font-size{min-width:3ch;text-align:center}
#search{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0}
.shelf-tools{font:14px system-ui;display:flex;gap:10px;align-items:center;flex-wrap:wrap}#library [hidden]{display:none}#items button.owned{opacity:.65}.book-thumb{display:inline-flex;width:45px;height:65px;flex:none;align-items:center;justify-content:center;margin-right:12px;vertical-align:middle;background:var(--panel);border:1px solid var(--line);border-radius:3px;font:12px Georgia,serif;color:var(--muted)}.book-thumb img{width:100%;height:100%;object-fit:contain}#items small{display:block;font:13px system-ui;color:var(--muted);margin-top:5px}
#query{flex:1 1 240px;min-width:0}
#status{font:14px/1.5 system-ui;color:var(--muted);min-height:1.5em;margin:8px 0 14px}
#items button{display:block;text-align:left;width:100%;padding:16px 18px;border-left:8px solid #9caaad;margin:8px 0}
#items button:nth-child(even){background:var(--panel);border-left-color:#b9a786}
#items button:nth-child(3n){border-left-color:#9aaca0}
#items button:nth-child(5n){border-left-color:#b49a94}
#reader[hidden],#library[hidden],#cover[hidden]{display:none}
#reader-head{position:sticky;top:0;z-index:2;background:var(--paper);border-bottom:1px solid var(--line);padding:8px 0 12px}
.book-heading{display:flex;gap:14px;align-items:center;margin:10px 0}
#cover{width:48px;max-height:70px;object-fit:contain}
#title{font-size:23px;line-height:1.25;margin:0 0 4px}
#where{font:13px system-ui;color:var(--muted);margin:0}
#chapters{max-width:100%;min-width:140px;flex:1}
.narration-options{font:13px system-ui;color:var(--muted);gap:8px;margin-top:5px}.narration-options select{flex:1;min-width:150px;max-width:320px;font-size:13px;padding:6px}.narration-options input{padding:0;min-width:80px;width:110px;accent-color:var(--accent)}#speech-speed-value{min-width:3.5ch}
audio{display:block;width:100%;height:42px;margin-top:8px}
.reader-note{font:12px system-ui;color:var(--muted);margin:6px 0 0}
#reading-body{min-height:120px;flex:1;overflow:auto;overscroll-behavior:contain;scrollbar-gutter:stable;scroll-padding:35% 0;border-bottom:1px solid var(--line)}
#passage{max-width:65ch;margin:0 auto;padding:40px 22px 45vh;font-size:var(--reading-size);line-height:1.85}
.reading-paragraph{white-space:pre-wrap;margin:0 -14px 1.1em;padding:8px 14px;border-left:3px solid transparent;border-radius:3px;cursor:pointer}
.reading-paragraph:hover{border-left-color:var(--line)}
.reading-paragraph[aria-current=true]{background:var(--highlight);border-left-color:var(--accent)}
figure{margin:26px 0;text-align:center}
figure img{display:block;max-width:100%;max-height:65vh;object-fit:contain;margin:auto}
figcaption{font:14px/1.5 system-ui;color:var(--muted);margin-top:10px}
.reading{height:calc(100dvh - 40px);display:flex;flex-direction:column}
.reading #reader{display:flex;flex-direction:column;min-height:0;flex:1}
.reading #reader-head{flex:none}
.reading #status{flex:none}
.reading .masthead{margin-bottom:0}
.reading .masthead h1{font-size:18px}
.reading #status{margin:6px 0}
#library-back{font-size:13px;padding:5px 10px}
.reading-label{font:12px system-ui;color:var(--muted);margin-left:auto}
@media(max-width:600px){body{padding:12px}
.preferences{gap:6px}
.preferences button{padding:6px 10px}
#title{font-size:20px}
#passage{padding:25px 15px 45vh}
.reading{height:calc(100dvh - 24px)}
#reader-head nav{gap:5px}
#reader-head nav button{font-size:13px;padding:8px}
#chapters{width:100%;flex-basis:100%}
}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}
}

</style>
</head>
<body>
<main id="books-app">
<header class="masthead">
<h1 class="brand" aria-label="Mercury Reader"><em>MERCURY</em> / READER</h1>
<div class="preferences" aria-label="Reading appearance">
<button id="theme" aria-pressed="false">Dark theme</button>
<button id="font-smaller" aria-label="Smaller book text">A−</button>
<output id="font-size" aria-live="polite">21</output>
<button id="font-larger" aria-label="Larger book text">A+</button>
</div>
</header>
<section id="reader" hidden aria-label="Book reader">
<div id="reader-head">
<nav>
<button id="library-back">← Library</button>
<span class="reading-label">MERCURY / READING ROOM</span>
</nav>
<div class="book-heading">
<img id="cover" alt="Book cover" hidden>
<div>
<h2 id="title">
</h2>
<p id="where" aria-live="polite">
</p>
</div>
</div>
<nav>
<select id="chapters" aria-label="Chapter">
</select>
<button id="previous">Previous paragraph</button>
<button id="next">Next paragraph</button>
<button id="follow" aria-pressed="true">Follow reading</button>
<button id="retry">Retry narration</button>
</nav>
<audio id="audio" controls preload="none">
</audio>
<nav class="narration-options" aria-label="Narration settings">
<label for="voice">Voice</label><select id="voice" aria-label="Narration voice" title="Changing voice restarts the current paragraph"><option value="">Default voice</option></select>
<label for="pauses">Pauses</label><select id="pauses" aria-label="Punctuation pauses" title="Changing pauses restarts the current paragraph"><option value="voice">Voice default</option><option value="natural" selected>More space</option><option value="relaxed">Unhurried</option></select>
<label for="speech-speed">Speed</label><input id="speech-speed" aria-label="Speech speed" type="range" min="0.5" max="2" step="0.05" value="1"><output id="speech-speed-value" for="speech-speed">1×</output>
</nav>
<p class="reader-note">Listen here, or read at your own pace. Select a paragraph to read from there.</p>
</div>
<div id="reading-body" tabindex="0" aria-label="Chapter text">
<article id="passage" aria-label="Book text">
</article>
</div>
</section>
<p id="status" role="status">
</p>
<section id="library" aria-label="Book library">
<nav>
<button id="shelf">My shelf</button>
<button id="continue">Continue reading</button>
<button id="discover">Discover Gutenberg</button>
<button data-mode="popular">Popular</button>
<button data-mode="new">New arrivals</button>
<button data-mode="subjects">Subjects</button>
<button data-mode="surprise">Surprise me</button>
</nav>
<form id="search">
<input id="query" aria-label="Book title or author" placeholder="Book title or author" maxlength="500">
<button type="submit" value="shelf">Search shelf</button>
<button type="submit" value="gutenberg">Search Gutenberg</button>
</form>
<div class="shelf-tools"><label id="sort-label" for="shelf-sort">Sort shelf</label><select id="shelf-sort"><option value="title">Title · A–Z</option><option value="author">Author · A–Z</option><option value="opened">Last opened</option><option value="added">Date added</option></select><span id="result-count"></span></div>
<div id="items">
</div>
<button id="load-more" hidden>Load more books</button>
</section>
</main>
<script src="/browser-views.js">
</script>
</body>
</html>
'''


def handle(handler,node_url,payload=None):
    """Caller has checked lo.use; never accept an arbitrary proxy destination."""
    parsed=urllib.parse.urlsplit(handler.path)
    action=parsed.path.removeprefix('/api/books').strip('/')
    query=urllib.parse.parse_qs(parsed.query)
    allowed={'target','id','chapter','paragraph','mode','subject','image','content','voice','query','start_index','pauses'}
    query={k:v[0] for k,v in query.items() if k in allowed}
    route={'':'/v1/books/fabric','read':'/v1/books/read','audio':'/v1/books/audio','voices':'/v1/books/voices','cover':'/v1/books/cover','image':'/v1/books/image','discover':'/v1/books/discover','discovery-cover':'/v1/books/discovery-cover'}.get(action)
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
            handler.send_header('Cache-Control','private, no-store');handler.send_header('X-Content-Type-Options','nosniff');handler.end_headers()
            while block:=response.read(65536):handler.wfile.write(block)
    except urllib.error.HTTPError as exc:
        body=exc.read(65536)
        handler.send_response(exc.code);handler.send_header('Content-Type','application/json');handler.send_header('Content-Length',str(len(body)));handler.end_headers();handler.wfile.write(body)
