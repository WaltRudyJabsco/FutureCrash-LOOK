"""The work command opens a real shell only after selecting the block."""
import fcntl
import os
from pathlib import Path
import pty
import select
import shlex
import struct
import subprocess
import sys
import termios
import time

import pytest


@pytest.mark.parametrize('configured_shell', [False, True])
def test_work_inline_shell_can_read_input_and_resume(tmp_path, configured_shell):
    pytest.importorskip('pyte')
    root = Path(__file__).resolve().parents[1]
    document = tmp_path/'workspace.md'
    source = """# Workspace

```sh
touch started
stty size
printf 'Ready for input: '
read answer
printf 'RESULT:%s\\n' "$answer"
```

Back to the document.

```sh
printf 'SECOND_%s\\n' BLOCK
```

```command label="Print marker" cwd="."
touch run-marker
printf 'RUN_%s\\n' MARKER
```
"""
    if configured_shell:
        if not Path('/bin/zsh').is_file():
            pytest.skip('zsh unavailable')
        source = source.replace('```sh', '```shell')
        (tmp_path/'.zshrc').write_text("alias lk='echo LK_ALIAS_OK'\nf() { echo F_FUNCTION_OK; }\n")
    document.write_text(source)
    editor = tmp_path/'edit.py'
    editor.write_text("from pathlib import Path\nimport sys\np=Path(sys.argv[1])\np.write_text(p.read_text().replace('Back to the document.', 'Edited in LK Work.'))\n")
    editor_command = shlex.join([sys.executable, str(editor)])
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 28, 100, 0, 0))
    process = subprocess.Popen(
        [sys.executable, str(root/'look/lk'), 'work', str(document)],
        stdin=slave, stdout=slave, stderr=slave,
        env=dict(os.environ, TERM='xterm-256color', VISUAL=editor_command,
                 SHELL='/bin/zsh' if configured_shell else '/bin/sh',
                 ZDOTDIR=str(tmp_path)), start_new_session=True,
    )
    os.close(slave)

    def until(needle):
        output = bytearray()
        deadline = time.monotonic()+5
        while needle not in output and time.monotonic()<deadline:
            if select.select([master], [], [], .1)[0]:
                output.extend(os.read(master, 8192))
        assert needle in output, bytes(output[-1500:])

    try:
        until(b'Run shell block')
        assert not (tmp_path/'started').exists()
        os.write(master, b'\t\r')
        until(b'16 95')
        os.write(master, b'alexandria\r')
        until(b'RESULT:alexandria')
        assert (tmp_path/'started').is_file()
        os.write(master, b'\x07')
        until(b'Resume shell')
        os.write(master, b'e')
        until(b'Edited in LK Work.')
        os.write(master, b'\t\r')
        until(b'Live shell')
        if configured_shell:
            os.write(master, b'lk; f\r')
            until(b'F_FUNCTION_OK')
        os.write(master, b'printf "AGAIN:%s\\n" "$answer"\r')
        until(b'AGAIN:alexandria')
        os.write(master, b'\x07')
        until(b'Resume shell')
        os.write(master, b'\t\r')
        until(b'SECOND_BLOCK')
        os.write(master, b'\x07')
        until(b'Resume shell 2')
        os.write(master, b'\t\r')
        until(b'RUN NOTE COMMAND')
        assert not (tmp_path/'run-marker').exists()
        os.write(master, b'R')
        until(b'Press Enter')
        assert (tmp_path/'run-marker').is_file()
        os.write(master, b'\r')
        until(b'LK WORK')
        os.write(master, b'q')
        deadline = time.monotonic()+4
        while process.poll() is None and time.monotonic()<deadline:
            if select.select([master], [], [], .1)[0]:
                try:
                    if not os.read(master, 8192):
                        break
                except OSError:
                    break
        assert process.wait(timeout=1) == 0
        assert document.read_text() == source.replace('Back to the document.', 'Edited in LK Work.')
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=4)
        os.close(master)


def test_notes_terminal_keeps_note_context_and_child_colors(tmp_path):
    pytest.importorskip('pyte')
    root = Path(__file__).resolve().parents[1]
    program = r"""
import runpy,sys
from pathlib import Path
root,path=map(Path,sys.argv[1:])
sys.path.insert(0,str(root/'look'))
import notebook
keys=runpy.run_path(str(root/'look/lk'))['_read_tty_key']
row=dict(path=str(path), title='Inline note', created=0, updated=0,
         body="Before the terminal\n\n```terminal label=Colors\nprintf '\\033[31mRED_MARK\\033[34mBLUE_MARK\\033[0m\\n'\n```\n\nAfter the terminal")
path.write_text(notebook.Notebook.markdown(row))
notebook.note_view(None,row,keys)
"""
    master,slave = pty.openpty()
    fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',30,100,0,0))
    child = subprocess.Popen([sys.executable,'-c',program,str(root),str(tmp_path/'note.md')],
                             stdin=slave,stdout=slave,stderr=slave,
                             env=dict(os.environ,TERM='xterm-256color',SHELL='/bin/sh'),
                             start_new_session=True)
    os.close(slave)

    def until(needle):
        output = bytearray()
        deadline = time.monotonic()+5
        while needle not in output and time.monotonic()<deadline:
            if select.select([master],[],[],.1)[0]:
                chunk = os.read(master,8192)
                if not chunk:
                    break
                output.extend(chunk)
        assert needle in output,bytes(output[-1800:])
        return bytes(output)

    try:
        until(b'Terminal: Colors')
        os.write(master,b'1')
        until(b'Press Enter to open')
        os.write(master,b'\r')
        frame = until(b'\x1b[0;34;49mBLUE_MARK')
        assert b'\x1b[0;31;49mRED_MARK' in frame
        assert b'Inline note' in frame
        assert b'Before the terminal' in frame and b'After the terminal' in frame
        os.write(master,b'\x07')
        until(b'Terminal collapsed')
        os.write(master,b'1\r')
        until(b'\x1b[0;34;49mBLUE_MARK')
        os.write(master,b'\x07')
        until(b'Terminal collapsed')
        os.write(master,b'q')
        assert child.wait(timeout=4)==0
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=4)
        os.close(master)
