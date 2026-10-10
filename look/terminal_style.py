"""Small, local Kitty palette controls. User fonts, keys, and shell stay owned."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import uuid

THEMES={
    'neon':{
        'background':'#071009','foreground':'#b7f7cb','cursor':'#68ff97','cursor_text_color':'#071009',
        'selection_background':'#31543a','selection_foreground':'#ffffff','url_color':'#68ff97',
        'active_tab_foreground':'#071009','active_tab_background':'#68ff97',
        'inactive_tab_foreground':'#91c79e','inactive_tab_background':'#14271a',
        'colors':('#101a14','#dc7777','#8fd6a2','#d9bf80','#83a9d9','#b69acb','#80c9c4','#c4d5c8',
                  '#617268','#f29b9b','#b5ebc2','#f1dba5','#a6c8ee','#d2b5e5','#a5e5df','#f0f6f1')},
    'paper':{
        # MercuryWriter's page and ink, with darker ANSI accents for light paper.
        'background':'#f6f1e7','foreground':'#201e1a','cursor':'#201e1a','cursor_text_color':'#f6f1e7',
        'selection_background':'#d9d0be','selection_foreground':'#201e1a','url_color':'#275b70',
        'active_tab_foreground':'#f6f1e7','active_tab_background':'#201e1a',
        'inactive_tab_foreground':'#716c62','inactive_tab_background':'#e8e1d4',
        'background_opacity':'1.0','background_blur':'0','cursor_trail':'0',
        'colors':('#201e1a','#963e39','#386348','#806023','#315a80','#755272','#28636b','#53514a',
                  '#716c62','#a03f38','#306a47','#846224','#285f88','#785076','#246773','#171714'),
        'accents':{81:'#28636b',117:'#315a80',150:'#386348',180:'#806023',183:'#755272',
                   110:'#315a80',211:'#963e69',245:'#716c62'}},
    'slate':{
        'background':'#11110f','foreground':'#f0eee7','cursor':'#d6b36a','cursor_text_color':'#11110f',
        'selection_background':'#393b3c','selection_foreground':'#f0eee7','url_color':'#8bc0cb',
        'active_tab_foreground':'#11110f','active_tab_background':'#d6b36a',
        'inactive_tab_foreground':'#aaa49a','inactive_tab_background':'#242421',
        'background_opacity':'1.0','background_blur':'0','cursor_trail':'0',
        'colors':('#151514','#c47b76','#91b38a','#d6b36a','#92aecb','#b39abc','#8bbabd','#dedbd3',
                  '#827f76','#dc9690','#adcba5','#e4c88c','#b0c7df','#ccb4d4','#aad2d5','#f0eee7')}
}
DESCRIPTIONS={'neon':'Green phosphor · current LOOK colors',
              'paper':'MercuryWriter paper · warm white and dark ink',
              'slate':'Quiet charcoal · warm ink and restrained accents'}
INCLUDE='globinclude look-theme.conf'
PERSONAL='globinclude kitty-local.conf'


def directory():
    return Path(os.environ.get('KITTY_CONFIG_DIRECTORY') or
                Path(os.environ.get('XDG_CONFIG_HOME') or Path.home()/'.config')/'kitty').expanduser()


def settings(name):
    theme=THEMES[name]
    result={key:value for key,value in theme.items() if key not in {'colors','accents'}}
    result.update({'color'+str(index):color for index,color in enumerate(theme['colors'])})
    result.update({'color'+str(index):color for index,color in theme.get('accents',{}).items()})
    return result


def write_file(path,data):
    temporary=path.with_name('.'+path.name+'-'+uuid.uuid4().hex)
    try:
        temporary.write_text(data,encoding='utf-8');temporary.replace(path)
    finally: temporary.unlink(missing_ok=True)


def select_theme(name,folder):
    if name not in (*THEMES,'reset'): raise ValueError('Unknown palette')
    config=folder/'kitty.conf'
    if not config.is_file(): raise ValueError('No Kitty config here; run ./install.sh --kitty first')
    before=config.read_text(encoding='utf-8')
    lines=before.splitlines(keepends=True)
    if not any(line.strip()==INCLUDE for line in lines):
        index=next((index for index,line in enumerate(lines) if line.strip()==PERSONAL),len(lines))
        # Add one appearance include, keeping local overrides last and all key maps.
        if index and not lines[index-1].endswith('\n'): lines[index-1]+='\n'
        lines.insert(index,INCLUDE+'\n')
        backup=config.with_name('kitty.conf.before-look-theme-'+uuid.uuid4().hex[:8])
        if config.is_symlink(): backup.symlink_to(config.readlink())
        else: shutil.copy2(config,backup)
        write_file(config,''.join(lines))
    theme=folder/'look-theme.conf'
    text='# LOOK palette: '+name+'\n'
    if name!='reset': text+=''.join(key+' '+value+'\n' for key,value in settings(name).items())
    if theme.is_file() and theme.read_text(encoding='utf-8')==text: return theme
    if theme.is_file():
        shutil.copy2(theme,theme.with_name('look-theme.conf.before-'+uuid.uuid4().hex[:8]))
    write_file(theme,text)
    return theme


def reload_kitty():
    value=os.environ.get('KITTY_PID','')
    if not value.isdecimal() or int(value)<=1: return False
    try:
        process=subprocess.run(['ps','-p',value,'-o','comm='],capture_output=True,text=True,timeout=2,check=True)
        if Path(process.stdout.strip()).name.lower()!='kitty': return False
        os.kill(int(value),signal.SIGUSR1)
        return True
    except (OSError,subprocess.SubprocessError): return False


def kitty_executable():
    executable=shutil.which('kitty')
    if executable: return executable
    for candidate in (Path('/Applications/kitty.app/Contents/MacOS/kitty'),
                      Path.home()/'Applications/kitty.app/Contents/MacOS/kitty'):
        if candidate.is_file(): return str(candidate)
    raise ValueError('Kitty is not installed')


def main(argv=None):
    parser=argparse.ArgumentParser(prog='lk terminal',description='Local Kitty palettes; existing fonts, keys, and shell remain yours.')
    commands=parser.add_subparsers(dest='action')
    theme=commands.add_parser('theme',help='Persist a palette; reset restores the underlying config')
    theme.add_argument('name',choices=(*THEMES,'reset'))
    launch=commands.add_parser('launch',help='Launch a separate Kitty window with a palette, without changing config')
    launch.add_argument('name',choices=tuple(THEMES))
    args=parser.parse_args(argv)
    try:
        if args.action=='theme':
            path=select_theme(args.name,directory())
            print('Kitty palette: '+args.name)
            print('Applied to current Kitty.' if reload_kitty() else 'Reload Kitty with Ctrl-Shift-F5, or reopen it.')
            print('Personal overrides in kitty-local.conf still apply.')
        elif args.action=='launch':
            command=[kitty_executable()]
            for key,value in settings(args.name).items(): command+=['--override',key+'='+value]
            subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            print('Opened Kitty · '+args.name)
        else:
            current=directory()/'look-theme.conf'
            print('LOOK TERMINAL · Kitty')
            for name in THEMES: print('  '+name+' · '+DESCRIPTIONS[name])
            print('  reset · restore existing Kitty appearance')
            if current.is_file():
                lines=current.read_text().splitlines()
                if lines: print(lines[0].removeprefix('# '))
            print('lk terminal theme NAME · lk terminal launch NAME')
        return 0
    except (OSError,ValueError) as exc:
        print('LOOK TERMINAL · '+str(exc),file=sys.stderr);return 1


if __name__=='__main__': raise SystemExit(main())
