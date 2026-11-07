"""Bounded clipboard snapshots. Attachments are data, never commands or host paths."""
import base64
import json
import mimetypes
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import unquote, urlparse

PREFIX = "LOOK-CLIP-ATTACHMENT/1\n"
MAX_BYTES = 3 * 1024 * 1024
MAX_ENCODED = 4 * MAX_BYTES // 3 + 4096


def pack(data, name, mime=None):
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Clipboard attachments must be nonempty and at most 3 MiB")
    name = Path(name).name[:200] or "clipboard.bin"
    return PREFIX + json.dumps(dict(name=name, mime=mime or mimetypes.guess_type(name)[0] or "application/octet-stream",
                                   data=base64.b64encode(data).decode()), sort_keys=True)


def unpack(value):
    if not value or not value.startswith(PREFIX):
        return None
    if len(value) > MAX_ENCODED:
        raise ValueError("Clipboard attachment is too large")
    item = json.loads(value[len(PREFIX):])
    if not isinstance(item, dict) or not all(isinstance(item.get(k), str) for k in ('name', 'mime', 'data')):
        raise ValueError("Invalid clipboard attachment")
    data = base64.b64decode(item['data'], validate=True)
    if not data or len(data) > MAX_BYTES or Path(item['name']).name != item['name'] or item['name'] in {'.', '..', ''}:
        raise ValueError("Invalid clipboard attachment")
    return dict(name=item['name'], mime=item['mime'], data=data)


def describe(value):
    try:
        item = unpack(value)
        return f"[{item['mime']}] {item['name']} · {len(item['data']):,} bytes" if item else value
    except (ValueError, TypeError):
        return "[Unavailable attachment]"


def file_snapshot(uri, for_print=False):
    parsed = urlparse(uri)
    if parsed.scheme != 'file' or parsed.netloc not in {'', 'localhost'}:
        raise ValueError('Only local copied files can be captured')
    path = Path(unquote(parsed.path))
    image=path.suffix.lower() in {'.png','.jpg','.jpeg'}
    limit=64*1024*1024 if for_print and image else MAX_BYTES
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError('Copy one regular file up to '+str(limit//(1024*1024))+' MiB; folders are not captured')
    with path.open('rb') as stream:
        data=stream.read(limit+1)
        return image_snapshot(data,path.name,mimetypes.guess_type(path.name)[0],for_print) if image else pack(data,path.name)


def run(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, timeout=3, **kwargs).stdout


def image_snapshot(data,name,mime,for_print=False):
    if for_print and len(data)>MAX_BYTES:
        import tempfile
        import clipboard_image
        with tempfile.TemporaryDirectory(prefix='look-clip-image-') as folder:
            source=Path(folder)/name;source.write_bytes(data)
            output=Path(folder)/'print-copy.png'
            info=clipboard_image.process(source,output=output,limit=MAX_BYTES)
            print('Large clipboard image: preparing '+str(info['size'][0])+' × '+str(info['size'][1])+' print copy; original clipboard unchanged.')
            return pack(output.read_bytes(),'clipboard-print.png','image/png')
    return pack(data,name,mime)


def capture(text_reader, for_print=False):
    """Prefer file ownership metadata, then image bytes, then plain text."""
    if sys.platform == 'darwin':
        script = r'''ObjC.import('AppKit');
var p=$.NSPasteboard.generalPasteboard;
var u=ObjC.unwrap(p.stringForType('public.file-url'));
if(u && Number(p.pasteboardItems.count)>1) JSON.stringify({error:'Copy one file at a time'});
else if(u) JSON.stringify({uri:u});
else { var d=p.dataForType('public.png');
if(!ObjC.unwrap(d)) {var t=p.dataForType('public.tiff'); if(ObjC.unwrap(t)) {var r=$.NSBitmapImageRep.imageRepWithData(t); if(ObjC.unwrap(r)) d=r.representationUsingTypeProperties($.NSBitmapImageFileTypePNG,$.NSDictionary.dictionary);}}
if(ObjC.unwrap(d) && Number(d.length)<=3145728) JSON.stringify({png:ObjC.unwrap(d.base64EncodedStringWithOptions(0))});
else if(ObjC.unwrap(d)) JSON.stringify({error:'Image exceeds 3 MiB'}); else '{}'; }'''
        if for_print:script=script.replace('3145728','67108864').replace('Image exceeds 3 MiB','Image exceeds 64 MiB')
        result = json.loads(run(['osascript', '-l', 'JavaScript', '-e', script]).decode())
        if result.get('error'): raise ValueError(result['error'])
        if result.get('uri'): return file_snapshot(result['uri'],for_print)
        if result.get('png'): return image_snapshot(base64.b64decode(result['png']), 'clipboard.png', 'image/png',for_print)
    else:
        wayland = bool(os.environ.get('WAYLAND_DISPLAY'))
        prefix = ['wl-paste'] if wayland else ['xclip', '-selection', 'clipboard', '-o']
        listing = prefix + (['--list-types'] if wayland else ['-t', 'TARGETS'])
        try: types = run(listing).decode().splitlines()
        except (OSError, subprocess.SubprocessError): return text_reader()
        def read(kind): return run(prefix + (['--type', kind] if wayland else ['-t', kind]))
        if 'text/uri-list' in types:
            uris = [s for s in read('text/uri-list').decode().splitlines() if s and not s.startswith('#')]
            if len(uris) != 1: raise ValueError('Copy one file at a time')
            return file_snapshot(uris[0],for_print)
        for kind, name in [('image/png','clipboard.png'), ('image/jpeg','clipboard.jpg')]:
            if kind in types: return image_snapshot(read(kind), name, kind,for_print)
    return text_reader()


def restore(value, text_writer, root):
    item = unpack(value)
    if not item: return text_writer(value)
    # A stable private file also makes recalled file URLs usable after the popup exits.
    import hashlib
    target = Path(root)/'recalled'/hashlib.sha256(item['data']).hexdigest()/item['name']
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    target.write_bytes(item['data']); target.chmod(0o600)
    if sys.platform == 'darwin':
        script = r'''ObjC.import('AppKit'); function run(a){var p=$.NSPasteboard.generalPasteboard;p.clearContents;
if(a[1]=='image/png'||a[1]=='image/jpeg') {var d=$.NSData.dataWithContentsOfFile(a[0]);p.setDataForType(d,a[1]=='image/png'?'public.png':'public.jpeg');}
else p.setStringForType($.NSURL.fileURLWithPath(a[0]).absoluteString,'public.file-url');}'''
        run(['osascript','-l','JavaScript','-e',script,str(target),item['mime']])
    else:
        image = item['mime'] in {'image/png','image/jpeg'}
        mime = item['mime'] if image else 'text/uri-list'
        content = item['data'] if image else (target.as_uri()+'\r\n').encode()
        args = ['wl-copy','--type',mime] if os.environ.get('WAYLAND_DISPLAY') else ['xclip','-selection','clipboard','-t',mime]
        run(args, input=content)
    return True


def preview(value):
    try:item=unpack(value)
    except ValueError:return 'Invalid clipboard attachment'
    if not item:return value
    label=describe(value)
    if item['mime'].startswith('image/'):
        import tempfile
        try:
            import clipboard_image
            with tempfile.TemporaryDirectory(prefix='look-clip-preview-') as folder:
                path=Path(folder)/item['name'];path.write_bytes(item['data'])
                return label+'\n'+clipboard_image.process(path)['preview']
        except (OSError,ValueError,subprocess.SubprocessError) as exc:return label+'\nImage preview unavailable: '+str(exc)
    return label+'\nFile snapshot · content retained, never executed'
