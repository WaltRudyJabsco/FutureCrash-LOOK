"""Small, local Kitty palette controls. User fonts, keys, and shell stay owned."""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import termios
import tty
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
        'selection_background':'#f3d76a','selection_foreground':'#201e1a','url_color':'#193a5a',
        'active_tab_foreground':'#f6f1e7','active_tab_background':'#201e1a',
        'inactive_tab_foreground':'#716c62','inactive_tab_background':'#e8e1d4',
        'background_opacity':'1.0','background_blur':'0','cursor_trail':'0',
        'colors':('#201e1a','#7d302c','#b8d3af','#e4c67d','#193a5a','#593c64','#1e4f56','#ded8cd',
                  '#59554e','#87372f','#28583b','#705015','#213f65','#624060','#22545a','#171714'),
        'accents':{75:'#193a5a',81:'#1e4f56',114:'#254f38',117:'#193a5a',150:'#254f38',
                   176:'#593c64',180:'#6b4a19',183:'#593c64',203:'#7d302c',221:'#6b4a19',
                   110:'#193a5a',211:'#7d302c',244:'#59554e',245:'#59554e',252:'#201e1a'}},
    'slate':{
        'background':'#11110f','foreground':'#f0eee7','cursor':'#d6b36a','cursor_text_color':'#11110f',
        'selection_background':'#393b3c','selection_foreground':'#f0eee7','url_color':'#8bc0cb',
        'active_tab_foreground':'#11110f','active_tab_background':'#d6b36a',
        'inactive_tab_foreground':'#aaa49a','inactive_tab_background':'#242421',
        'background_opacity':'1.0','background_blur':'0','cursor_trail':'0',
        'colors':('#151514','#c47b76','#91b38a','#d6b36a','#92aecb','#b39abc','#8bbabd','#dedbd3',
                  '#827f76','#dc9690','#adcba5','#e4c88c','#b0c7df','#ccb4d4','#aad2d5','#f0eee7')}
}
NAMES=(*THEMES,'custom')
DESCRIPTIONS={'neon':'Green phosphor · current LOOK colors',
              'paper':'MercuryWriter paper · warm white and dark ink',
              'slate':'Quiet charcoal · warm ink and restrained accents',
              'custom':'Your editable style · lk terminal customize'}
INCLUDE='globinclude look-theme.conf'
PERSONAL='globinclude kitty-local.conf'


def directory():
    return Path(os.environ.get('KITTY_CONFIG_DIRECTORY') or
                Path(os.environ.get('XDG_CONFIG_HOME') or Path.home()/'.config')/'kitty').expanduser()


CUSTOM_DEFAULTS={'background':'#f6f1e7','foreground':'#201e1a','accent':'#193a5a',
                 'muted':'#59554e','green':'#254f38','red':'#7d302c','tabs':'#201e1a','selection':'#f3d76a'}
INKS=(('Black ink','#201e1a'),('Navy ink','#193a5a'),('Blue ink','#213f65'),
      ('Red ink','#7d302c'),('Green ink','#254f38'),('Violet ink','#593c64'),
      ('Brown ink','#6b4a19'),('Slate ink','#59554e'),('Amber','#a65c1a'))
LIGHT_INKS=(('White','#fafafa'),('Warm white','#f6f1e7'),('Sky','#9fc5e8'),
            ('Mint','#a5d6b3'),('Rose','#e1a4a0'),('Gold','#d6b36a'),('Yellow highlighter','#f3d76a'))
PAPERS=(('Mercury paper','#f6f1e7'),('Albert paper','#f3efe3'),('White','#fafafa'),
        ('Cool white','#eef1f4'),('Charcoal','#11110f'))


def custom_roles(folder):
    roles=dict(CUSTOM_DEFAULTS);path=folder/'look-custom.json'
    if path.is_file():
        data=json.loads(path.read_text())
        if not isinstance(data,dict): raise ValueError('Custom colors must be an object')
        for key in roles:
            if key in data:
                if not isinstance(data[key],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',data[key]):
                    raise ValueError('Invalid custom color: '+key)
                roles[key]=data[key].lower()
    return roles


def luminance(color):
    channels=[int(color[index:index+2],16)/255 for index in (1,3,5)]
    linear=[value/12.92 if value<=.04045 else ((value+.055)/1.055)**2.4 for value in channels]
    return sum(weight*value for weight,value in zip((.2126,.7152,.0722),linear))


def contrast(first,second):
    light,dark=sorted((luminance(first),luminance(second)),reverse=True)
    return (light+.05)/(dark+.05)


def readable_text(background):
    # Pick the stronger contrast for selected rows and terminal tabs.
    light=luminance(background)
    return '#000000' if (light+.05)/.05 >= 1.05/(light+.05) else '#ffffff'


def settings(name,folder=None):
    if name=='custom':
        roles=custom_roles(folder if folder is not None else directory())
        result=settings('paper' if luminance(roles['background'])>.4 else 'slate')
        result.setdefault('color221',result['color3'])
        result.setdefault('color176',result['color5'])
        result.update({key:roles[key] for key in ('background','foreground')})
        result.update(cursor=roles['foreground'],cursor_text_color=roles['background'],
                      url_color=roles['accent'],selection_background=roles['selection'],
                      selection_foreground=readable_text(roles['selection']),
                      active_tab_background=roles['tabs'],active_tab_foreground=readable_text(roles['tabs']),
                      inactive_tab_background=roles['background'],inactive_tab_foreground=roles['muted'])
        for index in (4,6,12,14,75,81,110,117):result['color'+str(index)]=roles['accent']
        # Keep ANSI panel backgrounds distinct from LOOK text inks.
        result['color252']=roles['foreground']
        for index in (8,244,245):result['color'+str(index)]=roles['muted']
        for index in (10,114,150):result['color'+str(index)]=roles['green']
        for index in (1,9,203,211):result['color'+str(index)]=roles['red']
        return result
    theme=THEMES[name]
    result={key:value for key,value in theme.items() if key not in {'colors','accents'}}
    result.update({'color'+str(index):color for index,color in enumerate(theme['colors'])})
    result.update({'color'+str(index):color for index,color in theme.get('accents',{}).items()})
    return result


def application_colors():
    """Coordinate explicit LOOK RGB colors with Paper and the one custom style."""
    name=os.environ.get('LOOK_TERMINAL_THEME','')
    if not name:
        try:
            first=(directory()/'look-theme.conf').read_text().splitlines()[0]
            name=first.removeprefix('# LOOK palette: ')
        except (OSError,IndexError): return {}
    if name not in {'paper','custom'}: return {}
    try:palette=settings(name)
    except (OSError,ValueError):palette=settings('paper')
    roles={'BLUE':'color75','CYAN':'color81','GREEN':'color114','YELLOW':'color221',
           'MAGENTA':'color176','RED':'color203','WHITE':'foreground','GRAY':'color8','FAINT':'color8',
           'ACTIVE_BG':'selection_background','ACTIVE_FG':'selection_foreground'}
    return {role:tuple(int(palette[key][index:index+2],16) for index in (1,3,5))
            for role,key in roles.items()}


def write_file(path,data):
    temporary=path.with_name('.'+path.name+'-'+uuid.uuid4().hex)
    try:
        temporary.write_text(data,encoding='utf-8');temporary.replace(path)
    finally: temporary.unlink(missing_ok=True)


def select_theme(name,folder):
    if name not in (*NAMES,'reset'): raise ValueError('Unknown palette')
    chosen=settings(name,folder) if name!='reset' else {}
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
    if name!='reset': text+=''.join(key+' '+value+'\n' for key,value in chosen.items())
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


def preset_roles(name,folder):
    palette=settings(name,folder)
    mapping={'background':'background','foreground':'foreground','accent':'url_color',
             'muted':'color8','green':'color114' if 'color114' in palette else 'color2',
             'red':'color203' if 'color203' in palette else 'color1',
             'tabs':'active_tab_background','selection':'selection_background'}
    return {role:palette[key] for role,key in mapping.items()}


def customize(read_key,folder,base=None):
    if read_key is None or not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise ValueError('Open the selector in a terminal with lk terminal customize')
    if not (folder/'kitty.conf').is_file(): raise ValueError('No Kitty config here; run ./install.sh --kitty first')
    values=preset_roles(base,folder) if base else custom_roles(folder);roles=list(values);selected=0;choice=0;choosing=False;notice=''
    labels={'background':'Paper / background','foreground':'Text ink','accent':'Blue / accent ink',
            'muted':'Muted text','green':'Green pen ink','red':'Red pen ink','tabs':'Active tab','selection':'Selection / highlighter'}
    fd=sys.stdin.fileno();old=termios.tcgetattr(fd)
    try:
        from .look_renderer import fit
    except ImportError:
        from look_renderer import fit
    try:
        tty.setcbreak(fd);sys.stdout.write('\033[?25l')
        while True:
            width,height=shutil.get_terminal_size((100,30));page=max(1,height-9)
            role=roles[selected];options=PAPERS if role=='background' else INKS+LIGHT_INKS
            lines=['LOOK CUSTOM STYLE · '+(base+' → custom' if base else 'one editable style')]
            if choosing:
                lines.append(labels[role]+' · choose a color')
                top=max(0,choice-page+1)
                for index,(name,color) in enumerate(options[top:top+page],top):
                    r,g,b=(int(color[pos:pos+2],16) for pos in (1,3,5))
                    lines.append(('› ' if index==choice else '  ')+f'\033[48;2;{r};{g};{b}m  \033[0m '+name+' '+color)
            else:
                top=max(0,selected-page+1)
                for index,key in enumerate(roles[top:top+page],top):
                    r,g,b=(int(values[key][pos:pos+2],16) for pos in (1,3,5))
                    lines.append(('› ' if index==selected else '  ')+f'\033[48;2;{r};{g};{b}m  \033[0m '+labels[key]+' '+values[key])
            br,bg,bb=(int(values['background'][pos:pos+2],16) for pos in (1,3,5))
            ir,ig,ib=(int(values['foreground'][pos:pos+2],16) for pos in (1,3,5))
            lines+=[f'\033[48;2;{br};{bg};{bb}m\033[38;2;{ir};{ig};{ib}m  LOOK  ~/Project  · notes.md  \033[0m',
                    '↑↓ move · Enter choose · S save/apply · Esc back/cancel',notice]
            def sample(color,text,background=values['background']):
                r,g,b=(int(color[pos:pos+2],16) for pos in (1,3,5))
                br,bg,bb=(int(background[pos:pos+2],16) for pos in (1,3,5))
                return f'\033[48;2;{br};{bg};{bb}m\033[38;2;{r};{g};{b}m{text}\033[0m'
            lines[-2:-2]=[sample(values['red'],' Red pen ')+sample(values['green'],' Green pen '),
                           sample(readable_text(values['selection']),' Selected notes.md ',values['selection'])]
            sys.stdout.write('\033[2J\033[H'+'\n'.join(fit(line,max(1,width-1)) for line in lines)+'\033[J');sys.stdout.flush()
            key=read_key(fd,None);notice=''
            if key in {'esc','q','\x03'}:
                if choosing:choosing=False;continue
                return False
            if key=='down':
                if choosing:choice=min(len(options)-1,choice+1)
                else:selected=min(len(roles)-1,selected+1)
            elif key=='up':
                if choosing:choice=max(0,choice-1)
                else:selected=max(0,selected-1)
            elif key in {'\r','\n','enter','right'}:
                if choosing:values[role]=options[choice][1];choosing=False
                else:
                    choosing=True;choice=next((index for index,(_,color) in enumerate(options) if color==values[role]),0)
            elif key in {'s','S'}:
                poor=[labels[key] for key in ('foreground','accent','muted','green','red')
                      if contrast(values['background'],values[key])<4.5]
                if poor:
                    notice='Increase contrast against background: '+', '.join(poor);continue
                path=folder/'look-custom.json'
                if path.is_file():shutil.copy2(path,path.with_name('look-custom.json.before-'+uuid.uuid4().hex[:8]))
                write_file(path,json.dumps(values,indent=2)+'\n')
                select_theme('custom',folder);reload_kitty()
                return True
    finally:
        termios.tcsetattr(fd,termios.TCSADRAIN,old)
        sys.stdout.write('\033[?25h\033[0m');sys.stdout.flush()


def choose_theme(read_key):
    """Return a palette and whether to edit it; leave persistence to the caller."""
    selected=0;names=(*NAMES,'reset');fd=sys.stdin.fileno();old=termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd);sys.stdout.write('\033[?25l')
        while True:
            lines=['LOOK TERMINAL · choose a style']
            for index,name in enumerate(names):
                label=DESCRIPTIONS.get(name,'Restore your underlying Kitty appearance')
                lines.append(('› ' if index==selected else '  ')+name+' · '+label)
            lines.append('↑↓ move · Enter apply · E fine-tune into Custom · Esc cancel')
            sys.stdout.write('\033[2J\033[H'+'\n'.join(lines)+'\033[J');sys.stdout.flush()
            key=read_key(fd,None)
            if key=='down':selected=min(len(names)-1,selected+1)
            elif key=='up':selected=max(0,selected-1)
            elif key in {'esc','q','\x03'}:return None
            elif key in {'\r','\n','enter'}:return names[selected],False
            elif key in {'e','E'} and names[selected]!='reset':return names[selected],True
    finally:
        termios.tcsetattr(fd,termios.TCSADRAIN,old)
        sys.stdout.write('\033[?25h\033[0m');sys.stdout.flush()


def main(argv=None,read_key=None):
    parser=argparse.ArgumentParser(prog='lk terminal',description='Local Kitty palettes; existing fonts, keys, and shell remain yours.')
    commands=parser.add_subparsers(dest='action')
    theme=commands.add_parser('theme',help='Persist a palette; reset removes the LOOK overlay and restores your underlying Kitty appearance')
    theme.add_argument('name',choices=(*NAMES,'reset'))
    launch=commands.add_parser('launch',help='Launch a separate Kitty window with a palette, without changing config')
    launch.add_argument('name',choices=NAMES)
    custom=commands.add_parser('customize',help='Edit custom or start from a preset; saves as custom')
    custom.add_argument('base',nargs='?',choices=tuple(THEMES),help='Preset to fine-tune into custom')
    args=parser.parse_args(argv)
    try:
        if args.action=='theme':
            path=select_theme(args.name,directory())
            print('Kitty palette: '+args.name)
            print('Applied to current Kitty.' if reload_kitty() else 'Reload Kitty with Ctrl-Shift-F5, or reopen it.')
            print('Personal overrides in kitty-local.conf still apply.')
        elif args.action=='launch':
            command=[kitty_executable()]
            command+=['--override','env=LOOK_TERMINAL_THEME='+args.name]
            for key,value in settings(args.name).items(): command+=['--override',key+'='+value]
            subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            print('Opened Kitty · '+args.name)
        elif args.action=='customize':
            print('Custom style saved. Reload/reopen LOOK to refresh its text colors.' if customize(read_key,directory(),args.base) else 'Custom style unchanged.')
        elif read_key and sys.stdin.isatty() and sys.stdout.isatty():
            picked=choose_theme(read_key)
            if picked:
                name,edit=picked
                if edit:
                    saved=customize(read_key,directory(),None if name=='custom' else name)
                    print('Custom style saved. Reopen LOOK to refresh its text colors.' if saved else 'Custom style unchanged.')
                else:
                    select_theme(name,directory())
                    print('Kitty palette: '+name)
                    print('Applied to current Kitty.' if reload_kitty() else 'Reload Kitty with Ctrl-Shift-F5, or reopen it.')
        else:
            current=directory()/'look-theme.conf'
            print('LOOK TERMINAL · Kitty')
            for name in NAMES: print('  '+name+' · '+DESCRIPTIONS[name])
            print('  reset · remove LOOK theme overlay; restore your existing Kitty appearance')
            if current.is_file():
                lines=current.read_text().splitlines()
                if lines: print(lines[0].removeprefix('# '))
            print('lk terminal theme NAME · lk terminal launch NAME · lk terminal customize')
        return 0
    except (OSError,ValueError) as exc:
        print('LOOK TERMINAL · '+str(exc),file=sys.stderr);return 1


if __name__=='__main__': raise SystemExit(main())
