import importlib.machinery, importlib.util, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
loader=importlib.machinery.SourceFileLoader('look_lk_710',str(ROOT/'look'/'lk'))
spec=importlib.util.spec_from_loader(loader.name,loader)
lk=importlib.util.module_from_spec(spec); sys.modules[loader.name]=lk; loader.exec_module(lk)
sys.path.insert(0,str(ROOT/'core'))
import jev, cognition


def test_normalization_strips_discourse_and_self_address():
    assert jev.normalize_utterance('and close it')=='close it'
    assert jev.normalize_utterance('lo close that window')=='close that window'
    assert jev.normalize_utterance('okay then lo close it')=='close it'


def test_named_referent_unique_prefix_resolves():
    ref={'id':'term_a','kind':'terminal_window','command':'asciiquarium','platform':'linux'}
    d=jev.referential_action('close ascii',[ref])
    assert d and d['object']['id']=='term_a'


def test_named_referent_ambiguity_falls_through():
    refs=[
        {'id':'a','kind':'terminal_window','command':'asciiquarium'},
        {'id':'b','kind':'terminal_window','command':'ascii-clock'},
    ]
    assert jev.referential_action('close ascii',refs) is None


def test_image_generation_owns_weather_words():
    text='make me an image of a rain-soaked 1920s tokyo alley ramen shop'
    d=jev.image_imperative(text)
    assert d['prompt']=='a rain-soaked 1920s tokyo alley ramen shop'
    route=cognition.analyze(text,use_openjev=False)
    assert route.primary=='image'
    assert 'weather' not in route.families
    assert lk._lo_requires_weather(text) is False


def test_signal_image_does_not_get_claimed_by_comfy_tree():
    assert jev.image_imperative('make a Signal image of a rainy city') is None


def test_real_lo_image_turn_executes_before_cognition(tmp_path,monkeypatch,capsys):
    calls=[]
    monkeypatch.setattr(lk,'_lo_cognition_route',lambda *a,**k: (_ for _ in ()).throw(AssertionError('cognition ran before image JEV')))
    monkeypatch.setattr(lk,'_run_capability_tool',lambda name,args,workspace,profile: calls.append((name,args.copy())) or 'IMAGE OK · /tmp/test.png')
    class WS:
        def begin_action(self,*a,**k): return {'mode':'deliberate','verify':True}
        def record_receipt(self,*a,**k): return {}
        def latest_receipts(self,*a,**k): return []
    monkeypatch.setattr(lk,'_world_state',lambda:WS())
    rc=lk.ollama_chat(initial_prompt='generate an image of a rain soaked alley',access_profile='power',workspace_override=tmp_path,one_shot=True)
    assert rc==0
    assert calls==[('generate_image',{'prompt':'a rain soaked alley'})]
    out=capsys.readouterr().out
    assert 'weather ›' not in out
    assert 'Generated the image.' in out


def test_referent_variants_route_before_cognition(tmp_path,monkeypatch,capsys):
    ref={'id':'term_1','kind':'terminal_window','platform':'linux','command':'asciiquarium','pid_file':'/tmp/x'}
    prior={'tool':'run_command','path':'asciiquarium','args':{'command':'asciiquarium','new_terminal':True,'_referent':ref}}
    monkeypatch.setattr(lk,'_lo_latest_command_action',lambda:prior)
    monkeypatch.setattr(lk,'_lo_cognition_route',lambda *a,**k: (_ for _ in ()).throw(AssertionError('cognition ran')))
    monkeypatch.setattr(lk,'_close_typed_referent',lambda obj:'close ok · terminal window closed')
    class WS:
        def begin_action(self,*a,**k): return {'mode':'deliberate','verify':True}
        def record_receipt(self,*a,**k): return {}
        def latest_receipts(self,*a,**k): return []
    monkeypatch.setattr(lk,'_world_state',lambda:WS())
    for phrase in ('and close it','lo close that window','close ascii'):
        assert lk.ollama_chat(initial_prompt=phrase,access_profile='power',workspace_override=tmp_path,one_shot=True)==0
    assert capsys.readouterr().out.count('Closed that window.')==3


def test_installer_provisions_jev1_and_macos_lifecycle():
    install=(ROOT/'install.sh').read_text()
    assert 'MEM_GIB >= 12' in install
    assert 'OPENJEV_MODE="install"' in install
    assert 'com.futurecrash.look.openjev.plist' in install
    assert 'fcl-openjev-worker' in install
    worker=(ROOT/'core'/'fcl-openjev-worker').read_text()
    assert 'torch.cuda.is_available()' in worker
    assert 'torch.backends.mps' in worker
    assert "device='cpu'" in worker
