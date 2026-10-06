from pathlib import Path
import ast, re

ROOT=Path(__file__).resolve().parents[1]

def test_look_local_modules_are_installed():
    lk=(ROOT/'look/lk').read_text()
    tree=ast.parse(lk)
    local={p.stem for p in (ROOT/'look').glob('*.py')}
    imports=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            imports.update(a.name.split('.')[0] for a in node.names)
        elif isinstance(node,ast.ImportFrom) and node.module:
            imports.add(node.module.split('.')[0])
    required=sorted(local & imports)
    installer=(ROOT/'install-look.sh').read_text()
    missing=[m for m in required if not re.search(rf'look/{re.escape(m)}\.py',installer)]
    assert not missing, f'LOOK imports local modules not copied by installer: {missing}'
