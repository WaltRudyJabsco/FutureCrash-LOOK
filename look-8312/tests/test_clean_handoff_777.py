from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LK=(ROOT/'look/lk').read_text()
INSTALL=(ROOT/'install-look.sh').read_text()
RENDER=(ROOT/'look/look_renderer.py').read_text()


def test_playerctl_is_not_linuxbrew_core_dependency():
    core_block=INSTALL.split('core=(',1)[1].split('missing=()',1)[0]
    assert 'core+=(playerctl)' not in core_block
    assert 'sudo apt-get install -y playerctl' in INSTALL
    assert 'sudo dnf install -y playerctl' in INSTALL
    assert 'sudo pacman -S --noconfirm playerctl' in INSTALL
    assert 'Optional playerctl install failed; LOOK media remains available.' in INSTALL


def test_mpv_ipc_liveness_is_not_idle_value_truthiness():
    block=LK.split('def _media_mpv_alive():',1)[1].split('def _media_mpv_loaded():',1)[0]
    assert 'result.get("error")=="success"' in block
    assert 'bool(_media_mpv_request' not in block
    loaded=LK.split('def _media_mpv_loaded():',1)[1].split('def _media_wait_for_mpv_loaded',1)[0]
    assert 'idle is False' in loaded


def test_saved_queue_cannot_steal_transport():
    block=LK.split('# Transport follows a real player session',1)[1].split('# --- Starter control surfaces',1)[0]
    assert 'playing_system=_media_system_owner(include_paused_owner=False)' in block
    assert 'if _media_mpv_loaded():' in block
    assert 'remembered_system=_media_system_owner(include_paused_owner=True)' in block
    assert 'if action=="play":' in block
    assert 'no active media session' in block
    # No generic fallback may launch a saved queue for toggle/next/prev.
    assert 'result=_media_control_session(action)' not in block.split('if action=="play":',1)[1]


def test_loaded_receipt_required_before_claiming_look_owner():
    assert LK.count('if not _media_wait_for_mpv_loaded():') >= 2
    assert '_media_wait_for_mpv_start(proc, timeout=3.0)' in LK
    assert '_media_pause_playing_system()' in LK


def test_imagemagick7_jpeg_uses_magick_as_command_not_convert_subcommand():
    block=RENDER.split("convert=shutil.which('magick')",1)[1].split('if proc.returncode',1)[0]
    assert "cmd=[convert,str(path)+'[0]'" in block
    assert "cmd+=['convert']" not in block


def test_doctor_reports_http_source_receipt():
    block=LK.split('def _media_doctor():',1)[1].split('def _media_queue_has_video',1)[0]
    assert 'Range":"bytes=0-1023"' in block
    assert 'print(f"  http      {status}"' in block
    assert 'except urllib.error.HTTPError as exc:' in block
