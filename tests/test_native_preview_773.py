from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/'look'/'look_renderer.py').read_text()
ALBERT=(ROOT/'albert'/'install.sh').read_text()

def test_side_pane_reuses_native_adapter():
    assert "elif filtering and picked and width>=96:" in SRC
    assert "left_w+4,native_rows,right_w" in SRC

def test_kitty_is_a_native_driver_with_ascii_fallback():
    assert "self.driver='kitty'" in SRC
    assert "KITTY_WINDOW_ID" in SRC
    assert "\\x1b_Ga=T,t=f,f=100" in SRC
    assert "self.driver=None" in SRC

def test_worker_still_never_paints():
    worker=SRC[SRC.index('    def _worker(self)->None:'):SRC.index('    def _prepare(',SRC.index('    def _worker(self)->None:'))]
    assert 'sys.stdout' not in worker

def test_albert_launchagent_is_explicitly_started():
    assert 'launchctl kickstart -k "$DOMAIN/$LABEL"' in ALBERT
    assert 'launchctl bootstrap "$DOMAIN" "$PLIST"; then' in ALBERT
    assert 'launchctl print "gui/$(id -u)/com.futurecrash.albert"' in ALBERT


def test_native_invalid_image_keeps_ascii(monkeypatch,tmp_path,capsys):
    import look_renderer
    monkeypatch.setenv('LOOK_NATIVE_PREVIEW','off')
    controller=look_renderer.NativePreviewController()
    image=tmp_path/'wrong.png';image.write_bytes(b'JPEG not PNG')
    controller._ready=(controller._generation,image,1,1,10,30)
    controller.paint_ready()
    assert capsys.readouterr().out==''


def test_mac_native_conversion_is_real_png(tmp_path,monkeypatch):
    import sys,subprocess,look_renderer
    import pytest
    if sys.platform!='darwin':pytest.skip('requires macOS sips')
    import struct,zlib
    monkeypatch.setenv('LOOK_NATIVE_PREVIEW','off')
    monkeypatch.setattr(Path,'home',lambda:tmp_path)
    seed=tmp_path/'seed.png'
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
    seed.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',32,32,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+b'\xff\0\0'*32)*32))+chunk(b'IEND',b''))
    image=tmp_path/'art.jpg'
    subprocess.run(['/usr/bin/sips','-s','format','jpeg',str(seed),'--out',str(image)],check=True,capture_output=True)
    controller=look_renderer.NativePreviewController();controller.driver='kitty'
    result=controller._prepare(image,image.stat().st_mtime_ns,10,30)
    assert result and controller._png_dimensions(result)==(540,540)
