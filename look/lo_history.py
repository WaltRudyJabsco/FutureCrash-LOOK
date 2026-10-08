"""Device-local prompt recall. No attachments, responses, or replayed commands."""
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
import fcntl
import json
import os

try:
    import readline
except ImportError:
    readline = None

LIMIT = 500
MAX_PROMPT = 32768


def history_path():
    return Path.home() / '.local/share/look/lo_history.json'


def _load(path):
    try:
        if path.stat().st_size > LIMIT * MAX_PROMPT * 6: return []
        rows = json.loads(path.read_text())
        return [x for x in rows if isinstance(x, str) and '\n' not in x and len(x) <= MAX_PROMPT][-LIMIT:]
    except (OSError, ValueError, TypeError):
        return []


def remember(prompt):
    prompt = str(prompt).strip()
    if not prompt or '\n' in prompt or len(prompt) > MAX_PROMPT: return
    path = history_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path.with_suffix('.lock'), 'a') as lock:
            os.chmod(lock.name, 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX)
            rows = _load(path)
            if not rows or rows[-1] != prompt:
                rows.append(prompt)
                tmp = path.with_name(f'.lo_history.{os.getpid()}.tmp')
                fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, 'w') as out: json.dump(rows[-LIMIT:], out, ensure_ascii=False)
                os.replace(tmp, path)
    except OSError:
        pass  # Recall must never prevent a chat turn.
    if readline is not None:
        try:
            count = readline.get_current_history_length()
            if not count or readline.get_history_item(count) != prompt:
                readline.add_history(prompt)
        except (AttributeError, RuntimeError): pass


@contextmanager
def prompt_history():
    if readline is None:
        yield
        return
    original = [readline.get_history_item(i) for i in range(1, readline.get_current_history_length() + 1)]
    try:
        readline.clear_history()
        for text in _load(history_path()): readline.add_history(text)
        # Record submitted LO prompts explicitly, excluding confirmation inputs.
        if hasattr(readline, 'set_auto_history'): readline.set_auto_history(False)
        yield
    finally:
        readline.clear_history()
        for text in original:
            if text is not None: readline.add_history(text)
        if hasattr(readline, 'set_auto_history'): readline.set_auto_history(True)


def session(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        if kwargs.get('one_shot'):
            return function(*args, **kwargs)
        with prompt_history():
            initial = kwargs.get('initial_prompt')
            if initial: remember(initial)
            return function(*args, **kwargs)
    return wrapped
