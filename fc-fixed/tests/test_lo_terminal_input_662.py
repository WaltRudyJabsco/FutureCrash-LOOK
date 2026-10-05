from pathlib import Path
import ast
import re

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'look'/'lk').read_text()


def _prompt_fn(doc):
    tree=ast.parse(SOURCE)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_lo_readline_prompt')
    ns={'re':re,'readline':type('Readline',(),{'__doc__':doc})()}
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<lo-prompt>','exec'),ns)
    return ns['_lo_readline_prompt']


def test_lo_input_no_longer_gives_readline_a_multiline_colored_prompt():
    assert 'prompt = _lo_read_input().strip()' in SOURCE
    assert 'input("\\n"+_lo_label("you","36")+"\\n"+_c("› ","36"))' not in SOURCE
    assert 'print("\\n"+_lo_label("you","36"))' in SOURCE


def test_gnu_readline_ansi_is_marked_zero_width():
    fn=_prompt_fn('GNU readline')
    prompt=fn('\x1b[36m› \x1b[0m')
    assert '\x01\x1b[36m\x02' in prompt
    assert '\x01\x1b[0m\x02' in prompt
    visible=re.sub(r'[\x01\x02]|\x1b\[[0-9;]*m','',prompt)
    assert visible=='› '


def test_macos_libedit_prompt_is_plain_width_safe():
    fn=_prompt_fn('libedit readline wrapper')
    assert fn('\x1b[38;2;103;214;238m› \x1b[0m')=='› '
