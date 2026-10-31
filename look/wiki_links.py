"""Literal LK Wiki references for Markdown notes; never shell commands or web URLs."""
from pathlib import PurePosixPath
import re
from urllib.parse import urlsplit,parse_qs,unquote,quote,urlencode
from notebook_markdown import safe_text


def parse(target):
    parts=urlsplit(target)
    if parts.scheme!='wiki' or parts.netloc or parts.fragment:raise ValueError('Use wiki:Article_title with optional source, node and archive')
    title=unquote(parts.path)
    if not title or len(title)>500 or safe_text(title)!=title or any(c in '\n\t<>' for c in title):raise ValueError('Wiki links need one article title without controls')
    query=parse_qs(parts.query,keep_blank_values=True)
    if set(query)-{'source','node','archive'} or any(len(v)!=1 for v in query.values()):raise ValueError('Unknown or repeated Wiki link field')
    value={k:v[0] for k,v in query.items()}
    source=value.get('source','saved')
    if source not in {'saved','live'}:raise ValueError('Wiki source must be saved or live')
    node=value.get('node')
    if node is not None and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,100}',node):raise ValueError('Invalid Wiki archive owner')
    archive=value.get('archive')
    if archive is not None and (PurePosixPath(archive).name!=archive or not archive.endswith('.zim') or len(archive)>255 or safe_text(archive)!=archive):raise ValueError('Wiki archive must be a ZIM filename, not a path')
    if source=='live' and (node or archive):raise ValueError('Live Wiki links do not have an archive owner')
    return dict(title=title,source=source,node=node,archive=archive)


def target(title,*,live=False,node=None,archive=None):
    query={'source':'live' if live else 'saved'}
    if not live:
        if node:query['node']=node
        if archive:query['archive']=archive
    value='wiki:'+quote(title,safe='')+'?'+urlencode(query)
    parse(value)
    return value
