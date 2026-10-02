from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/'look'/'look_renderer.py').read_text()
ALBERT=(ROOT/'albert'/'install.sh').read_text()

def test_side_pane_reuses_native_adapter():
    assert "elif (cursoring or filtering or selecting) and picked and width>=96:" in SRC
    assert "left_w+4,max(2,list_usable-2),right_w" in SRC

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
