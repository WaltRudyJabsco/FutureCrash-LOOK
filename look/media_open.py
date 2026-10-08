"""Linux graphical media edge, independent of desktop MIME registration."""
from __future__ import annotations
import json, os, shutil, sys
from pathlib import Path
try:
    from . import media_core
except ImportError:
    import media_core


def mpv_binary():
    binary=shutil.which('mpv')
    if binary: return binary
    for base in ('/home/linuxbrew/.linuxbrew/bin','/usr/local/bin','/usr/bin','/opt/homebrew/bin'):
        path=Path(base)/'mpv'
        if path.is_file() and os.access(path,os.X_OK): return str(path)
    return None


def command(path,preferred=None):
    """Use the configured app or mpv for Linux media; other types use the OS."""
    path=Path(path)
    if not sys.platform.startswith('linux') or path.suffix.casefold() not in media_core.MEDIA_EXTENSIONS: return None
    category='video' if path.suffix.casefold() in media_core.VIDEO_EXTENSIONS else 'audio'
    if preferred is None:
        try: preferred=json.loads((Path.home()/'.local/share/look/apps.json').read_text()).get(category,'system')
        except (OSError,ValueError,AttributeError): preferred='system'
    if preferred and preferred!='system':
        binary=shutil.which(preferred)
        if binary is None and Path(preferred).is_file() and os.access(preferred,os.X_OK): binary=preferred
        if binary is None: raise OSError(f'Preferred {category} app is unavailable: {preferred}')
        return [binary,str(path)]
    binary=mpv_binary()
    return [binary,'--player-operation-mode=pseudo-gui','--',str(path)] if binary else None
