#!/usr/bin/env python3
"""Build reference surfaces without importing LK or running any command.

Registry supplies descriptions; dispatch AST supplies otherwise missing entry
points; live help and usage messages preserve subcommand/option detail.
"""
import argparse
import ast
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def string(node, version):
    if isinstance(node,ast.Constant) and isinstance(node.value,str): return node.value
    if isinstance(node,ast.JoinedStr):
        return ''.join(part.value if isinstance(part,ast.Constant) else version if isinstance(part.value,ast.Name) and part.value.id=='VERSION' else '{'+ast.unparse(part.value)+'}' for part in node.values)
    return ''


def collect(root=ROOT):
    source=(root/'look/lk').read_text(); tree=ast.parse(source)
    registry=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_COMMANDS' for t in n.targets))
    version=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='VERSION' for t in n.targets))
    help_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='help_screen')
    help_text=next(string(n.value,version) for n in help_node.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='body' for t in n.targets))
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    routes=set()
    for n in ast.walk(main):
        if not isinstance(n,ast.Compare) or not n.comparators: continue
        left=ast.unparse(n.left)
        if left not in {'cmd','sys.argv[1]'}: continue
        right=n.comparators[0]
        values=[right] if isinstance(right,ast.Constant) else right.elts if isinstance(right,(ast.Set,ast.Tuple,ast.List)) else []
        routes.update(v.value for v in values if isinstance(v,ast.Constant) and isinstance(v.value,str) and not v.value.startswith(('_','-')))
    registered={item[0].split()[1] for item in registry if item[0].startswith('lk ')}
    forms=list(registry)
    for command in sorted(routes-registered):
        forms.append((f'lk {command}','[ARGS]','aliases','Additional routed entry point; see usage details below'))
    usages={}
    options={}
    for relative in ['look/lk','look/look_renderer.py','look/ytd.py','look/games.py','look/notebook.py','look/disc_ui.py']:
        parsed=ast.parse((root/relative).read_text())
        lines=set(); flags=set()
        for n in ast.walk(parsed):
            # Printed usage, not comments/tests or arbitrary implementation strings.
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='print' and n.args:
                text=string(n.args[0],version)
                if text.lower().startswith('usage:'):
                    lines.add(text.rstrip())
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='add_argument':
                names=[a.value for a in n.args if isinstance(a,ast.Constant) and isinstance(a.value,str)]
                if names:
                    help_value=next((string(k.value,version) for k in n.keywords if k.arg=='help'),'')
                    flags.add(' / '.join(names)+(f' — {help_value}' if help_value else ''))
        for owner in parsed.body:
            if not isinstance(owner,ast.FunctionDef): continue
            recognized=set()
            for comparison in ast.walk(owner):
                if isinstance(comparison,ast.Compare):
                    recognized.update(token.value for token in ast.walk(comparison) if isinstance(token,ast.Constant) and isinstance(token.value,str) and token.value.startswith('--') and ' ' not in token.value)
            if recognized:
                flags.add(owner.name+': '+', '.join(sorted(recognized)))
        usages[relative]=sorted(lines)
        options[relative]=sorted(flags)
    known={row[0] for row in forms}
    categories={row[0].split()[1]:row[2] for row in registry if row[0].startswith('lk ')}
    for usage in usages['look/lk']:
        words=usage.removeprefix('usage:').strip().split()
        if not words or words[0]!='lk': continue
        stem=['lk']; index=1
        while index<len(words) and re.fullmatch(r'[a-z][a-z0-9_-]*',words[index]):
            stem.append(words[index]); index+=1
        command=' '.join(stem)
        if len(stem)<2 or command in known: continue
        arguments=' '.join(words[index:])
        arguments=re.sub(r'(?<![<\w])\b[A-Z][A-Z0-9_]*\b(?![>\w])',r'<\g<0>>',arguments)
        forms.append((command,arguments,categories.get(stem[1],'commands'),'See usage details and live glossary below'))
        known.add(command)
    return version,forms,help_text,usages,options


KEYS='''KEYBOARD SURFACES

Uppercase letters mean Shift + letter (R is Shift-R, D is Shift-D); lowercase
transport keys stay lowercase.
Key labels use cyan, ordinary labels are subdued; green indicates playback or
selection, amber indicates paused/partial/unavailable, purple indicates modes.
Colors supplement text and never carry the only indication of state.

LOOK files: H hidden, F sort, R rename, D delete, B desktop clipboard,
C Copy To, M Move To, T cut, P paste, L LO context, X clear working set,
Y path, G exit to directory. Hidden files default off; lh shows them.

Media Find: type filters or / enters search; ↑↓ or J/K move; Shift-↑↓ page; Shift-←→ ends;
Tab mark; A mark/unmark all visible; C clear selection; Enter/P play;
Q append queue; S save playlist; I info; V logical/all physical sources;
H hidden; X hide selected; D choose a containing directory to hide;
U remove matching hide rules; Esc finishes search, then clears query, then exits.
◆ is SHA identity and · is scanned identity; these are indicators, not keys.

LK MP: / enters search; Enter/Esc finish editing and retain the filter;
↑↓ or J/K select; Shift-↑↓ page; Shift-←→ ends; Tab mark;
A marks/unmarks all visible; C clears marks; Enter plays marks/current;
B appends marks/current to queue; D hides a directory;
L library; Q queue; space play/pause; ←/→ seek 10s; p/n previous/next;
s shuffle; r repeat; v opens visuals; x stop; Esc clears query then exits.
Both media screens allow arrows, Tab and selection actions during search.

LK Player: space play/pause; ←/→ seek 10s; p/n previous/next;
s shuffle; r repeat; v cycles six ambient visualizers, large ASCII album art, and normal view;
x stop; q/Esc closes the view while playback continues.
Visualizers are ambient animations, not measurements of decoded audio.

Destination picker: ← parent (above filesystem root shows Fabric nodes);
→ descend; Enter chooses the highlighted directory (not the current directory);
↑↓ selection; Shift-↑↓ pages; Shift-←→ first/last; type filters;
Backspace edits filter; Esc/Q cancels. On remote roots Tab toggles common/all;
inside remote directories Tab returns to common places. Local views have no Tab mode.
Destination prompt: Tab completes local/remote paths and recent destinations;
→/↓ opens picker; ← edits the line; quote spaces when entering shell commands:
lcp "video.mp4" "@3090:/run/media/jreno/2TB Storage/srv/media/video/"
@node:~/ expands on the destination node, not on the initiating Mac.

ff [WORDS]: recursive filename search under this node's home, not Fabric search.
Results fill in while discovery runs; H includes hidden paths. Enter returns
through the normal LOOK file view. fznv opens a selected file in Neovim.
lk find QUERY: catalog filename/path/metadata/description/supported content search
across reachable paired Fabric nodes, with local fallback. Remote-only results
currently offer a node-qualified path via Y; they do not silently fetch bytes.

LO input: ↑/↓ recalls prompt history; ←/→ edits text; Ctrl-D exits;
Ctrl-C cancels the current request. Browser/CarPlay controls use media transport;
terminal transport follows the active supported player.

Downloads: default permanent ~/Downloads/LOOK; --holding opts into 30-day
retention in ~/Downloads/LOOK-Holding. Ctrl-C detaches; cancel is explicit.
--detach returns immediately; --json returns a receipt, not completed video.
keep moves a held download and its sidecar together and clears expiry.
Neighboring .info.json holds searchable source metadata; MP4 playback itself
does not require it. Manual moves should keep both if descriptions matter.
Existing LOOK-owned Downloads/Pictures roots are discovered on each node at
watcher startup and every five minutes. Completed LOOK downloads index immediately.
Configured desktop media apps apply to LOOK opens; protected Apple media may
require an authorized Apple player. File extensions alone do not establish DRM.
'''


def outputs(root=ROOT):
    version,forms,help_text,usages,options=collect(root)
    intro=f'LOOK {version} — command and keyboard reference\n\nGenerated by tools/command_reference.py from the registry, dispatch, live help,\nprinted usage and argument parsers. Do not edit generated files by hand.\nThis covers executable LOOK entry points; optional external tools have their own manuals.\n\nlk help: starter map. lk commands: searchable forms. lk doc / lk help all:\nthis full reference. man lk: the same reference offline. tldr lk: short examples.\n\n'
    reference=intro+'COMMAND INDEX\n\n'
    for command,args,category,description,*alias in forms:
        reference+=(command+(' '+args if args else ''))+f'\n  [{category}] {description}'+(f' · alias: {alias[0]}' if alias else '')+'\n'
    reference+='\n'+KEYS+'\nLIVE GLOSSARY\n'+help_text+'\nUSAGE AND OPTIONS\n'
    for path,lines in usages.items():
        reference+=f'\n{path}\n'+ '\n'.join(lines)+'\n'
        if options[path]: reference+='Parser arguments and recognized option tokens (grouped by handler):\n'+'\n'.join(options[path])+'\n'
    grammar='# LOOK command grammar\n\nGenerated by `python3 tools/command_reference.py`. Full flags and keys: [reference](../look/docs/REFERENCE.md).\n\n| Command | Arguments | Area | Purpose |\n|---|---|---|---|\n'
    escape=lambda value:str(value).replace('|','\\|').replace('\n',' ')
    for command,args,area,desc,*alias in forms:
        grammar+='| `'+escape(command)+'` | `'+escape(args)+'` | '+escape(area)+' | '+escape(desc)+(f' · {escape(alias[0])}' if alias else '')+' |\n'
    roff='.TH LK 1 "October 2026" "LOOK '+version+' / Future Crash + LOOK '+(root/'VERSION').read_text().strip()+'" "User Commands"\n.SH NAME\nlk \\- LOOK file, media, AI and Fabric toolkit\n.SH REFERENCE\n.nf\n'
    for line in reference.splitlines():
        line=line.replace('\\','\\e')
        if line.startswith(('.',"'")): line='\\&'+line
        roff+=line+'\n'
    roff+='.fi\n'
    tldr='''# lk

> LOOK files, media, AI and Fabric toolkit.
> Full reference: `lk doc`, `lk help all`, or `man lk`.

- Open LOOK in a directory (hidden files default off):

`lk {{path/to/directory}}`

- Browse every command and compose one into the shell:

`lk commands`

- Search reachable Fabric catalogs:

`lk find {{words}}`

- Browse Fabric media or the integrated player:

`lk media find {{artist_or_title}}`

`lk mp {{query}}`

- Download a video on the storage node:

`lk ytd {{url}} --node {{3090}}`

- Inspect Fabric health and update options:

`lk fabric`

- Read the complete offline reference:

`lk doc`
'''
    command_help=command_help_pages(root,forms,usages)
    return {root/'look/docs/REFERENCE.md':reference,root/'docs/COMMAND-GRAMMAR.md':grammar,root/'look/lk.1':roff,root/'look/docs/command_forms.json':json.dumps(forms,ensure_ascii=False,indent=2)+'\n',root/'look/docs/command_help.json':json.dumps(command_help,ensure_ascii=False,indent=2)+'\n',root/'look/tldr/lk.md':tldr}


def command_help_pages(root,forms,usages):
    tree=ast.parse((root/'look/lk').read_text())
    functions={node.name:node for node in tree.body if isinstance(node,ast.FunctionDef)}
    handlers={}
    for block in ast.walk(functions['main']):
        if not isinstance(block,ast.If): continue
        commands=set()
        for comparison in ast.walk(block.test):
            if isinstance(comparison,ast.Compare) and isinstance(comparison.left,ast.Name) and comparison.left.id=='cmd':
                commands.update(node.value for node in ast.walk(comparison) if isinstance(node,ast.Constant) and isinstance(node.value,str))
        targets={node.value.func.id for statement in block.body for node in ast.walk(statement)
                 if isinstance(node,ast.Return) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name)}
        for command in commands: handlers.setdefault(command,set()).update(targets)
    grouped={}
    for command,args,area,description,*alias in forms:
        words=command.split(); name=words[1] if words[0]=='lk' and len(words)>1 else words[0]
        grouped.setdefault(name,[]).append(command+(' '+args if args else '')+'\n  '+description)
    pages={}
    for name,entries in grouped.items():
        parts=['LOOK HELP · '+name,'','COMMAND FORMS',*entries]
        usage=[line for lines in usages.values() for line in lines
               if line.startswith('usage: lk '+name+' ') or line.startswith('usage: '+name+' ')]
        if usage: parts.extend(['','USAGE',*sorted(set(usage))])
        seen=set(); pending=list(handlers.get(name,set())); flags=set()
        for _depth in range(3):
            next_level=[]
            for target in pending:
                if target in seen or target not in functions: continue
                seen.add(target)
                for node in ast.walk(functions[target]):
                    if isinstance(node,ast.Compare):
                        flags.update(token.value for token in ast.walk(node) if isinstance(token,ast.Constant) and isinstance(token.value,str) and token.value.startswith('--') and ' ' not in token.value)
                    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in functions:
                        next_level.append(node.func.id)
            pending=next_level
        if flags and name!='settings': parts.extend(['','RECOGNIZED FLAGS',', '.join(sorted(flags))])
        surface_help={
            'settings':'Settings opens a searchable picker. Supply a word to start filtered, e.g. lk settings voice. Arrows choose; Enter opens the setting.',
            'models':'Models opens the local model chooser. Supply an installed model name to select it. Use lk ollama models for model management and lk fabric models for Fabric inventory.',
            'mp':'LK MP: / search; arrows choose; Tab marks; A marks all shown; E edits metadata for selected tracks; R refreshes metadata; Enter plays; B adds to queue; L library; Q queue; Space pause; Esc clears filter, then exits.',
            'media':'Artist/album browsing: lk media artists or albums opens groups; Enter opens albums/tracks; Esc returns. lk media import opens the owner-local CD/DVD/Blu-ray workbench; --node selects a paired owner. lk media storage remembers a preferred node and maps its root with music/movies/tv/books/inbox; --destination overrides each import. Remote imports deliver through the inbox in the background, verify checksums and index the destination while keeping the source. lk media import watch follows active work without IDs; deliver uses the remembered destination and an album picker; an album name selects one import. In the workbench L delivers/retries the selected album. Use lk media import --help for capture, title choice, metadata and job flags. lk media edit QUERY --artist NAME --all corrects shared metadata; --help lists the fields. Media Find: type or / filters; arrows move; Tab marks; A marks all shown; E edits metadata for selected tracks; R refreshes metadata; Enter plays; Q adds to queue; Esc ends search, clears filter, then exits.',
            'lo':'LO flags: --conservative, --workspace, --power, --unsafe select access; --no-start avoids starting inference; --events-json emits machine events. @NODE selects a host. search PROMPT requests web search; bg PROMPT queues background work.',
        }
        if name in surface_help: parts.extend(['','INTERFACE',surface_help[name]])
        if name=='fabric':
            backend=root/'core/node.py'
            if backend.is_file():
                node_flags=[]
                for node in ast.walk(ast.parse(backend.read_text())):
                    if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='add_argument':
                        names=[arg.value for arg in node.args if isinstance(arg,ast.Constant) and isinstance(arg.value,str) and arg.value.startswith('-')]
                        help_value=next((string(key.value,'') for key in node.keywords if key.arg=='help'),'')
                        if names: node_flags.append(' / '.join(names)+(' — '+help_value if help_value else ''))
                parts.extend(['','FABRIC NODE FLAGS',*sorted(set(node_flags))])
        parts.extend(['','More: lk help all · lk doc · man lk','For command-specific help: lk COMMAND --help or lk help COMMAND'])
        pages[name]='\n'.join(parts)
    return pages


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--check',action='store_true'); args=parser.parse_args()
    stale=[]
    for path,content in outputs().items():
        if args.check:
            if not path.exists() or path.read_text()!=content: stale.append(str(path.relative_to(ROOT)))
        else:
            path.parent.mkdir(parents=True,exist_ok=True); path.write_text(content)
    if stale:
        print('Command reference drift: '+', '.join(stale)); print('Run: python3 tools/command_reference.py'); return 1
    print('Command reference synchronized'); return 0

if __name__=='__main__': raise SystemExit(main())
