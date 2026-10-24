"""Short-lived, authenticated browser references to files surfaced by cognition."""
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import threading
import time

PRESENTATION_TTL_SECONDS = 3600
PRESENTATION_LIMIT = 256


def candidates(text, events):
    # Inspect strings directly: JSON-escaping a receipt can corrupt Unicode paths.
    strings = [str(text or '')]
    def visit(value):
        if isinstance(value, str):
            strings.append(value)
            try: decoded = json.loads(value)
            except (ValueError, TypeError): return
            if isinstance(decoded, (dict, list)): visit(decoded)
        elif isinstance(value, dict):
            for child in value.values(): visit(child)
        elif isinstance(value, list):
            for child in value: visit(child)
    visit(list(events or []))
    found = []
    pattern = r'''(?:~|/)[^\n\r\t"'<>]*?\.(?:png|jpe?g|webp|gif|pdf|txt|md|html?)(?=$|[\s`"'<>),;\]])'''
    for value in strings:
        for raw in re.findall(pattern, value, flags=re.I):
            try:
                path = Path(os.path.expanduser(raw.strip())).resolve()
                if path.is_file() and path not in found: found.append(path)
            except (OSError, ValueError): pass
    return found[:8]


class Presentations:
    def __init__(self):
        self.rows = {}
        self.lock = threading.Lock()

    def present(self, path):
        path = Path(path)
        token = secrets.token_urlsafe(18)
        now = time.time()
        with self.lock:
            self.rows = {key:value for key,value in self.rows.items() if value[0] > now}
            while len(self.rows) >= PRESENTATION_LIMIT: self.rows.pop(next(iter(self.rows)))
            self.rows[token] = (now+PRESENTATION_TTL_SECONDS, path)
        return {'name':path.name, 'type':mimetypes.guess_type(str(path))[0] or 'application/octet-stream',
                'url':'/api/present/'+token}

    def get(self, token):
        with self.lock:
            row = self.rows.get(token)
            if not row: return None
            expires, path = row
            if expires <= time.time():
                self.rows.pop(token, None); return None
        return path if path.is_file() else None
