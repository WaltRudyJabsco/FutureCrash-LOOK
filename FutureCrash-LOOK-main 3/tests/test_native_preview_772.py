from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/'look'/'look_renderer.py').read_text()


def test_native_preview_is_progressive_not_a_second_pager():
    assert 'class NativePreviewController' in SRC
    assert "self.driver='iterm'" in SRC
    assert 'A preview completion is not a pager event' in SRC
    assert 'on_wakeup=native_preview.paint_ready' in SRC


def test_native_preview_has_latest_wins_and_kill_switch():
    assert "LOOK_NATIVE_PREVIEW" in SRC
    assert 'while True: self._jobs.get_nowait()' in SRC
    assert 'generation!=self._generation' in SRC


def test_native_preview_keeps_preview_view_proof_path():
    request='native_preview.request(picked,len(context_rows)+3,1,max(2,list_usable-2),width)'
    assert request in SRC


def test_worker_never_writes_terminal():
    worker=SRC[SRC.index('    def _worker(self)->None:'):SRC.index('    def _prepare(',SRC.index('    def _worker(self)->None:'))]
    assert 'sys.stdout' not in worker
    assert 'os.write(self._wfd' in worker
