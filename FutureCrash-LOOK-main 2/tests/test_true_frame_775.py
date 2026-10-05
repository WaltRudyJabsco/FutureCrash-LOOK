from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INSTALL=(ROOT/'install.sh').read_text()
RENDERER=(ROOT/'look'/'look_renderer.py').read_text()

def test_macos_ingress_bootstrap_is_hard_failure_and_kickstarted():
    assert 'if ! launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.futurecrash.look.ingress.plist"' in INSTALL
    assert 'launchctl kickstart -k "gui/$(id -u)/com.futurecrash.look.ingress"' in INSTALL

def test_ingress_failure_reports_its_own_lifecycle_and_port():
    assert 'com.futurecrash.look.ingress' in INSTALL
    assert 'recent ingress log:' in INSTALL
    assert 'future-crash-look/ingress.log' in INSTALL
    assert '-iTCP:7333' in INSTALL

def test_native_preview_reads_png_geometry_without_image_dependency():
    assert 'def _png_dimensions' in RENDERER
    assert "struct.unpack('>II',header[16:24])" in RENDERER

def test_native_preview_contains_and_centers_in_cell_geometry():
    assert 'def _contained_rect' in RENDERER
    assert 'scale=min((cols*cell_w)/image_w,(rows*cell_h)/image_h)' in RENDERER
    assert 'row+(rows-draw_rows)//2' in RENDERER
    assert 'col+(cols-draw_cols)//2' in RENDERER

def test_native_paint_uses_contained_rectangle_for_both_drivers():
    assert 'width={draw_cols};height={draw_rows};preserveAspectRatio=1' in RENDERER
    assert 'c={draw_cols},r={draw_rows},C=1,q=2' in RENDERER
