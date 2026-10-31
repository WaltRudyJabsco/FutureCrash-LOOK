from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import os
import pytest
import words_desk as desk
import words
from test_media_request_regressions import lk


def result(query='obtuse'):
    return {'query':query,'source':'Test dictionary','results':[{'lemma':query,'part_of_speech':'adjective','definitions':['Slow to understand.'],'examples':['A sample sentence.'],'synonyms':['dense','slow'],'antonyms':['acute'],'related':{'similar':['dull']}}]}


class Work:
    def get(self,key,compute,*args,**kwargs):
        if getattr(self,'key',None)!=key:self.key=key;self.value=compute()
        return self.value
    def close(self):pass


def terminal(monkeypatch,lk,size=(80,28)):
    monkeypatch.setattr(words,'launch_word',lambda:None)
    monkeypatch.setattr(desk.sys,'stdin',Mock(isatty=lambda:True,fileno=lambda:0))
    monkeypatch.setattr(desk.sys.stdout,'isatty',lambda:True)
    monkeypatch.setattr(desk.termios,'tcgetattr',lambda fd:['original'])
    restore=Mock();monkeypatch.setattr(desk.termios,'tcsetattr',restore)
    monkeypatch.setattr(desk.tty,'setcbreak',lambda fd:None)
    monkeypatch.setattr(desk,'LatestWork',Work)
    monkeypatch.setattr(lk.shutil,'get_terminal_size',lambda *args:os.terminal_size(size))
    return restore


def keys(monkeypatch,lk,sequence):
    iterator=iter(sequence);monkeypatch.setattr(lk,'_read_tty_key',lambda *args:next(iterator))


def test_meaning_synonyms_and_antonyms_are_selectable_by_sense():
    value=result()
    assert 'Slow to understand' in desk.entries(value,0)[0]['detail']
    synonyms=desk.entries(value,1)
    assert [r['target'] for r in synonyms]==['dense','slow','dull']
    assert synonyms[-1]['detail'].startswith('Related (similar), not a direct synonym')
    assert desk.entries(value,2)[0]['target']=='acute'


def test_spell_only_shows_issues_and_explicit_suggestions():
    value={'words':[{'word':'good','recognized':True,'suggestions':[],'source':'SCOWL'},
                    {'word':'sentance','recognized':False,'suggestions':['sentence'],'source':'SCOWL'}]}
    rows=desk.entries(value,3)
    assert len(rows)==2 and all('good' not in row['title'] for row in rows)
    assert rows[1]['issue']=='sentance' and rows[1]['replacement']=='sentence'
    assert desk.replace_word('sentance sentances sentance.','sentance','sentence')=='sentence sentances sentence.'


@pytest.mark.parametrize('size',[(40,16),(80,28),(160,40)])
def test_bare_desk_keeps_search_views_and_pane_without_filer(lk,monkeypatch,capsys,size):
    restore=terminal(monkeypatch,lk,size)
    calls=[]
    def tool(action,query,language):
        calls.append((action,query));return {'installed':True} if action=='status' else result(query)
    monkeypatch.setattr(words,'tool',tool)
    pane=Mock(return_value='Shell opened beside LOOK · Option-Shift-W switch pane · Ctrl-Shift-W close focused pane')
    monkeypatch.setattr(desk.terminal_style,'open_pane',pane)
    copy=Mock(return_value='Copied');monkeypatch.setattr(desk,'copy',copy)
    frames=[];monkeypatch.setattr(lk,'_terminal_frame_payload',lambda text:frames.append(lk._strip_ansi(text)) or '')
    keys(monkeypatch,lk,['esc','W',*'obtuse','enter','2','y','enter','3','esc'])
    assert desk.desk(lk)==0
    assert calls==[('status',''),('lookup','obtuse'),('lookup','obtuse'),('lookup','dense'),('lookup','dense')]
    pane.assert_called_once_with(Path.cwd());copy.assert_called_once_with('dense')
    assert all(len(frame.splitlines())<=size[1] for frame in frames)
    assert 'LOOK WORDS' in frames[-1] and any('SYNONYMS' in f for f in frames)
    assert restore.call_args.args[2]==['original']
    assert '\033[?2004l' in capsys.readouterr().out


def test_editor_paste_does_not_execute_commands_and_escape_restores_query(lk,monkeypatch):
    terminal(monkeypatch,lk)
    pane=Mock();monkeypatch.setattr(desk.terminal_style,'open_pane',pane)
    lookup=Mock(return_value=result());monkeypatch.setattr(words,'tool',lookup)
    keys(monkeypatch,lk,['/','\x15','paste:W\x1b[31m\nZoë','esc','esc'])
    assert desk.desk(lk,initial='obtuse')==0
    lookup.assert_called_once_with('lookup','obtuse','en_US');pane.assert_not_called()


def test_spell_suggestion_applies_to_working_copy_and_copies_it(lk,monkeypatch):
    terminal(monkeypatch,lk)
    def tool(action,query,language):
        if query.endswith('sentance'):
            return {'words':[{'word':'sentance','recognized':False,'suggestions':['sentence'],'source':'SCOWL'}]}
        return {'words':[{'word':'sentence','recognized':True,'suggestions':[],'source':'SCOWL'}]}
    monkeypatch.setattr(words,'tool',tool)
    copy=Mock(return_value='Copied');monkeypatch.setattr(desk,'copy',copy)
    # The issue has two wrapped display rows; the next row is the suggestion.
    keys(monkeypatch,lk,['down','down','enter','c','esc'])
    assert desk.desk(lk,initial='A sentance',view=3)==0
    copy.assert_called_once_with('A sentence')


def test_clipboard_paragraph_selects_spelling_and_keeps_unicode(lk,monkeypatch):
    terminal(monkeypatch,lk)
    paragraph='Zoë wrote a very beautiful sentence about the garden today.'
    monkeypatch.setattr(desk.clipboard_shelf,'read_clipboard',lambda:paragraph)
    tool=Mock(return_value={'words':[]});monkeypatch.setattr(words,'tool',tool)
    keys(monkeypatch,lk,['esc','p','enter','esc'])
    assert desk.desk(lk)==0
    assert tool.call_args.args==('spell',paragraph,'en_US')


def test_explicit_copy_saves_clip_without_enabling_capture(monkeypatch):
    shelf=Mock();monkeypatch.setattr(desk.clipboard_shelf,'Shelf',lambda:shelf)
    monkeypatch.setattr(desk.clipboard_shelf,'copy_clipboard',lambda text:True)
    assert desk.copy('Zoë')=='Copied to clipboard and LK Clip'
    shelf.observe.assert_called_once_with('Zoë');shelf.set.assert_not_called();shelf.close.assert_called_once()


def test_resize_and_idle_keep_input_and_do_not_repaint(lk,monkeypatch):
    terminal(monkeypatch,lk)
    monkeypatch.setattr(words,'tool',lambda *args:result())
    sizes=[(100,30)];frames=[]
    monkeypatch.setattr(lk.shutil,'get_terminal_size',lambda *args:os.terminal_size(sizes[-1]))
    monkeypatch.setattr(lk,'_terminal_frame_payload',lambda text:frames.append(text) or text)
    sequence=iter(['','/','e','', 'esc','esc'])
    def read(*args):
        key=next(sequence)
        if key=='e':sizes.append((40,16))
        return key
    monkeypatch.setattr(lk,'_read_tty_key',read)
    assert desk.desk(lk,initial='obtus')==0
    assert any('obtuse▏' in lk._strip_ansi(frame) for frame in frames)


def test_back_returns_to_previous_thesaurus_query(lk,monkeypatch):
    terminal(monkeypatch,lk)
    queries=[]
    def tool(action,query,language):queries.append(query);return result(query)
    monkeypatch.setattr(words,'tool',tool)
    keys(monkeypatch,lk,['enter','b','esc'])
    assert desk.desk(lk,initial='obtuse',view=1)==0
    assert queries==['obtuse','dense','obtuse']


def test_pending_lookup_does_not_block_escape_or_paint_after_exit(lk,monkeypatch,capsys):
    import threading
    from media_ui_work import LatestWork
    terminal(monkeypatch,lk);monkeypatch.setattr(desk,'LatestWork',LatestWork)
    entered=threading.Event();release=threading.Event();finished=threading.Event()
    def tool(*args):
        entered.set();release.wait(2);finished.set();return result()
    monkeypatch.setattr(words,'tool',tool)
    def read(*args):
        assert entered.wait(1)
        return 'esc'
    monkeypatch.setattr(lk,'_read_tty_key',read)
    try:
        assert desk.desk(lk,initial='obtuse')==0
        capsys.readouterr()
    finally:release.set()
    assert finished.wait(1)
    assert capsys.readouterr().out==''


def test_initial_search_treats_command_letters_as_text(lk,monkeypatch):
    terminal(monkeypatch,lk)
    tool=Mock(return_value=result());monkeypatch.setattr(words,'tool',tool)
    copy=Mock();monkeypatch.setattr(desk,'copy',copy)
    keys(monkeypatch,lk,[*'cat','enter','esc'])
    assert desk.desk(lk)==0
    assert tool.call_args.args==('lookup','cat','en_US')
    copy.assert_not_called()


def test_launch_card_appears_once_and_disappears_on_first_character(lk,monkeypatch):
    terminal(monkeypatch,lk,size=(40,16))
    card=Mock(return_value={'word':'pellucid','definition':'Transparently clear.','part_of_speech':'adjective','source':'Local WordNet'})
    monkeypatch.setattr(words,'launch_word',card)
    monkeypatch.setattr(words,'tool',lambda *args:{'installed':True})
    frames=[]
    monkeypatch.setattr(lk,'_terminal_frame_payload',lambda text:frames.append(lk._strip_ansi(text)) or '')
    keys(monkeypatch,lk,['c','esc','esc'])
    assert desk.desk(lk)==0
    assert 'WORD OF THIS LAUNCH' in frames[0] and 'pellucid' in frames[0]
    assert all('WORD OF THIS LAUNCH' not in frame for frame in frames[1:])
    card.assert_called_once()
    assert all(len(frame.splitlines())<=16 for frame in frames)


def test_explicit_query_has_no_launch_card(lk,monkeypatch):
    terminal(monkeypatch,lk)
    card=Mock();monkeypatch.setattr(words,'launch_word',card)
    monkeypatch.setattr(words,'tool',lambda *args:result())
    keys(monkeypatch,lk,['esc'])
    assert desk.desk(lk,initial='obtuse')==0
    card.assert_not_called()
