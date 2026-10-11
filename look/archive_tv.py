"""Small Internet Archive adapter; playback stays in LOOK's existing player."""
from __future__ import annotations
import errno
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
import urllib.parse
import urllib.request

BASE = 'https://archive.org'
MAX_METADATA = 8 * 1024 * 1024
MEATY = 'mrmeatyallepisodesspecialspromosextra'
MTV = '1981.08.01_MTV_First_Four_Hours_12am_Saturday_August_1st_1981'
CHANNELS = {'mtv': 'Early MTV', 'prelinger': 'Prelinger films', 'animation': 'Animation', 'meaty': 'Mr. Meaty'}
QUERIES = {'mtv': 'title:MTV AND year:[1981 TO 1989] AND mediatype:movies',
           'prelinger': 'collection:prelinger AND mediatype:movies',
           'animation': 'collection:animationandcartoons AND mediatype:movies'}


def label(value):
    return ''.join(c for c in str(value) if c.isprintable())[:300]


def identifier(value):
    value = str(value).strip()
    if value in {'mtv', 'meaty'}: return MTV if value == 'mtv' else MEATY
    if value.startswith('https://archive.org/details/'):
        value = urllib.parse.urlparse(value).path.split('/')[2]
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,199}', value):
        raise ValueError('Use an Archive item identifier or https://archive.org/details/… URL')
    return value


def read_json(path):
    request = urllib.request.Request(BASE + path, headers={'User-Agent': 'FutureCrash-LOOK ArchiveTV/1.0', 'Accept': 'application/json'})
    with urllib.request.urlopen(request, timeout=15) as response:
        data = response.read(MAX_METADATA + 1)
    if len(data) > MAX_METADATA: raise ValueError('Archive metadata exceeds limit')
    result = json.loads(data)
    if not isinstance(result, dict): raise ValueError('Invalid Archive metadata')
    return result


def metadata(item):
    item = identifier(item)
    data = read_json('/metadata/' + item)
    if not data.get('metadata'): raise ValueError('Archive item unavailable: ' + item)
    if str(data['metadata'].get('access-restricted-item', '')).casefold() in {'true', '1'}:
        raise ValueError('Archive item requires access authorization')
    return data


def videos(item, data):
    """One MP4 per source file, preferring Archive's streaming derivative."""
    item = identifier(item); grouped = {}
    for file in data.get('files', []):
        name = str(file.get('name') or ''); path = PurePosixPath(name)
        if (not name.lower().endswith('.mp4') or path.is_absolute() or '..' in path.parts
                or any(ord(c) < 32 or ord(c) == 127 for c in name)
                or str(file.get('private', '')).casefold() in {'true', '1'}): continue
        key = re.sub(r'\.ia(?=\.mp4$)', '', name, flags=re.I)
        old = grouped.get(key)
        if old is None or 'IA' in str(file.get('format', '')): grouped[key] = file
    rows = []
    for name, file in sorted(grouped.items()):
        title = label(Path(name).stem)
        rows.append({'id': item + '/' + file['name'], 'title': title,
                     'artist': 'Internet Archive', 'album': label(data['metadata'].get('title', item)),
                     'path': BASE + '/download/' + item + '/' + urllib.parse.quote(file['name'], safe='/'),
                     'source_url': BASE + '/details/' + item, 'media_type': 'video/mp4', 'format': 'mp4',
                     'bytes': int(file.get('size') or 0), 'archive_item': item, 'archive_file': file['name']})
    return rows


def item_queue(item):
    item = identifier(item); rows = videos(item, metadata(item))
    if not rows: raise ValueError('No publicly available MP4 playback files for ' + item)
    return rows


def meaty_queue(data=None, extras=False):
    """Paired aired episodes: S1 01–12, S2 01–06, then two full specials.

    Sources: Archive file inventory; https://thetvdb.com/series/mr-meaty/allseasons/official
    Shorts/promos are separate so a filename sort cannot insert them into episodes.
    """
    rows = videos(MEATY, data or metadata(MEATY)); episodes = {}; bonus = []; special = {}
    for row in rows:
        name = row['archive_file']; match = re.search(r'S(\d{2})E(\d{2})\s*-', name, re.I)
        if match and ((int(match[1]) == 1 and 1 <= int(match[2]) <= 12) or (int(match[1]) == 2 and 1 <= int(match[2]) <= 6)):
            key = (int(match[1]), int(match[2])); episodes[key] = row
        elif Path(name).name.casefold() in {'big greasy musical.mp4', 'dream of the dead.mp4'}:
            special[Path(name).name.casefold()] = row
        elif 'extras/' in name.casefold(): bonus.append(row)
    missing = [(s, e) for s, count in ((1, 12), (2, 6)) for e in range(1, count + 1) if (s, e) not in episodes]
    if missing: raise ValueError('Mr. Meaty source is incomplete: ' + ', '.join(f'S{s:02}E{e:02}' for s, e in missing))
    if len(special) != 2: raise ValueError('Mr. Meaty source is missing a full-length special')
    queue = [episodes[key] for key in sorted(episodes)]
    for title in ('big greasy musical.mp4', 'dream of the dead.mp4'):
        row = dict(special[title]); row['title'] = 'Special · ' + row['title']; queue.append(row)
    return queue + bonus if extras else queue


def search(query, limit=12):
    params = urllib.parse.urlencode({'q': query, 'output': 'json', 'rows': min(40, max(1, limit)),
                                    'fl[]': 'identifier', 'sort[]': 'downloads desc'})
    result = read_json('/advancedsearch.php?' + params)
    return [identifier(row['identifier']) for row in result.get('response', {}).get('docs', []) if row.get('identifier')]


def channel_queue(channel, limit=8):
    if channel == 'meaty': return meaty_queue(), []
    if channel not in QUERIES: raise ValueError('Channel must be mtv, prelinger, animation or meaty')
    items = search(QUERIES[channel], limit)
    if channel == 'mtv': items = [MTV] + [item for item in items if item != MTV]
    queue = []; unavailable = []
    for item in items[:limit]:
        try: queue.append(item_queue(item)[0])
        except (OSError, ValueError) as exc: unavailable.append(label(exc))
    if not queue: raise ValueError('No playable Archive items: ' + '; '.join(unavailable[:2]))
    return queue, unavailable


def download(row, directory):
    """Explicit download; no overwrites, redirects to local paths, or auto-import."""
    directory = Path(directory).expanduser().resolve(); directory.mkdir(parents=True, exist_ok=True)
    target = directory / Path(row['archive_file']).name
    expected = int(row.get('bytes') or 0)
    if not expected or shutil.disk_usage(directory).free < expected + 64 * 1024 * 1024:
        raise ValueError('Download size unknown or insufficient free space')
    if target.exists(): raise ValueError('Destination already exists: ' + str(target))
    fd, temporary = tempfile.mkstemp(prefix='.archive-', suffix='.part', dir=directory)
    try:
        with os.fdopen(fd, 'wb') as out, urllib.request.urlopen(row['path'], timeout=30) as source:
            copied = 0
            for block in iter(lambda: source.read(1024 * 1024), b''):
                copied += len(block)
                if copied > expected: raise ValueError('Archive download exceeds reported size')
                out.write(block)
            if copied != expected: raise ValueError('Incomplete Archive download')
        # Hard-link publication is exclusive; a concurrently created file wins.
        try:
            os.link(temporary, target)
        except OSError as exc:
            if exc.errno not in {errno.EPERM, errno.EOPNOTSUPP, errno.EXDEV, errno.ENOSYS}:
                raise
            # exFAT has no hard links; exclusive creation still protects existing files.
            with open(target, 'xb') as out:
                try:
                    with open(temporary, 'rb') as source:
                        shutil.copyfileobj(source, out)
                except BaseException:
                    target.unlink()
                    raise
    finally:
        os.unlink(temporary)
    return target
