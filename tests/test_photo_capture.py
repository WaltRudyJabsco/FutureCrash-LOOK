import io
import json
from pathlib import Path
import threading
import urllib.request
import urllib.error
from unittest.mock import Mock
import pytest
from PIL import Image
import photo_capture as photo

@pytest.fixture
def png():
    image=Image.new('RGB',(24,16),'red');output=io.BytesIO();image.save(output,format='PNG');return output.getvalue()


def test_save_photo_uses_existing_image_clipboard_and_private_shelf(tmp_path,monkeypatch,png):
    import clipboard_shelf,screen_shot,clipboard_items
    monkeypatch.setattr(clipboard_shelf,'directory',lambda:tmp_path/'clip')
    copy=Mock();monkeypatch.setattr(screen_shot,'copy_image',copy)
    result=photo.save_photo(png,tmp_path/'photos')
    path=Path(result['path'])
    assert path.read_bytes()==png and path.stat().st_mode&0o777==0o600
    assert result['shelf'] and result['clipboard'];copy.assert_called_once_with(path)
    shelf=clipboard_shelf.Shelf()
    try:assert clipboard_items.unpack(shelf.rows()[0][1])['data']==png
    finally:shelf.close()


def test_system_clipboard_failure_keeps_saved_photo_and_lk_clip(tmp_path,monkeypatch,png):
    import clipboard_shelf,screen_shot
    monkeypatch.setattr(clipboard_shelf,'directory',lambda:tmp_path/'clip')
    monkeypatch.setattr(screen_shot,'copy_image',Mock(side_effect=ValueError('Unavailable')))
    result=photo.save_photo(png,tmp_path/'photos')
    assert Path(result['path']).exists() and result['shelf'] and not result['clipboard']


def test_bad_image_rejected_before_writing(tmp_path):
    with pytest.raises(ValueError):photo.save_photo(b'not an image',tmp_path/'photos')
    assert not (tmp_path/'photos').exists()


def test_loopback_capture_requires_session_token_and_same_origin(tmp_path,monkeypatch,png):
    server=photo.CaptureServer(tmp_path/'photos')
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base='http://127.0.0.1:'+str(server.server_port)
    save=Mock(return_value={'path':'saved','shelf':True,'clipboard':True});monkeypatch.setattr(photo,'save_photo',save)
    def post(origin,token):
        return urllib.request.urlopen(urllib.request.Request(base+'/capture',data=png,headers={'Origin':origin,'X-LOOK-Photo-Token':token,'Content-Type':'image/png'}))
    try:
        for origin,token in [('https://other.example',server.token),(base,'wrong')]:
            with pytest.raises(urllib.error.HTTPError) as error:post(origin,token)
            assert error.value.code==403
        with post(base,server.token) as response:assert json.load(response)['clipboard']
        save.assert_called_once_with(png,tmp_path/'photos')
        request=urllib.request.Request(base+'/close',data=b'',headers={'Origin':base,'X-LOOK-Photo-Token':server.token})
        with urllib.request.urlopen(request) as response:assert json.load(response)['closed']
        assert server.finished.is_set()
    finally:server.shutdown();server.server_close()


def test_camera_javascript_compiles(tmp_path):
    import subprocess
    node='/Users/jreno/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
    if not Path(node).exists():pytest.skip('Node unavailable')
    path=tmp_path/'photo.js';path.write_text(photo.PAGE.split('<script>')[1].split('</script>')[0])
    subprocess.run([node,'--check',str(path)],check=True,capture_output=True)


def test_browser_cam_saves_to_host_shelf_without_touching_host_desktop(tmp_path,monkeypatch,png):
    from core import photo_web
    from types import SimpleNamespace
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    save=Mock(return_value={'path':'saved','shelf':True,'clipboard':False})
    monkeypatch.setattr(photo,'save_photo',save)
    handler=SimpleNamespace(headers={'Origin':'https://signal.example','Host':'signal.example','Content-Type':'image/png','Content-Length':str(len(png))},rfile=io.BytesIO(png))
    monkeypatch.setattr(photo_web,'send',lambda h,status,data:(status,data))
    code,data=photo_web.post(handler)
    assert code==200 and data['shelf']
    save.assert_called_once_with(png,tmp_path/'Pictures/LOOK Photos',system_clipboard=False)
    handler.headers['Origin']='https://other.example'
    with pytest.raises(ValueError):photo_web.post(handler)


@pytest.mark.parametrize('surface,handler_name',[('signal-window','App'),('albert','Handler')])
def test_cam_post_requires_existing_surface_authorization(tmp_path,monkeypatch,surface,handler_name):
    import importlib.util
    from core import photo_web
    root=Path(__file__).resolve().parents[1]
    monkeypatch.setenv('HOME',str(tmp_path))
    spec=importlib.util.spec_from_file_location('photo_surface_'+handler_name,root/surface/'server.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    handler=object.__new__(getattr(module,handler_name));handler.path='/api/photo'
    handler._require_endpoint=Mock(return_value=False)
    post=Mock(return_value='saved');monkeypatch.setitem(__import__('sys').modules,'photo_web',photo_web);monkeypatch.setattr(photo_web,'post',post)
    assert handler.do_POST() is None;post.assert_not_called()
    handler._require_endpoint.return_value=True
    assert handler.do_POST()=='saved'


def test_signal_theater_page_uses_signal_node_url(tmp_path,monkeypatch):
    import importlib.util,sys
    from core import theater_admin_web
    root=Path(__file__).resolve().parents[1];monkeypatch.setenv('HOME',str(tmp_path))
    spec=importlib.util.spec_from_file_location('photo_signal_theater',root/'signal-window/server.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    handler=object.__new__(module.App);handler.path='/theater';handler._require_endpoint=lambda _:True
    monkeypatch.setitem(sys.modules,'theater_admin_web',theater_admin_web)
    opened=Mock(return_value='opened');monkeypatch.setattr(theater_admin_web,'handle',opened)
    assert handler.do_GET()=='opened'
    opened.assert_called_once_with(handler,module.NODE_URL)
