from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[1]


def _load_lk():
    spec=importlib.util.spec_from_file_location('lk800', ROOT/'look'/'lk')
    # Extensionless scripts need an explicit SourceFileLoader.
    from importlib.machinery import SourceFileLoader
    spec=importlib.util.spec_from_loader('lk800', SourceFileLoader('lk800', str(ROOT/'look'/'lk')))
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def test_media_find_supports_look_negative_terms():
    lk=_load_lk()
    rows=[
        {'title':'Clampdown','artist':'The Clash','album':'London Calling'},
        {'title':'Clampdown Live','artist':'The Clash','album':'Live'},
        {'title':'Rock the Casbah Remix','artist':'The Clash','album':'Remixes'},
        {'title':'Psycho Killer','artist':'Talking Heads'},
    ]
    got=lk._media_filter_rows(rows, r'clash \live \remix')
    assert [r['title'] for r in got] == ['Clampdown']


def test_media_find_selection_keys_are_playlist_oriented():
    text=(ROOT/'look'/'lk').read_text()
    assert 'A select all' in text
    assert 'Q queue' in text
    assert 'visible_ids.issubset(selected_ids)' in text
    assert 'A queue matches' not in text


def test_albert_uses_full_fabric_queue():
    html=(ROOT/'albert'/'index.html').read_text()
    assert 'const queue=Array.isArray(f.queue)&&f.queue.length?f.queue:null' in html
    assert "mediaStep('${f.id}',-1)" in html
    assert "mediaStep('${f.id}',1)" in html
    assert "addEventListener('ended',()=>mediaStep(media.dataset.foldId,1)" in html
    assert "mediaClear('${f.id}')" in html
    assert "${qi+1} / ${queue.length}" in html


def test_new_albert_audio_replaces_prior_audio_fold():
    html=(ROOT/'albert'/'index.html').read_text()
    assert "if(f.type==='audio'){state.folds.forEach" in html
    assert "if(old.type==='audio'&&!old.dismissed)old.dismissed=true" in html
