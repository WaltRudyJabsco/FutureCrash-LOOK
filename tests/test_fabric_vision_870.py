import base64
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VISION=ROOT/'core'/'fabric_vision.py'
LK=(ROOT/'look'/'lk').read_text(encoding='utf-8')
NODE=(ROOT/'core'/'node.py').read_text(encoding='utf-8')
INSTALL=(ROOT/'install.sh').read_text(encoding='utf-8')


def load_vision():
    spec=importlib.util.spec_from_file_location('fabric_vision_test',VISION)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_fabric_vision_is_pull_only_and_ephemeral():
    text=VISION.read_text(encoding='utf-8')
    assert 'capture_screen' in text
    assert 'TemporaryDirectory' in text
    assert 'stored": False' in text
    assert 'previous_hash' in text
    assert 'image_base64' in text
    assert 'threading' not in text
    assert 'time.sleep' not in text


def test_screen_route_is_authenticated_and_relayable():
    assert 'if path == "/v1/vision/screen"' in NODE
    assert 'return self._serve_vision_screen' in NODE
    assert 'FABRIC_IDENTITY.auth_headers_for_url(url)' in NODE
    assert 'vision.screen' in NODE


def test_look_cli_supports_one_shot_watch_save_and_ask():
    assert 'lk vision screen' in LK
    assert '--watch' in LK
    assert '--every' in LK
    assert '--save' in LK
    assert '--ask' in LK
    assert '_vision_model_answer(data,ask,label)' in LK
    assert 'nothing retained remotely' in LK


def test_installer_carries_fabric_vision_module():
    assert 'core/fabric_vision.py' in INSTALL
    assert 'installed Fabric Vision core differs from release' in INSTALL


def test_unchanged_frame_omits_image_payload(tmp_path, monkeypatch):
    mod=load_vision()
    fake=tmp_path/'shot.png'
    data=b'not-a-real-png-but-stable-for-hash'
    monkeypatch.setattr(mod,'capture_provider',lambda:{'name':'fake','tool':'/fake/tool','platform':'test'})
    monkeypatch.setattr(mod,'_capture_command',lambda provider,output:['fake',str(output)])
    class Result:
        returncode=0
        stderr=b''
    def run(*args,**kwargs):
        # capture_screen owns a private temp path; create its expected output.
        command=args[0]
        Path(command[-1]).write_bytes(data)
        return Result()
    monkeypatch.setattr(mod.subprocess,'run',run)
    def compress(source,dest,max_width,quality):
        source.write_bytes(data)
        return source,'image/png'
    monkeypatch.setattr(mod,'_compress',compress)
    first=mod.capture_screen()
    assert first['ok'] is True and first['changed'] is True
    assert base64.b64decode(first['image_base64'])==data
    second=mod.capture_screen(previous_hash=first['hash'])
    assert second['ok'] is True and second['changed'] is False
    assert 'image_base64' not in second


def test_wayland_never_selects_x11_only_import(monkeypatch):
    mod=load_vision()
    monkeypatch.setattr(mod.platform,'system',lambda:'Linux')
    monkeypatch.setenv('XDG_SESSION_TYPE','wayland')
    monkeypatch.setattr(mod,'_which',lambda *names: '/usr/bin/import' if 'import' in names else None)
    monkeypatch.setattr(mod,'_portal_python',lambda:None)
    provider=mod.capture_provider()
    assert provider['tool']==''
    assert provider['session']=='wayland'
    assert 'Wayland screen capture' in provider['error']


def test_wayland_uses_desktop_portal_before_x11_fallback(monkeypatch):
    mod=load_vision()
    monkeypatch.setattr(mod.platform,'system',lambda:'Linux')
    monkeypatch.setenv('XDG_SESSION_TYPE','wayland')
    monkeypatch.setattr(mod,'_which',lambda *names: None)
    monkeypatch.setattr(mod,'_portal_python',lambda:'/usr/bin/python3')
    provider=mod.capture_provider()
    assert provider['name']=='xdg-desktop-portal'
    assert provider['session']=='wayland'


def test_portal_provider_uses_portal_capture_not_capture_command(tmp_path,monkeypatch):
    mod=load_vision()
    data=b'portal-frame'
    monkeypatch.setattr(mod,'capture_provider',lambda:{'name':'xdg-desktop-portal','tool':'/usr/bin/python3','platform':'linux','session':'wayland'})
    class Result:
        returncode=0
        stderr=b''
    def portal(provider,output):
        output.write_bytes(data)
        return Result()
    monkeypatch.setattr(mod,'_capture_portal',portal)
    monkeypatch.setattr(mod,'_capture_command',lambda *args: (_ for _ in ()).throw(AssertionError('X11 command path used')))
    monkeypatch.setattr(mod,'_compress',lambda source,dest,max_width,quality:(source,'image/png'))
    result=mod.capture_screen()
    assert result['ok'] is True
    assert base64.b64decode(result['image_base64'])==data
