"""Small terminal Markdown preview. Source text remains the notebook's authority."""
from __future__ import annotations

import re
import unicodedata

RESET='\033[0m'
CYAN=('38;5;117',)
DIM=('2',)
CODE=('38;5;180',)
PLAIN=re.compile(r'[^\\`*_~\[]+')


def safe_text(text):
    """Keep Unicode (including joiners); show terminal controls as inert escapes."""
    return ''.join(char if char in '\n\t' or unicodedata.category(char) not in {'Cc','Cs'}
                   else ('\\x%02x' % ord(char)) for char in text.replace('\r\n','\n').replace('\r','\n'))


def markdown_link(text):
    match=re.match(r'\[([^\]\n]+)\]\(',text)
    if not match: return None
    start=match.end(); end=start; nesting=1; angled=text[start:start+1]=='<'
    if angled:
        close=text.find('>',start+1)
        if close<0 or text[close+1:close+2]!=')': return None
        return match[1],text[start+1:close],close+2
    while end<len(text):
        char=text[end]
        if char=='\n': return None
        if char=='(': nesting+=1
        elif char==')':
            nesting-=1
            if not nesting: return match[1],text[start:end],end+1
        end+=1
    return None


def inline(text,style=(),depth=0,links=None):
    """Parse paired marks only; incomplete Markdown remains readable as text."""
    spans=[]; cursor=0
    while cursor<len(text):
        literal=PLAIN.match(text,cursor)
        if literal:
            spans.append((literal[0],style)); cursor=literal.end(); continue
        rest=text[cursor:]
        if rest.startswith('\\') and len(rest)>1 and rest[1] in r'\`*_{}[]()#+-.!>~':
            spans.append((rest[1],style)); cursor+=2; continue
        ticks=re.match(r'`+',rest)
        if ticks:
            marker=ticks[0]; end=text.find(marker,cursor+len(marker))
            if end>=0:
                spans.append((text[cursor+len(marker):end],style+CODE))
                cursor=end+len(marker); continue
        link=markdown_link(rest)
        if link and depth<8:
            label,target,length=link
            spans.extend(inline(label,style+('4',)+CYAN,depth+1))
            if links is not None:
                links.append((label,target))
                spans.append((' ['+str(len(links))+']',style+CYAN))
            cursor+=length; continue
        matched=False
        for marker,accent in (('***',('1','3')),('___',('1','3')),('**',('1',)),('__',('1',)),('~~',('9',)),('*',('3',)),('_',('3',))):
            if not rest.startswith(marker) or depth>=8: continue
            start=cursor+len(marker); end=text.find(marker,start)
            if end<=start or text[start].isspace() or text[end-1].isspace(): continue
            # Underscores within identifiers are ordinary text, not emphasis.
            if '_' in marker and ((cursor and text[cursor-1].isalnum()) or
                                  (end+len(marker)<len(text) and text[end+len(marker)].isalnum())): continue
            spans.extend(inline(text[start:end],style+accent,depth+1,links))
            cursor=end+len(marker); matched=True; break
        if matched: continue
        spans.append((text[cursor],style)); cursor+=1
    return spans


def cell_width(character):
    if unicodedata.combining(character): return 0
    return 2 if unicodedata.east_asian_width(character) in {'W','F'} else 1


def wrap_spans(spans,width):
    """Wrap visible cells before adding ANSI; every row fits the note's box."""
    glyphs=[(char,style) for text,style in spans for char in text]
    rows=[]; pending=[]; cells=0
    def flush(row):
        rendered=[]; previous=None; used=0
        for char,style in row:
            if style!=previous:
                rendered.append('\033[0'+(';'+';'.join(style) if style else '')+'m'); previous=style
            rendered.append(char); used+=cell_width(char)
        rows.append(''.join(rendered)+RESET+' '*max(0,width-used))
    for char,style in glyphs:
        size=cell_width(char)
        if size>width: char='�'; size=1
        if cells+size>width:
            split=next((i for i in range(len(pending)-1,0,-1) if pending[i][0]==' '),None)
            if split is None:
                flush(pending); pending=[]; cells=0
            else:
                flush(pending[:split]); pending=pending[split+1:]
                cells=sum(cell_width(item[0]) for item in pending)
        pending.append((char,style)); cells+=size
    flush(pending)
    return rows


def render(text,width,links=None):
    """Render common note Markdown without HTML, image fetching, or side effects."""
    width=max(1,width)
    # Notes cannot inject terminal commands. Tabs keep a predictable visual width.
    text=safe_text(text).expandtabs(4)
    lines=text.splitlines(); rows=[]; fence=None; index=0
    while index<len(lines):
        line=lines[index]; index+=1
        marker=re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$',line)
        if fence:
            if marker and marker[1][0]==fence[0] and len(marker[1])>=len(fence) and not marker[2].strip():
                fence=None
            else: rows.extend(wrap_spans([(line,CODE)],width))
            continue
        if marker:
            fence=marker[1]; continue
        heading=re.match(r'^ {0,3}(#{1,6})\s+(.+?)\s*$',line)
        setext=index<len(lines) and line.strip() and re.fullmatch(r' {0,3}(=+|-+)\s*',lines[index])
        if heading or setext:
            level=len(heading[1]) if heading else (1 if lines[index].strip().startswith('=') else 2)
            title=re.sub(r'\s+#+\s*$','',heading[2]) if heading else line.strip()
            if setext and not heading: index+=1
            style=(('1',) if level<=2 else ())+CYAN
            if level>=4: style+=DIM
            rows.extend(wrap_spans(inline(title,style,links=links),width)); continue
        if re.fullmatch(r' {0,3}(?:(?:\*\s*){3,}|(?:-\s*){3,}|(?:_\s*){3,})',line):
            rows.extend(wrap_spans([('─'*width,DIM)],width)); continue
        quote=re.match(r'^ {0,3}>\s?(.*)$',line)
        if quote:
            rows.extend(wrap_spans([('│ ',CYAN)]+inline(quote[1],DIM,links=links),width)); continue
        item=re.match(r'^(\s*)(?:[-+*]|\d+[.)])\s+(.*)$',line)
        if item:
            task=re.match(r'^\[([ xX])\]\s*(.*)$',item[2])
            number=re.match(r'^\s*(\d+)[.)]',line)
            prefix=item[1]+(('☑ ' if task[1].lower()=='x' else '☐ ') if task else
                            (number[1]+'. ' if number else '• '))
            body=task[2] if task else item[2]
            rows.extend(wrap_spans([(prefix,CYAN)]+inline(body,DIM if task and task[1].lower()=='x' else (),links=links),width)); continue
        rows.extend(wrap_spans(inline(line,links=links),width))
    return rows


def extract_links(text):
    links=[]
    render(text,240,links)
    return links
