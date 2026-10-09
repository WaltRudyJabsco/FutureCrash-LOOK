"""One isolated LO turn. Pipes carry JSON; the worker never inherits the TUI input."""
import json
from pathlib import Path
import sys


def main():
    for folder in (Path(__file__).resolve().parents[1]/'look',Path.home()/'.local/share/look'):
        if (folder/'lo_engine.py').is_file():
            sys.path.insert(0,str(folder))
            break
    import lo_engine
    payload=json.load(sys.stdin)
    if not isinstance(payload,dict): raise ValueError('LO request must be an object')
    result=lo_engine.chat_once(**payload)
    json.dump(result,sys.stdout,ensure_ascii=False)
    return 0


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc),file=sys.stderr)
        raise SystemExit(1)
