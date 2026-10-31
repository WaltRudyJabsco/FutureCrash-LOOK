import json
from pathlib import Path
import time
from unittest.mock import Mock
import pytest
import latin
import latin_core as core
from test_media_request_regressions import lk


def test_complete_course_has_all_lessons_references_and_license():
    import hashlib
    assert hashlib.sha256(core.TEXT.encode()).hexdigest()=='09697d0ee38ef370b3e6eff6e1a4313438e2a62e98a92c4862b5ca723a5fd0a3'
    value=core.course()
    assert [r['number'] for r in value['units']]==list(range(80))
    assert 'SUBJUNCTIVE' in value['units'][79]['text']
    assert 'THE ALPHABET' in value['units'][0]['text']
    assert len(core.vocabulary())>1000
    assert 'FULL PROJECT GUTENBERG' in value['references'][-1]['text']
    assert {'readings','appendix-1','appendix-2','appendix-3','index'}<={r['id'] for r in value['references']}
    for n in (-1,80,'nonsense'):
        with pytest.raises(ValueError):core.unit(n)


def test_every_lesson_has_unique_checked_question_and_no_bad_options():
    cards=core.checks()
    assert [c['lesson'] for c in cards]==list(range(80))
    assert len({c['id'] for c in core.deck()})==len(core.deck())
    for card in cards:
        assert len(card['options'])==len(set(card['options']))==4
        assert card['answers'][0] in card['options'] and card['why']
    assert len(core.forms())==474


def test_morphology_examples_across_course_and_accepted_alternatives():
    cards={c['id']:c for c in core.forms()}
    expected={
        'form-puella-singular-4':'puellā','form-servus-singular-5':'serve',
        'form-corpus-plural-0':'corpora','form-mare-plural-1':'marium',
        'form-amō-present indicative active-0':'amō',
        'form-moneō-present subjunctive active-0':'moneam',
        'form-regō-imperfect indicative active-0':'regēbam',
        'form-audiō-future indicative active-2':'audiet',
        'form-capiō-imperfect subjunctive active-3':'caperēmus',
        'form-sum-perfect indicative-0':'fuī',
    }
    for ident,answer in expected.items():assert core.accepted(answer,cards[ident],strict=True),(ident,cards[ident])
    assert core.accepted('civis',cards['form-cīvis-plural-3'])
    assert core.accepted('amare',cards['form-amō-present indicative passive-1'])
    assert core.accepted('amavere',cards['form-amō-perfect indicative active-5'])
    card=cards['form-puella-singular-4']
    assert core.accepted('puella',card) and not core.accepted('puella',card,strict=True)
    assert core.accepted('puella\u0304',card,strict=True)
    assert core.fold('JŪLIUS')==core.fold('iulius')
    assert not core.accepted('puellam',card)


def test_vocabulary_parse_and_lookup_keep_meaning_and_strip_category_labels():
    words=core.lesson_words()[18]
    assert any('companion' in w['definition'] for w in words)
    assert all('ADJECTIVES' not in w['definition'] for w in words)
    assert core.search('ablative absolute')
    assert core.search('subjunctive',kind='lessons')


def test_progress_is_private_local_persistent_and_reference_does_not_lose_place(tmp_path):
    path=tmp_path/'latin/progress.sqlite3';state=core.Progress(path)
    state.save_lesson('lesson-018',page=9,studied=True)
    state.save_lesson('appendix-1',page=100)
    assert state.summary()['last']=='lesson-018'
    assert state.summary()['studied']==1
    state.close();state=core.Progress(path)
    assert state.lesson('lesson-018')['page']==9
    assert path.stat().st_mode&0o777==0o600
    state.close()


def test_spaced_review_excludes_unseen_and_not_due_cards(tmp_path):
    state=core.Progress(tmp_path/'state.sqlite3');cards=core.checks()[:2];now=10000
    assert state.due(cards,now)==[] and len(state.due(cards,now,new=True))==2
    due=state.grade(cards[0]['id'],True,now)
    assert due==now+86400
    assert state.due(cards,now)==[]
    assert [c['id'] for c in state.due(cards,due)]==[cards[0]['id']]
    assert state.grade(cards[0]['id'],True,due)==due+3*86400
    assert state.grade(cards[0]['id'],False,due)==due+600
    assert state.summary()['attempts']==3 and state.summary()['correct']==2
    state.close()


def test_cli_read_only_forms_work_without_creating_progress(tmp_path,monkeypatch,capsys):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    assert latin.main(['list','--json'])==0
    assert len(json.loads(capsys.readouterr().out))==80
    assert latin.main(['lesson','18'])==0
    assert 'SUM' in capsys.readouterr().out
    assert latin.main(['words','puella','--json'])==0
    assert json.loads(capsys.readouterr().out)
    assert not (tmp_path/'.local').exists()


def test_export_is_explicit_non_overwriting_and_private(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    path=tmp_path/'progress.json'
    assert latin.main(['export',str(path)])==0
    assert json.loads(path.read_text())['summary']['studied']==0
    assert path.stat().st_mode&0o777==0o600
    before=path.read_bytes();assert latin.main(['export',str(path)])==1
    assert path.read_bytes()==before


def test_terminal_escape_restores_modes_and_no_network_or_audio(lk,tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    class Terminal:
        def isatty(self):return True
        def fileno(self):return 0
    monkeypatch.setattr(latin.sys,'stdin',Terminal());monkeypatch.setattr(latin.sys.stdout,'isatty',lambda:True)
    old=['original'];monkeypatch.setattr(latin.termios,'tcgetattr',lambda fd:old)
    restored=Mock();monkeypatch.setattr(latin.termios,'tcsetattr',restored);monkeypatch.setattr(latin.tty,'setcbreak',lambda fd:None)
    monkeypatch.setattr(lk,'_read_tty_key',lambda *args:'esc')
    import urllib.request,subprocess
    monkeypatch.setattr(urllib.request,'urlopen',lambda *a,**k:pytest.fail('Latin must be offline'))
    monkeypatch.setattr(subprocess,'Popen',lambda *a,**k:pytest.fail('Latin must not start helpers or speech'))
    assert latin.main([],lk)==0
    assert restored.call_args.args[2] is old


def test_reader_mark_page_navigation_and_reference_state(lk,tmp_path,monkeypatch):
    state=core.Progress(tmp_path/'progress.sqlite3')
    monkeypatch.setattr(latin.termios,'tcgetattr',lambda fd:[])
    class Input:
        def fileno(self):return 0
    monkeypatch.setattr(latin.sys,'stdin',Input())
    keys=iter(['m','shiftright','esc']);monkeypatch.setattr(lk,'_read_tty_key',lambda *args:next(keys))
    classroom=latin.Classroom(lk,state);classroom.read(core.unit(18))
    saved=state.lesson('lesson-018');assert saved['studied'] and saved['page']>0
    state.close()


def test_multiple_classrooms_keep_all_review_attempts(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    path=tmp_path/'state.sqlite3';core.Progress(path).close()
    def review(_):
        state=core.Progress(path)
        try:
            for i in range(20):state.grade('check-1',True,now=i)
        finally:state.close()
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(review,range(2)))
    state=core.Progress(path)
    assert state.summary()['attempts']==40
    state.close()


def test_real_terminal_lesson_navigation_marks_progress_and_restores_modes(tmp_path):
    import os,pty,select,subprocess,sys,termios,fcntl,struct
    root=Path(__file__).resolve().parents[1]
    script=r'''
import sys,termios,importlib.machinery,importlib.util
from pathlib import Path
Path.home=staticmethod(lambda:Path(sys.argv[2]))
sys.path.insert(0,sys.argv[1]+'/look')
l=importlib.machinery.SourceFileLoader('latin_ui_test',sys.argv[1]+'/look/lk');s=importlib.util.spec_from_loader(l.name,l);ui=importlib.util.module_from_spec(s);l.exec_module(ui)
import latin
before=termios.tcgetattr(0)
assert latin.main(['lesson','18'],ui)==0
after=termios.tcgetattr(0)
for attrs in (before,after):attrs[3]&=~getattr(termios,'PENDIN',0)
assert before==after
print('LATIN_TERMINAL_RESTORED')
'''
    master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',30,100,0,0))
    proc=subprocess.Popen([sys.executable,'-u','-c',script,str(root),str(tmp_path)],stdin=slave,stdout=slave,stderr=slave,start_new_session=True)
    os.close(slave);output=b''
    def until(text,timeout=5):
        nonlocal output
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            if text in output:return True
            if select.select([master],[],[],.02)[0]:
                try:output+=os.read(master,65536)
                except OSError:break
        return False
    try:
        assert until(b'LATIN'),output[-1000:]
        output=b'';os.write(master,b'\x1b[1;2C')
        assert until(b'Project Gutenberg'),output[-1000:]
        output=b'';os.write(master,b'/')
        assert until(b'Find in this text'),output[-1000:]
        assert until('› '.encode()),output[-1000:]
        output=b'';os.write(master,b'\x1b')
        assert until(b'Project Gutenberg'),output[-1000:]
        output=b'';os.write(master,b'm')
        assert until(b'Marked studied'),output[-1000:]
        output=b'';os.write(master,b'\x1b')
        assert until(b'LATIN_TERMINAL_RESTORED'),output[-1000:]
        proc.wait(timeout=2);assert proc.returncode==0
        state=core.Progress(tmp_path/'.local/share/look/latin/progress.sqlite3')
        assert state.lesson('lesson-018')['studied']==1 and state.lesson('lesson-018')['page']>0
        state.close()
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
        os.close(master)


def test_idle_classroom_does_not_repaint(lk,tmp_path,monkeypatch):
    state=core.Progress(tmp_path/'progress.sqlite3')
    monkeypatch.setattr(latin.termios,'tcgetattr',lambda fd:[])
    class Input:
        def fileno(self):return 0
    monkeypatch.setattr(latin.sys,'stdin',Input())
    keys=iter([None,None,'esc']);monkeypatch.setattr(lk,'_read_tty_key',lambda *a:next(keys))
    room=latin.Classroom(lk,state);render=Mock();monkeypatch.setattr(room,'frame',render)
    room.choose('Test',[{'title':'One'}],lambda r:r['title'])
    assert render.call_count==1
    state.close()


def test_course_uses_existing_bundle_rules_and_keeps_progress_out():
    from core import maintenance
    for name in ('latin.py','latin_core.py','latin_data.py','latin_course.py'):
        assert maintenance.allowed('.local/share/look/'+name)
    assert not maintenance.allowed('.local/share/look/latin/progress.sqlite3')
    installer=(Path(__file__).resolve().parents[1]/'install-look.sh').read_text()
    for name in ('latin.py','latin_core.py','latin_data.py','latin_course.py'):assert '$ROOT/look/'+name in installer


def test_words_search_and_practice_prompts_use_renderer_directly(lk,tmp_path,monkeypatch):
    # The real LK module imports selected renderer symbols, not a module attribute.
    assert not hasattr(lk,'look_renderer')
    state=core.Progress(tmp_path/'progress.sqlite3')
    monkeypatch.setattr(latin.termios,'tcgetattr',lambda fd:[])
    restored=Mock();monkeypatch.setattr(latin.termios,'tcsetattr',restored)
    monkeypatch.setattr(latin.tty,'setcbreak',lambda fd:None)
    class Input:
        def fileno(self):return 0
    monkeypatch.setattr(latin.sys,'stdin',Input())
    prompt=Mock(return_value=('',False));monkeypatch.setattr(latin.look_renderer,'prompt_line',prompt)
    room=latin.Classroom(lk,state)
    room.words(lesson=0)  # No supplied vocabulary: show a return prompt.
    assert prompt.call_count==1
    keys=iter(['/','esc']);monkeypatch.setattr(lk,'_read_tty_key',lambda *a:next(keys))
    room.choose('Words',[{'title':'Test'}],lambda r:r['title'])
    assert prompt.call_count==2
    prompt.return_value=('',True)
    room.practice(0,exact=True)
    assert prompt.call_count==3 and state.summary()['attempts']==0
    assert restored.call_count==3
    state.close()
