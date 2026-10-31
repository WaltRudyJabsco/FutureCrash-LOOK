"""Article image blocks: fixed layout, viewport-only work, UI-owned native painting."""
from collections import defaultdict
import look_renderer
from media_ui_work import LatestWork
from notebook_markdown import safe_text,cell_width
import wiki_images

MAX_IMAGE_COLUMNS=80
MIN_IMAGE_ROWS=4
MAX_IMAGE_ROWS=12
IMAGE_ANCHOR_BASE=-10000
IMAGE_ANCHOR_STEP=100


def layout(ui,article,width,page,hints=False,show=True):
    import wiki
    text_anchors=[];text=wiki.article_lines(ui,article,width,hints,text_anchors)
    groups=defaultdict(list)
    if show:
        for index,image in enumerate(article.get('images',[])):
            before=image.get('before')
            if type(before) is int and 0<=before<=len(article['paragraphs']):groups[before].append((index,image))
    lines=[];anchors=[];blocks=[];inserted=set()
    def insert(pi):
        if pi in inserted:return
        inserted.add(pi)
        for order,(index,image) in enumerate(groups.get(pi,())):
            cols=max(8,min(MAX_IMAGE_COLUMNS,width-1));rows=min(MAX_IMAGE_ROWS,max(MIN_IMAGE_ROWS,page-3))
            if image.get('width') and image.get('height'):
                rows=max(MIN_IMAGE_ROWS,min(rows,round(cols*image['height']/image['width']/2)))
            base=IMAGE_ANCHOR_BASE+order*IMAGE_ANCHOR_STEP
            lines.append(ui._c(f'IMAGE {index+1} · '+safe_text(image['title']),'2'));anchors.append((pi,base))
            blocks.append({'image':index,'start':len(lines),'rows':rows,'cols':cols})
            for row in range(rows):lines.append('');anchors.append((pi,base+row+1))
            lines.append('');anchors.append((pi,base+rows+1))
    for line,anchor in zip(text,text_anchors):
        insert(anchor[0]);lines.append(line);anchors.append(anchor)
    insert(len(article['paragraphs']))
    return lines,anchors,blocks


class InlineImages:
    def __init__(self,ui,*,live=False,archive='',owner='local'):
        self.ui=ui;self.source={'live':live,'archive':archive,'owner':owner}
        self.work={};self.native={};self.article={};self.pending=[]

    def reset(self,article):
        self.clear()
        for work in self.work.values():work.close()
        for native in self.native.values():native.close()
        self.work={};self.native={};self.article=article;self.pending=[]

    def compose(self,lines,blocks,top,page,native_images=True):
        visible=list(lines[top:top+page]);self.pending=[]
        for block in blocks:
            start=block['start'];rows=block['rows'];cols=block['cols']
            first=max(start,top);last=min(start+rows,top+page)
            if first>=last:continue
            index=block['image'];image=self.article['images'][index]
            if index not in self.work:self.work[index]=LatestWork()
            art,path,error=self.work[index].get((cols,rows),lambda image=dict(image),w=cols,h=rows:wiki_images.prepare(image,w,h,**self.source),([],None,'Loading image…'),ttl=60) or ([],None,'Image unavailable')
            padding=max(0,(rows-len(art))//2)
            for line in range(first,last):
                offset=line-start-padding
                if 0<=offset<len(art):
                    text=art[offset];used=sum(cell_width(c) for c in self.ui._strip_ansi(text))
                    visible[line-top]=' '*max(0,(cols-used)//2)+text
                elif not art and line==start:visible[line-top]=self.ui._c(safe_text(error or 'Image unavailable'),'2')
            if native_images and path:
                if index not in self.native:self.native[index]=look_renderer.NativePreviewController()
                self.pending.append((index,path,2+start-top,rows,cols,(2,2+page)))
        return visible

    def clear(self):
        # One clear per frame. Individual controllers must not erase siblings.
        cleared=False
        for native in self.native.values():
            if native.enabled and not cleared:native.frame_cleared();cleared=True
            else:native.invalidate()

    def paint(self):
        for index,path,row,rows,cols,clip in self.pending:
            native=self.native[index];native.clip_rows=clip
            native.request(path,row,1,rows,cols)
        for native in self.native.values():native.paint_ready()

    def close(self):
        self.clear()
        for work in self.work.values():work.close()
        for native in self.native.values():native.close()
        self.work={};self.native={};self.pending=[]
