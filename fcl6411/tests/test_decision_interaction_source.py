import pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class DecisionInteractionSourceTests(unittest.TestCase):
    def test_play_shorthand_routes_to_media(self):
        src=(ROOT/'look'/'lk').read_text()
        self.assertIn('if cmd=="play": return media(["play",*rest]) if rest else media(["play"])',src)
    def test_terminal_ask_polls_shared_decision(self):
        src=(ROOT/'core'/'node.py').read_text()
        self.assertIn('select.select([sys.stdin],[],[],0.25)',src)
        self.assertIn('Enter leaves it pending for Signal/Fabric',src)
if __name__=='__main__': unittest.main()
