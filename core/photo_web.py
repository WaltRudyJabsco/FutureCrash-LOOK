"""Authenticated browser CAM captures share Photo's durable save and LK Clip path."""
from pathlib import Path
import socket
import sys
import urllib.parse
try:from .radio_web import send
except ImportError:from radio_web import send


def post(handler):
    origin=urllib.parse.urlsplit(handler.headers.get('Origin',''))
    if not origin.netloc or origin.netloc!=handler.headers.get('Host'):
        raise ValueError('Open this camera from Signal or Albert directly')
    for folder in (Path(__file__).resolve().parent.parent/'look',Path.home()/'.local/share/look'):
        if (folder/'photo_capture.py').exists() and str(folder) not in sys.path:sys.path.insert(0,str(folder))
    import photo_capture
    size=int(handler.headers.get('Content-Length','0'))
    if handler.headers.get('Content-Type')!='image/png' or not 0<size<=photo_capture.MAX_PHOTO_BYTES:
        raise ValueError('Capture must be PNG and at most 3 MiB')
    data=handler.rfile.read(size)
    if len(data)!=size:raise ValueError('Photo upload was incomplete')
    # A remote browser contributes to this host's shelf, without replacing its desktop clipboard.
    result=photo_capture.save_photo(data,Path.home()/'Pictures/LOOK Photos',system_clipboard=False)
    return send(handler,200,dict(result,host=socket.gethostname()))
