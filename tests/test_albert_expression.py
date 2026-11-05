import json
from pathlib import Path
import subprocess
import pytest
from core import albert_expression as expression

ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('prompt,scene',[('read a book','pages'),('music for tonight','waves'),('grow flowers','garden'),('the moon','orbit'),('our fabric home','paths'),('museum art','weave'),('weather today','rain')])
def test_topic_selects_bounded_descriptor(prompt,scene):
    result=expression.describe(prompt,'Some response')
    assert result['scene']==scene and result['version']==1
    assert result==expression.describe(prompt,'Some response')
    assert result['seed']!=expression.describe(prompt,'Different response')['seed']
    assert len(result['word'])<=12


def test_browser_matrix_is_deterministic_bounded_varied_and_safe():
    source=(ROOT/'albert/index.html').read_text()
    js=source[source.index('const EXPRESSION_SCENES='):source.index('function renderChoices(')]
    script=r'''
const assert=require('assert');function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
'''+js+r'''
const shapes=new Set();
for(const scene of EXPRESSION_SCENES){const sig={seed:'12345678abcdef',scene,word:'HELLO'};const m=expressionMatrix(sig);assert.deepEqual(m,expressionMatrix(sig));assert.ok(m.dots.length>30&&m.dots.length<3072);assert.ok(m.dots.every(([x,y])=>x>=0&&x<96&&y>=0&&y<32));shapes.add(JSON.stringify(m.dots));assert.notEqual(expressionMatrix({...sig,variation:1}).scene,scene)}
assert.equal(shapes.size,8);
const dirty=renderSignal({seed:'ffff',word:'<script>alert(1)</script>',scene:'<img>'},'bad\" onclick=evil()');assert.ok(!dirty.includes('<script>'));assert.ok(!dirty.includes('<img>'));assert.ok(!dirty.includes('NaN'));assert.ok(dirty.includes('dot-matrix illustration'));
assert.equal(renderSignal({}), '');
'''
    subprocess.run(['node','-e',script],check=True)
    assert '@media(prefers-reduced-motion:reduce)' in source
