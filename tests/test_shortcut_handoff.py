from pathlib import Path
import pytest
from shortcut_handoff import prepare


def test_temporary_file_survives_shortcut_cleanup(tmp_path):
    source=tmp_path/'Library/Group Containers/group.com.apple.shortcuts/Temporary/runner/News overview.html'
    source.parent.mkdir(parents=True);source.write_text('<p>Article</p>')
    result=prepare(['Summarize this',str(source)],home=tmp_path)
    source.unlink()
    assert result[0]=='Summarize this'
    saved=Path(result[1]);assert saved.read_text()=='<p>Article</p>'
    assert saved.stat().st_mode & 0o777==0o600


def test_missing_shortcut_file_fails_without_launching(tmp_path):
    source=tmp_path/'Library/Group Containers/group.com.apple.shortcuts/Temporary/gone.html'
    with pytest.raises(ValueError,match='expired'):prepare([str(source)],home=tmp_path)


def test_ordinary_paths_and_text_are_preserved(tmp_path):
    args=['Text with spaces',str(tmp_path/'regular.txt')]
    assert prepare(args,home=tmp_path)==args
