import json
from look import lo_history as history


class Editor:
    def __init__(self): self.rows = ['unrelated confirmation']; self.auto = True
    def get_current_history_length(self): return len(self.rows)
    def get_history_item(self, index): return self.rows[index - 1]
    def clear_history(self): self.rows.clear()
    def add_history(self, text): self.rows.append(text)
    def set_auto_history(self, value): self.auto = value


def test_recall_is_persistent_separate_and_does_not_execute(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    editor = Editor()
    monkeypatch.setattr(history, 'readline', editor)
    history.remember('what is in this chart?')
    history.remember('!git status')
    editor.rows = ['unrelated confirmation']
    with history.prompt_history():
        assert editor.rows == ['what is in this chart?', '!git status']
        assert not editor.auto
        history.remember('compare with this file')
    assert editor.rows == ['unrelated confirmation']
    assert editor.auto
    with history.prompt_history():
        assert editor.rows[-1] == 'compare with this file'
    assert history.history_path().stat().st_mode & 0o777 == 0o600


def test_history_bounded_deduplicated_and_invalid_file_recovers(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setattr(history, 'readline', None)
    monkeypatch.setattr(history, 'LIMIT', 3)
    for text in ('one', 'two', 'two', '', 'three', 'four', 'multiple\nlines'):
        history.remember(text)
    assert json.loads(history.history_path().read_text()) == ['two', 'three', 'four']
    history.history_path().write_text('invalid')
    history.remember('recovered')
    assert json.loads(history.history_path().read_text()) == ['recovered']


def test_session_restores_editor_on_error_and_one_shot_does_not_record(monkeypatch, tmp_path):
    monkeypatch.setenv('HOME', str(tmp_path))
    editor = Editor()
    monkeypatch.setattr(history, 'readline', editor)
    @history.session
    def chat(**kwargs): raise RuntimeError('failure')
    import pytest
    with pytest.raises(RuntimeError): chat(initial_prompt='test image')
    assert editor.rows == ['unrelated confirmation']
    with pytest.raises(RuntimeError): chat(one_shot=True, initial_prompt='browser request')
    assert json.loads(history.history_path().read_text()) == ['test image']
