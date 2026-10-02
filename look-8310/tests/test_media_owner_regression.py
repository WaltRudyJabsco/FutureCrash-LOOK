import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LK=(ROOT/'look'/'lk').read_text(encoding='utf-8')
INSTALL=(ROOT/'install.sh').read_text(encoding='utf-8')
SERVER=(ROOT/'local-labs-host'/'server.py').read_text(encoding='utf-8')

class MediaOwnerRegressionTests(unittest.TestCase):
    def test_owned_mpv_identity_is_exact_ipc_marker(self):
        self.assertIn('def _media_owned_mpv_pids():',LK)
        self.assertIn('marker=f"--input-ipc-server={MEDIA_IPC_FILE}"',LK)
        self.assertNotIn('killall mpv',LK)

    def test_reuse_happens_before_stale_socket_unlink(self):
        launch=LK.index('def _media_launch_session(session):')
        stream=LK.index('def _media_launch_stream(',launch)
        body=LK[launch:stream]
        self.assertLess(body.index('if _media_mpv_alive():'),body.index('MEDIA_IPC_FILE.unlink(missing_ok=True)'))
        self.assertIn('_media_stop_owned_mpvs()',body)

    def test_stop_reaps_orphaned_look_players(self):
        control=LK.index('def _media_control_session(action):')
        body=LK[control:LK.index('def _media_repeat_command',control)]
        self.assertGreaterEqual(body.count('_media_stop_owned_mpvs()'),2)

    def test_next_album_is_deterministic(self):
        self.assertIn('"next album":"next_album"',LK)
        self.assertIn('"go to the next album":"next_album"',LK)

    def test_server_upgrade_normalizes_canonical_controller(self):
        self.assertIn('ln -sfn "$HOME/.local/share/local-labs-host/server.py" "$HOME/.local/bin/server"',INSTALL)
        self.assertIn('id="openjev"',SERVER)

if __name__=='__main__': unittest.main()
