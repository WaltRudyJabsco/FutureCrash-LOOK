from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_node_exposes_media_output_routing():
    text=(ROOT/'core/node.py').read_text()
    for needle in ('/v1/media/output','/v1/media/outputs','/v1/media/state','/v1/media/session-full','/v1/media/route','/v1/media/audio'):
        assert needle in text
    assert '_fabric_media_move' in text
    assert '_serve_media_audio' in text
    assert 'media.playback' in text


def test_signal_output_selector_lives_on_media_card_and_routes_media():
    html=(ROOT/'signal-window/index.html').read_text()
    js=(ROOT/'signal-window/app.js').read_text()
    server=(ROOT/'signal-window/server.py').read_text()
    assert 'id="mediaOutput"' not in html
    assert "className='media-output-select'" in js
    assert "thisDeviceLabel()" in js
    assert "value='__browser__'" in js
    assert '/api/media/outputs' in js
    assert '/api/media/move' in js
    assert '/api/media/audio' in js
    assert 'media_node:mediaNode' in js
    assert '/v1/media/route' in server
    assert '/v1/media/audio' in server
    assert 'deterministic-media' in server


def test_camera_prompt_is_real_selected_text_not_placeholder():
    js=(ROOT/'signal-window/app.js').read_text()
    assert "input.value='what am I looking at?'" in js
    assert 'input.select()' in js
    assert "input.placeholder='what am I looking at?'" not in js


def test_look_has_node_scoped_media_controls():
    text=(ROOT/'look/lk').read_text()
    assert '_media_outputs_command' in text
    assert '_media_on_command' in text
    assert 'lk media on NODE play TARGET' in text
    assert 'session-json' in text
    assert '_media_adopt_session' in text


def test_installer_treats_mpv_as_workstation_dependency():
    text=(ROOT/'install-look.sh').read_text()
    core_line=next(line for line in text.splitlines() if line.startswith('core=('))
    assert 'mpv' in core_line
    assert 'Install mpv?' not in text
