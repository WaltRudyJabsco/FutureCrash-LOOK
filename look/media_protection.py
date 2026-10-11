"""Bounded ISO-BMFF sample-entry inspection; never guess protection from .m4v."""
from pathlib import Path
import struct

CONTAINERS = {b'moov', b'trak', b'mdia', b'minf', b'stbl'}
PROTECTED = {b'encv', b'enca', b'drmi', b'drms'}
MAX_BOXES = 10000


def protected(path):
    path = Path(path)
    if path.suffix.casefold() == '.m4p': return True
    if path.suffix.casefold() not in {'.m4v', '.mp4', '.mov', '.m4a'}: return False
    try:
        with path.open('rb') as stream:
            size = path.stat().st_size; budget = [MAX_BOXES]
            def boxes(start, end, depth=0, sample_entries=False):
                if depth > 10: return False
                while start + 8 <= end and budget[0] > 0:
                    budget[0] -= 1; stream.seek(start); header = stream.read(8)
                    if len(header) != 8: return False
                    length, kind = struct.unpack('>I4s', header); head = 8
                    if length == 1:
                        large = stream.read(8)
                        if len(large) != 8: return False
                        length = struct.unpack('>Q', large)[0]; head = 16
                    elif length == 0: length = end - start
                    if length < head or start + length > end: return False
                    if sample_entries and kind in PROTECTED: return True
                    if kind in CONTAINERS and boxes(start + head, start + length, depth + 1): return True
                    if kind == b'stsd' and length >= head + 8 and boxes(start + head + 8, start + length, depth + 1, True): return True
                    start += length
                return False
            return boxes(0, size)
    except (OSError, ValueError, struct.error): return False


def require_generic_playback(path):
    if protected(path):
        raise ValueError('Protected media requires an authorized provider app; on a Mac use Media Find → T (Apple TV) or O (Open with)')
