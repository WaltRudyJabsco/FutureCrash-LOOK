"""LOOK saver configuration, scene scheduling, and terminal picker.

The graphical edge lives in saver_gui; importing this module never opens a display
or installs software. Saver preferences are independent of the music player.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import termios
import time
import tty

import book_reader
import player_visuals
import terminal_style

SCHEMA=1
MAX_SETTINGS_BYTES=65536
MIN_INTERVAL=5
MAX_INTERVAL=600
DEFAULT_INTERVAL=20
QT_PACKAGE='PySide6-Essentials==6.10.3'
SCENES=tuple(name for name in player_visuals.NAMES if name not in {'Cycle','Album Art'})
PALETTES=('auto',*terminal_style.THEMES)


def settings_path():return Path.home()/'.config/look/saver.json'
def runtime_path():return Path.home()/'.local/share/look/saver-runtime/bin/python'


def defaults():
    return dict(schema=SCHEMA,scene='cycle',enabled=list(SCENES),display='all',
                interval=DEFAULT_INTERVAL,palette='auto',independent=True,inversions=True)


def scene_name(value):
    normalized=str(value).strip().casefold().replace('-',' ')
    if normalized=='cycle':return 'cycle'
    for name in SCENES:
        if name.casefold()==normalized:return name
    raise ValueError('Unknown screensaver: '+str(value)+' · use lk saver list')


def validate(value):
    if not isinstance(value,dict) or value.get('schema',SCHEMA)!=SCHEMA:
        raise ValueError('Unsupported saver settings')
    result={**defaults(),**value}
    result['scene']=scene_name(result['scene'])
    enabled=result['enabled']
    if not isinstance(enabled,list) or len(enabled)>len(SCENES) or any(name not in SCENES for name in enabled):
        raise ValueError('Invalid enabled screensavers')
    result['enabled']=list(dict.fromkeys(enabled))
    if result['display'] not in {'all','current'}:raise ValueError('Display must be all or current')
    if result['palette'] not in PALETTES:raise ValueError('Unknown saver palette')
    interval=result['interval']
    if isinstance(interval,bool) or not isinstance(interval,(int,float)) or not math.isfinite(interval) or not MIN_INTERVAL<=interval<=MAX_INTERVAL:
        raise ValueError(f'Cycle interval must be {MIN_INTERVAL}–{MAX_INTERVAL} seconds')
    for key in ('independent','inversions'):
        if not isinstance(result[key],bool):raise ValueError('Invalid '+key+' setting')
    return result


def load():
    try:
        with settings_path().open('rb') as source:raw=source.read(MAX_SETTINGS_BYTES+1)
    except FileNotFoundError:return defaults()
    if len(raw)>MAX_SETTINGS_BYTES:raise ValueError('Saver settings exceed 64 KiB')
    return validate(json.loads(raw))


def save(settings):book_reader.write_json(settings_path(),validate(settings))


class SceneRun:
    """A stable scene/color per interval; no per-frame randomness or flashing."""
    def __init__(self,settings,seed):
        self.settings=validate(settings)
        self.rng=random.Random(seed)
        self.seed=self.rng.randrange(100000)
        self.scenes=list(self.settings['enabled']) if self.settings['scene']=='cycle' else [self.settings['scene']]
        if not self.scenes:raise ValueError('Enable at least one screensaver for Cycle')
        self.rng.shuffle(self.scenes)
        self.step=None;self.style=None
        self.inverse_rows=set();self.captions=None
        self.color_revision=0;self.scene_offset=0;self.timeline_step=0
        self.cycling=self.settings['scene']=='cycle'
        self.offset=self.rng.random()*self.settings['interval'] if self.settings['independent'] else 0

    def next_color(self):
        self.color_revision+=1
        self.step=None

    def copy_controls_from(self,other):
        self.color_revision=other.color_revision
        self.scene_offset=other.scene_offset
        self.scenes=list(other.scenes);self.cycling=other.cycling
        self.step=None

    def next_scene(self,elapsed=None):
        if elapsed is not None:self.timeline_step=int(max(0,elapsed+self.offset)//self.settings['interval'])
        if not self.cycling:
            current=self.scenes[0]
            self.scenes=[name for name in SCENES if name in self.settings['enabled'] or name==current]
            self.scene_offset=self.scenes.index(current)-self.timeline_step
            self.cycling=True
        self.scene_offset+=1
        self.next_color()

    def sample(self,elapsed,width,height):
        step=int(max(0,elapsed+self.offset)//self.settings['interval'])
        self.timeline_step=step
        if step!=self.step:
            pairs=[]
            palettes=terminal_style.THEMES.values() if self.settings['palette']=='auto' else [terminal_style.THEMES[self.settings['palette']]]
            for palette in palettes:
                for ink in palette['colors'][9:15]:
                    paper=palette['background']
                    if terminal_style.contrast(paper,ink)>=4.5:pairs.append((paper,ink))
            # Matching displays stay synchronized even if one misses a paint.
            step_rng=random.Random(self.seed+step)
            pairs=list(dict.fromkeys(pairs))
            paper,ink=pairs[(step_rng.randrange(len(pairs))+self.color_revision)%len(pairs)]
            if self.settings['inversions'] and step_rng.randrange(5)==0:paper,ink=ink,paper
            self.style=(paper,ink);self.step=step
        scene=self.scenes[(step+self.scene_offset)%len(self.scenes)]
        phase=elapsed+self.offset
        lines=player_visuals.frame(player_visuals.NAMES.index(scene)+1,width,height,phase,True,self.seed,captions=self.captions)
        self.inverse_rows=player_visuals.flight_deck_inverse_rows(height,phase) if scene=='Flight Deck' else set()
        return scene,lines,self.style


def interpreter():
    if importlib.util.find_spec('PySide6') is not None:return Path(sys.executable)
    candidate=runtime_path()
    if candidate.is_file():
        result=subprocess.run([str(candidate),'-c','from PySide6 import QtWidgets'],capture_output=True,timeout=15)
        if result.returncode==0:return candidate
    return None


def setup():
    """Explicit installation into an isolated user environment, never system Python."""
    runtime=runtime_path();folder=runtime.parent.parent
    print(f'Install {QT_PACKAGE} in {folder}\nExisting LOOK settings and system Python are preserved.',flush=True)
    if folder.is_symlink():raise ValueError('Saver runtime directory must not be a symbolic link')
    folder.parent.mkdir(parents=True,exist_ok=True)
    if not runtime.is_file():subprocess.run([sys.executable,'-m','venv',str(folder)],check=True)
    subprocess.run([str(runtime),'-m','pip','install',QT_PACKAGE],check=True)
    subprocess.run([str(runtime),'-c','from PySide6 import QtWidgets'],check=True)
    print('Saver graphics ready · lk sv starts your saved selection')
    return 0


def launch(settings,*,preview=False,seconds=None):
    settings=validate(settings)
    if settings['scene']=='cycle' and not settings['enabled']:
        raise ValueError('Enable at least one screensaver for Cycle')
    executable=interpreter()
    if executable is None:raise ValueError('Graphics runtime not installed · run lk saver setup (isolated Qt runtime)')
    if sys.platform.startswith('linux') and not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY') or os.environ.get('QT_QPA_PLATFORM')=='offscreen'):
        raise ValueError('Start lk sv from a graphical desktop session on this computer')
    payload=dict(settings=settings,preview=preview,seconds=seconds)
    result=subprocess.run([str(executable),str(Path(__file__).with_name('saver_gui.py'))],input=json.dumps(payload),text=True)
    return result.returncode


def picker(ui):
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        for name in ('cycle',*SCENES):print(name)
        print('Start: lk sv [NAME] · setup: lk saver setup');return 0
    settings=load();names=('cycle',*SCENES);index=names.index(settings['scene'])
    fd=sys.stdin.fileno();old=termios.tcgetattr(fd)
    notice='Enter starts · A saves · Preview leaves settings unchanged'
    last_preview=None;preview=None;started=time.monotonic()
    try:
        tty.setcbreak(fd);sys.stdout.write('\033[?25l')
        while True:
            width,height=ui.shutil.get_terminal_size((90,30));width=max(20,width)
            controls=ui._media_hints('↑↓ select · Shift-arrows page/ends · Space enable · P preview · Enter start · A save · D displays · M matching/independent · C colors · I invert · -/+ interval · G setup graphics · q/Esc back',width).splitlines()
            page=max(1,height-len(controls)-8);index=max(0,min(index,len(names)-1));top=(index//page)*page
            selected=names[index];settings['scene']=selected
            signature=(selected,tuple(settings['enabled']),settings['palette'],settings['inversions'],settings['interval'])
            if signature!=last_preview:
                try:preview=SceneRun(settings,17)
                except ValueError:preview=None
                last_preview=signature;started=time.monotonic()
            preview_width=min(60,width//2) if width>=90 else 0
            preview_lines=preview.sample(time.monotonic()-started,preview_width,page)[1] if preview and preview_width else []
            left_width=width-preview_width-3 if preview_width else width
            frame=[ui._c('LOOK SAVER','1;36')+' · ambient visuals · Escape dismisses',
                   f"Displays: {settings['display']} · {'independent' if settings['independent'] else 'matching'} scenes",
                   f"Colors: {settings['palette']} · inversions: {'occasional' if settings['inversions'] else 'off'} · {settings['interval']:g}s per scene"]
            colors=terminal_style.list_colors()
            for line in range(page):
                position=top+line
                if position<len(names):
                    name=names[position];mark='↻' if name=='cycle' else ('✓' if name in settings['enabled'] else ' ')
                    label=f'{mark} {name}'
                    left=terminal_style.list_row(label,left_width,position,position==index,colors)
                else:left=' '*left_width
                left+=' '*max(0,left_width-len(ui._strip_ansi(left)))
                right=ui._c(preview_lines[line],'36') if line<len(preview_lines) else ''
                frame.append(left+(' │ '+right if preview_width else ''))
            frame.extend(['',ui._c(notice,'33'),*controls])
            rendered='\n'.join(ui._ansi_clip(line,width) for line in frame[:height])
            sys.stdout.write(ui._terminal_frame_payload(rendered));sys.stdout.flush()
            key=ui._read_tty_key(fd,.12)
            if key in {'esc','q','\x03'}:return 0
            if key=='up':index-=1
            elif key=='down':index+=1
            elif key in {'pageup','shiftup'}:index-=page
            elif key in {'pagedown','shiftdown'}:index+=page
            elif key in {'home','shiftleft'}:index=0
            elif key in {'end','shiftright'}:index=len(names)-1
            elif key==' ' and selected!='cycle':
                if selected in settings['enabled']:settings['enabled'].remove(selected)
                else:settings['enabled'].append(selected)
            elif key in {'a','A'}:
                try:save(settings);notice='Saved · lk sv will use this selection'
                except (OSError,ValueError) as exc:notice=str(exc)
            elif key in {'d','D'}:settings['display']='current' if settings['display']=='all' else 'all'
            elif key in {'m','M'}:settings['independent']=not settings['independent']
            elif key in {'c','C'}:settings['palette']=PALETTES[(PALETTES.index(settings['palette'])+1)%len(PALETTES)]
            elif key in {'i','I'}:settings['inversions']=not settings['inversions']
            elif key in {'+','='}:settings['interval']=min(MAX_INTERVAL,settings['interval']+5)
            elif key=='-':settings['interval']=max(MIN_INTERVAL,settings['interval']-5)
            elif key in {'p','P','enter','\r','\n','g','G'}:
                termios.tcsetattr(fd,termios.TCSADRAIN,old);sys.stdout.write('\033[?25h\033[0m');sys.stdout.flush()
                try:
                    if key in {'g','G'}:
                        print(f'Install {QT_PACKAGE} into {runtime_path().parent.parent}?')
                        if input('Install isolated graphics runtime? [y/N] ').strip().casefold()=='y':setup();notice='Graphics runtime ready'
                    else:
                        code=launch(settings,preview=key in {'p','P'})
                        notice='Back from saver · A saves this selection' if code==0 else 'Graphics could not start · run lk sv from your desktop for details'
                except (OSError,ValueError,subprocess.SubprocessError) as exc:notice=str(exc)
                finally:tty.setcbreak(fd);sys.stdout.write('\033[?25l')
    finally:
        termios.tcsetattr(fd,termios.TCSADRAIN,old)
        sys.stdout.write('\033[0m\033[?25h\033[2J\033[H');sys.stdout.flush()


def main(args,*,ui=None,quick=False):
    parser=argparse.ArgumentParser(prog='lk sv' if quick else 'lk saver',description='Ambient multi-display screensavers. Escape dismisses; this does not lock the computer.')
    parser.add_argument('selection',nargs='*',help='scene name, cycle, start, list, setup, or text [reset]')
    parser.add_argument('--display',choices=('all','current'),help='current means the display under the pointer at launch')
    parser.add_argument('--interval',type=float,help='seconds per scene, 5–600')
    parser.add_argument('--palette',choices=PALETTES)
    parser.add_argument('--matching',action='store_true',help='matching scenes and colors across displays')
    parser.add_argument('--independent',action='store_true',help='independent scenes and colors across displays')
    parser.add_argument('--invert',action=argparse.BooleanOptionalAction,default=None,help='occasional inverted colors')
    parser.add_argument('--preview',action='store_true',help='open a small graphical preview')
    parser.add_argument('--seconds',type=float,help='dismiss automatically after this many seconds')
    parser.add_argument('--save',action='store_true',help='save supplied settings without launching')
    options=parser.parse_args(args)
    try:
        selection=options.selection
        if selection and selection[0]=='start':selection=selection[1:]
        action=' '.join(selection)
        if action=='list':
            print('\n'.join(('cycle',*SCENES)));return 0
        if action=='setup':return setup()
        if action in {'text','text reset'}:
            import saver_text
            return saver_text.reset() if action=='text reset' else saver_text.generate()
        if not args and not quick:
            if ui is None:raise ValueError('Picker needs the LOOK terminal interface')
            return picker(ui)
        settings=load()
        if action and action!='start':settings['scene']=scene_name(action)
        for key in ('display','interval','palette'):
            if getattr(options,key) is not None:settings[key]=getattr(options,key)
        if options.matching and options.independent:raise ValueError('Choose matching or independent displays')
        if options.matching:settings['independent']=False
        if options.independent:settings['independent']=True
        if options.invert is not None:settings['inversions']=options.invert
        if options.seconds is not None and (not math.isfinite(options.seconds) or not 0<options.seconds<=86400):raise ValueError('Seconds must be positive and at most 86400')
        settings=validate(settings)
        if options.save:save(settings);print('Saver settings saved');return 0
        return launch(settings,preview=options.preview,seconds=options.seconds)
    except (OSError,ValueError,RuntimeError,ImportError,subprocess.SubprocessError) as exc:
        print('LOOK SAVER · '+str(exc),file=sys.stderr);return 1
