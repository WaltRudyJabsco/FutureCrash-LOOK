"""Mercury Reader's read-only assistant edge: catalog first, never folder guesses."""
import json
import re
import unicodedata
from urllib.parse import urlencode


def query_text(value):
    value=str(value or '').strip().strip(' .!?')
    if len(value)>=2 and value[0] in '\"“' and value[-1] in '\"”':return value[1:-1]
    if re.search(r'\s+book$',value,re.I):value=re.sub(r'\s+book$','',value,flags=re.I);value=re.sub(r'^(?:the|a|an)\s+','',value,flags=re.I)
    return re.sub(r'^(?:the\s+)?book\s+','',value,flags=re.I).strip()


def intent(prompt):
    text=' '.join(str(prompt or '').strip().strip(' .!?').split())
    text=re.sub(r"^(?:(?:let['’]?s|let us|can we|could we|can you|could you|please|I want to|I'd like to)\s+)+",'',text,flags=re.I)
    if re.fullmatch(r'/(?:books|reader|mercury-reader)|(?:open\s+)?mercury reader|(?:show|open|list) (?:my |our |the )?(?:books|bookshelf|book library)|what books (?:do we|do I) have',text,re.I):return {'action':'shelf','query':''}
    if re.fullmatch(r'(?:continue|resume) (?:reading|listening)(?: please)?',text,re.I):return {'action':'resume','query':''}
    match=re.fullmatch(r'(?:read(?: more(?: of)?)?|start reading|continue(?: reading| listening)?|resume(?: reading| listening)?|listen to)\s+(.+?)(?:\s+please)?',text,re.I)
    if not match:return None
    query=re.sub(r'^to\s+','',match[1],flags=re.I)
    if re.match(r'(?:(?:my|our|the)\s+)?(?:notes?|files?|articles?|webpages?|messages?|clipboard|music|playback|songs?|tracks?|albums?|playlists?|podcasts?|videos?|movies?)\b|(?:this|that|it|with|writing|working|from|on|about|up on)\b',query,re.I):return None
    return {'action':'resume','query':query_text(query)}


def folded(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(text).casefold()) if not unicodedata.combining(c))


def similarity(a,b):
    # Fuzzy results are suggestions only, never authority to open the wrong book.
    if min(len(a),len(b))<4:return 0
    left=[a[i:i+2] for i in range(len(a)-1)];right=[b[i:i+2] for i in range(len(b)-1)]
    common=0;remaining=list(right)
    for pair in left:
        if pair in remaining:common+=1;remaining.remove(pair)
    return 2*common/max(1,len(left)+len(right))


def matches(query,entries):
    terms=folded(query_text(query)).split()
    exact=[row for row in entries if all(term in folded(row.get('title','')+' '+row.get('author','')) for term in terms)]
    if exact:return {'status':'matched','entries':exact}
    scored=[]
    for row in entries:
        words=re.findall(r'\w+',folded(row.get('title','')+' '+row.get('author','')))
        score=min((max((similarity(term,word) for word in words),default=0) for term in terms),default=0)
        if score>=.65:scored.append((score,row))
    scored.sort(key=lambda item:item[0],reverse=True)
    return {'status':'suggestions' if scored else 'no_match','entries':[row for _,row in scored[:8]]}


def lookup(query='',catalog=None,book_ids=None):
    if len(query)>500:raise ValueError('Book search is limited to 500 characters')
    if catalog is None:
        import books
        catalog=books.catalog()
    rows=catalog.get('entries',[])
    if book_ids is not None:rows=[row for row in rows if row['id'] in book_ids]
    result=matches(query,rows);unique={}
    for row in sorted(result['entries'],key=lambda r:(r.get('offline',False),-r.get('reading',{}).get('updated',0))):unique.setdefault(row['id'],row)
    entries=[]
    for row in list(unique.values())[:30]:
        item={key:row[key] for key in ('id','title','author','format','node','reading','offline') if key in row}
        item['reader_path']='/reader?'+urlencode({'id':row['id'],'target':row.get('node','local'),'resume':'1'})
        entries.append(item)
    status='ambiguous' if query and result['status']=='matched' and len(unique)>1 else result['status']
    return dict(service='Mercury Reader',status=status,entries=entries,total_matches=len(unique),errors=catalog.get('errors',[]),warning=catalog.get('warning',''),terminal_command='lk books',guidance='Use the Fabric bookshelf and saved reading position. Never guess media folders. Suggestions require the user to choose; no book was launched or narration started.')


def describe(result):
    rows=result['entries']
    if not rows:text='No matching book is visible on the Fabric shelf. Open Mercury Reader (/reader) to search Gutenberg or inspect the shelf.'
    else:
        text=('Closest books on your Fabric shelf—choose the one you meant:' if result['status'] in {'suggestions','ambiguous'} else 'Mercury Reader · your Fabric shelf:')
        if result.get('total_matches',0)>len(rows):text+=f" Showing {len(rows)} of {result['total_matches']} matching books."
        for row in rows:
            reading=row.get('reading',{});position=f"chapter {reading.get('chapter',0)+1}, paragraph {reading.get('paragraph',0)+1}" if reading.get('updated') else 'not started'
            text+='\n• '+row['title']+(' — '+row.get('author','') if row.get('author') else '')+' · '+position+(' · owner offline' if row.get('offline') else '')+'\n  '+row['reader_path']
        text+='\nOpen the reader link from Signal/Albert, or use `lk books` in the terminal. Reading progress is kept with the book owner.'
    if result.get('errors') or result.get('warning'):text+='\nSome book owners are unavailable; this may be an incomplete shelf.'
    return text


def tools():
    return [{'type':'function','function':{'name':name,'description':description,'parameters':{'type':'object','properties':{'query':{'type':'string','maxLength':500}},'additionalProperties':False}}} for name,description in (
        ('books_shelf','List the Mercury Reader EPUB/PDF books on the trusted Fabric shelf and their saved reading positions. Use for what books we have; do not inspect media folders.'),
        ('books_lookup','Find a Mercury Reader book by title/author and return its saved progress and owner-scoped reader link. Fuzzy suggestions require a choice. Read-only: does not open a browser, play speech, download or change progress.'))]


def run_tool(name,args):
    if name not in {'books_shelf','books_lookup'}:raise ValueError('Unknown books tool')
    return json.dumps(lookup(str(args.get('query','') or '')),ensure_ascii=False)
