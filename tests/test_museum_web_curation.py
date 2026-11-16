"""Missing originals must not hide curation for registered library entries."""
import shutil
import subprocess
from pathlib import Path
import pytest
from core.museum_web import PAGE

def test_registered_work_without_original_has_voting_controls(tmp_path):
    node=shutil.which('node') or '/Users/jreno/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
    if not Path(node).exists():pytest.skip('Node required for browser action test')
    function=PAGE.split('function renderActions(row,controls){',1)[1].split('// Keep image elements',1)[0]
    script="""const assert=require('assert');let offline=false,owner='3090',collections={},mode='saved',timer=null;
const document={createElement:()=>({setAttribute(){}})};
function renderActions(row,controls){FUNCTION
function labels(row){const controls={items:[],replaceChildren(){this.items=[]},append(b){this.items.push(b)}};renderActions(row,controls);return controls.items.map(b=>b.textContent)}
assert(labels({added:123,downloaded:false}).includes('👍'));
assert(labels({added:123,downloaded:false}).includes('👎'));
assert(!labels({downloaded:false}).includes('👍'));
offline=true;assert(!labels({added:123}).includes('👍'));
""".replace('FUNCTION',function)
    path=tmp_path/'actions.js';path.write_text(script)
    subprocess.run([node,str(path)],check=True,capture_output=True,text=True)
