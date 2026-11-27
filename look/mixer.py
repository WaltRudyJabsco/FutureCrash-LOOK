"""Mercury Mix launcher and read-only assistant discovery."""
import argparse
import json
import sys
import urllib.request
import urllib.error
import webbrowser
from pathlib import Path

HOSTS={'signal':'http://127.0.0.1:7331','albert':'http://127.0.0.1:7330'}


def origin(preferred=None):
    for name in ([preferred] if preferred else HOSTS):
        try:
            with urllib.request.urlopen(HOSTS[name]+('/api/status' if name=='signal' else '/health'),timeout=1) as response:
                if response.status==200:return HOSTS[name]
        except urllib.error.HTTPError as exc:
            # An authenticated host is running even when this probe has no cookie.
            if exc.code in {401,403}:return HOSTS[name]
        except (OSError,ValueError):pass
    raise ValueError('Start Signal or Albert from LK Services, then run lk mix again. Mercury Mix uses their existing browser access.')


def main(argv=None):
    parser=argparse.ArgumentParser(prog='lk mix',description='Mercury Mix: two browser-local decks, a shared fader and your Fabric music library.')
    parser.add_argument('--host',choices=list(HOSTS));parser.add_argument('--url',action='store_true',help='Print the local browser address without opening it')
    args=parser.parse_args(argv)
    try:
        url=origin(args.host)+'/mix'
        if not args.url:webbrowser.open(url)
        print(url);return 0
    except (OSError,ValueError) as exc:print('Mercury Mix: '+str(exc));return 1


def tools():
    return [{'type':'function','function':{'name':'mix_library','description':'Find music available for Mercury Mix, the two-deck browser instrument at /mix in Signal and Albert (lk mix from a terminal). Returns real Fabric track references. Read-only: does not start playback or control an active browser mix.','parameters':{'type':'object','properties':{'query':{'type':'string','maxLength':200}},'additionalProperties':False}}}]


def run_tool(args):
    if not isinstance(args,dict) or set(args)-{'query'} or not isinstance(args.get('query',''),str) or len(args.get('query',''))>200:raise ValueError('Use an optional music query up to 200 characters')
    import fabric_files
    # Core is shared by the browser gateways and this catalog hook.
    try:from core import mixer_web
    except ImportError:
        core=Path.home()/'.local/share/future-crash-look/core'
        if str(core) not in sys.path:sys.path.insert(0,str(core))
        import mixer_web
    value=mixer_web.catalog(fabric_files.request('/v1/media/fabric',timeout=12),args.get('query',''))
    rows=value['entries']
    return json.dumps({'entries':rows[:24],'matches':value['total'],'mixer_path':'/mix','launch_command':'lk mix','errors':value.get('errors',[])})
