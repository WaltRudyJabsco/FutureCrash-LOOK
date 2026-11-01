import hashlib
import io
from pathlib import Path
import tarfile
from unittest.mock import Mock
import pytest
import book_native


def package(binary=b'fixture',link=False):
    raw=io.BytesIO()
    with tarfile.open(fileobj=raw,mode='w:gz') as archive:
        for name,data in [('bookokrat',binary),('LICENSE',b'License'),('SOURCE.txt',(book_native.REPOSITORY+'\ncommit\n').encode())]:
            info=tarfile.TarInfo(name);info.size=len(data)
            if name=='bookokrat' and link:info.type=tarfile.SYMTYPE;info.linkname='/outside'
            archive.addfile(info,io.BytesIO(data))
    data=raw.getvalue();return data,{'sha256':hashlib.sha256(data).hexdigest(),'commit':'commit'}


def test_verified_native_package_installs_beside_standard_reader(tmp_path,monkeypatch):
    data,build=package();run=Mock(return_value=Mock(stdout='bookokrat '+book_native.VERSION))
    monkeypatch.setattr(book_native.subprocess,'run',run)
    destination=tmp_path/'native'/book_native.VERSION
    book_native.install_package(data,build,destination)
    assert (destination/'bookokrat').read_bytes()==b'fixture'
    assert (destination/'LICENSE').is_file() and (destination/'SOURCE.txt').is_file()
    assert (destination/'install.json').is_file()
    assert run.call_args.args[0][1:] == ['--version']
    with pytest.raises(ValueError,match='retained'):book_native.install_package(data,build,destination)


def test_native_installer_rejects_tampered_bytes_and_symlinks(tmp_path):
    data,build=package()
    with pytest.raises(ValueError,match='verification'):book_native.install_package(data+b'changed',build,tmp_path/'bad')
    data,build=package(link=True)
    with pytest.raises(ValueError,match='invalid member'):book_native.install_package(data,build,tmp_path/'bad')
    assert not (tmp_path/'bad').exists()
