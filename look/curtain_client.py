"""Local CLI/client edge. PINs travel in request bodies, never command arguments."""
import argparse
import getpass
import json
import urllib.request
import urllib.error
import sys
import shutil
import termios
import tty

URL='http://127.0.0.1:7332/v1/curtain'


def request(action='status',**fields):
    data=None if action=='status' else json.dumps(dict(action=action,**fields)).encode()
    req=urllib.request.Request(URL,data=data,headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=15) as response:result=json.load(response)
    except urllib.error.HTTPError as error:
        try:message=json.load(error).get('error','Curtain request failed')
        except ValueError:message='Curtain request failed'
        raise ValueError(message) from None
    if result.get('error'):raise ValueError(result['error'])
    return result


def read_pin(prompt):
    if not sys.stdin.isatty():return getpass.getpass(prompt)
    fd=sys.stdin.fileno();prior=termios.tcgetattr(fd);digits=[]
    try:
        tty.setraw(fd)
        sys.stdout.write(prompt);sys.stdout.flush()
        while len(digits)<4:
            key=sys.stdin.read(1)
            if key in {'\x03','\x1b','\x04',''}:raise EOFError('PIN entry cancelled')
            if key in {'\x7f','\b'} and digits:
                digits.pop();sys.stdout.write('\b \b');sys.stdout.flush()
            elif key in '0123456789' and key:
                digits.append(key);sys.stdout.write('*');sys.stdout.flush()
        return ''.join(digits)
    finally:
        # Discard queued paste/Enter bytes so they cannot answer the next prompt.
        termios.tcsetattr(fd,termios.TCSAFLUSH,prior)
        sys.stdout.write('\n');sys.stdout.flush()


def main(args,command='lock'):
    parser=argparse.ArgumentParser(prog='lk '+command,description='Fabric PIN curtain (not an OS lock)')
    parser.add_argument('action',nargs='?',choices=('setup','status','lock','unlock'))
    opts=parser.parse_args(args)
    if opts.action is None and command=='lock':return picker()
    action=opts.action or ('unlock' if command=='unlock' else 'lock')
    try:
        fields={'variant':'they-live'} if command=='lktl' and action=='lock' else {}
        if action=='setup':
            if request().get('configured'):fields['old_pin']=read_pin('Current PIN: ')
            fields['pin']=read_pin('New four-digit PIN: ')
            if fields['pin']!=read_pin('Repeat PIN: '):raise ValueError('PINs do not match')
        elif action=='unlock':fields['pin']=read_pin('PIN: ')
        result=request(action,**fields)
        print('LOOK CURTAIN · '+('covered' if result.get('locked') else 'open'))
        for item in result.get('delivery',[]):
            print(item['node']+' · '+(item.get('desktop') or 'received' if item.get('ok') else item.get('error','failed')))
        if not result.get('configured'):print('First use: lk lock setup')
        return 0 if result.get('ok') else 1
    except (OSError,ValueError,EOFError) as exc:print('LOOK CURTAIN · '+str(exc));return 1


def picker():
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print('LOOK CURTAIN · lk lk starts · lk unlock opens · lk lock setup chooses PIN')
        return 0
    import terminal_style
    message=''
    while True:
        try:state=request()
        except (OSError,ValueError) as exc:state={};message=str(exc)
        print('\033[2J\033[HLOOK CURTAIN\n')
        print('Flight Deck · Bridge · all reachable paired nodes')
        print('Ambient PIN curtain · not an operating-system lock\n')
        print('PIN: '+('configured' if state.get('configured') else 'not set'))
        print('This node: '+('covered' if state.get('locked') else 'open'))
        print('AI captions: cached text if prepared; built-in text otherwise\n')
        for line in terminal_style.command_lines('L lock now · U unlock · P set/change PIN · G prepare AI captions · R refresh · Q back',shutil.get_terminal_size().columns-1):print(line)
        if message:print('\n'+message)
        fd=sys.stdin.fileno();prior=termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd);key=sys.stdin.read(1).lower()
        finally:termios.tcsetattr(fd,termios.TCSADRAIN,prior)
        if key in {'q','\x1b','\x03'}:return 0
        if key=='r':continue
        if key=='g':
            try:
                import saver_text
                saver_text.generate();message='AI captions prepared for the next lock'
            except Exception as exc:message=str(exc)
        elif key in {'l','u','p'}:
            action={'l':'lock','u':'unlock','p':'setup'}[key]
            code=main([action]);message='Action completed' if code==0 else 'Action failed; see message above'
            if key=='l' and code==0:return 0
            input('Press Enter to return to the curtain settings…')
