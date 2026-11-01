import hashlib
import io
import json
from pathlib import Path
import tarfile
from unittest.mock import Mock

import pytest
from core import mercury_install as installer
from test_mercury_integration import request


def archive_bytes():
    output=io.BytesIO()
    with tarfile.open(fileobj=output,mode='w:gz') as archive:
        info=tarfile.TarInfo('release/install_core.py');data=b'# verified source\n';info.size=len(data)
        archive.addfile(info,io.BytesIO(data))
    return output.getvalue()


def test_pins_match_verified_companion_archive():
    pin=json.loads((Path(__file__).resolve().parents[1]/'integrations/mercury.json').read_text())
    assert installer.REVISION==pin['revision']
    assert installer.ARCHIVE_SHA256==pin['sha256']


def test_paired_install_route_requires_explicit_confirmation(monkeypatch):
    from core import node
    operation=Mock();monkeypatch.setattr(node.mercury_install,'schedule',operation)
    reply=request('/v1/mercury/install',plane='ingress',authorized=False)
    operation.assert_not_called()
    reply=request('/v1/mercury/install',plane='ingress')
    operation.assert_called_once_with(confirm=None,enable_sync=False)
    assert reply.call_args.args[0]==202


def test_schedule_does_not_install_without_confirmation(tmp_path,monkeypatch):
    monkeypatch.setattr(installer,'root',lambda:tmp_path)
    spawn=Mock();monkeypatch.setattr(installer.subprocess,'Popen',spawn)
    with pytest.raises(PermissionError):installer.schedule()
    spawn.assert_not_called()


def test_helper_uses_existing_modern_python_instead_of_old_node_interpreter(monkeypatch):
    monkeypatch.setattr(installer.sys,'executable','/usr/bin/python3')
    monkeypatch.setattr(installer.shutil,'which',lambda name:'/usr/bin/python3')
    monkeypatch.setattr(installer.Path,'is_file',lambda path:True)
    run=Mock(side_effect=lambda command,**kwargs:type('Result',(),{'returncode':0 if command[0]=='/opt/homebrew/bin/python3' else 1})())
    monkeypatch.setattr(installer.subprocess,'run',run)
    assert installer.python_runtime()=='/opt/homebrew/bin/python3'


def test_missing_modern_python_fails_before_app_changes(monkeypatch):
    monkeypatch.setattr(installer.Path,'is_file',lambda path:False)
    with pytest.raises(RuntimeError,match='unchanged'):installer.python_runtime()


@pytest.mark.parametrize('kind',['traversal','symlink'])
def test_archive_refuses_paths_and_symlinks(tmp_path,kind):
    archive=tmp_path/'bad.tar.gz'
    with tarfile.open(archive,'w:gz') as source:
        entry=tarfile.TarInfo('../private' if kind=='traversal' else 'release/link')
        if kind=='symlink':entry.type=tarfile.SYMTYPE;entry.linkname='/private'
        source.addfile(entry)
    target=tmp_path/'out';target.mkdir()
    with pytest.raises(ValueError,match='Unsafe'):installer.extract(archive,target)


@pytest.mark.parametrize('failure',[False,True])
def test_upgrade_preserves_manuscripts_and_retains_rollback_copy(tmp_path,monkeypatch,failure):
    app=tmp_path/'app';app.mkdir();(app/'mercury_server.py').write_text('old runtime')
    (app/'library').mkdir();(app/'library/project.mercury').write_text('precious manuscript')
    (app/'mercury_config.json').write_text('personal settings')
    root=tmp_path/'jobs';folder=root/'one';folder.mkdir(parents=True);(folder/'go').touch()
    monkeypatch.setattr(installer,'root',lambda:root);monkeypatch.setattr(installer,'app_root',lambda:app)
    installer.atomic(root/'status.json',{'state':'staged'})
    data=archive_bytes();monkeypatch.setattr(installer,'ARCHIVE_SHA256',hashlib.sha256(data).hexdigest())
    monkeypatch.setattr(installer.urllib.request,'urlopen',lambda *args,**kwargs:io.BytesIO(data))
    monkeypatch.setattr(installer,'stop_existing',Mock());monkeypatch.setattr(installer,'configure_service',Mock())
    services=Mock();monkeypatch.setattr(installer,'service',services)
    def apply(*args,**kwargs):(app/'mercury_server.py').write_text('new runtime')
    monkeypatch.setattr(installer.subprocess,'run',apply)
    calls=[]
    def api(path,payload=None,**kwargs):
        calls.append((path,payload))
        if failure:raise RuntimeError('verification failed')
        if path=='/api/version':return {'version':installer.VERSION}
        return {'enabled':True,'offline':[{'ready':True}],'conflicts':[]}
    monkeypatch.setattr(installer,'api',api)
    installer.run(folder,True)
    receipt=installer.status()
    assert receipt['state']==('failed' if failure else 'healthy')
    assert (app/'library/project.mercury').read_text()=='precious manuscript'
    assert (app/'mercury_config.json').read_text()=='personal settings'
    assert (folder/'previous-app/mercury_server.py').read_text()=='old runtime'
    assert (app/'mercury_server.py').read_text()==('old runtime' if failure else 'new runtime')
    if failure:assert (folder/'failed-app/mercury_server.py').read_text()=='new runtime'
    else:assert ('/api/sync/config',{'enabled':True}) in calls
