"""Read-only per-command help generated from the live command registry and parsers."""
import json
from pathlib import Path


def show(words):
    text=' '.join(words).strip()
    text=text.removeprefix('lk ')
    if text in {'notes','tasks','reminders','lkn'}:
        import notebook
        return notebook.main(['--help'])
    data=json.loads((Path(__file__).with_name('docs')/'command_help.json').read_text())
    root=text.split()[0] if text else ''
    root={'o':'lo','music':'media'}.get(root,root)
    page=data.get(root)
    if not page:
        print('LOOK HELP · command not found: '+text)
        print('Available: '+', '.join(sorted(data)))
        return 2
    print(page)
    return 0
