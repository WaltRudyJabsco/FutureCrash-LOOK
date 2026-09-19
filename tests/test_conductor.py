import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"core"))
from conductor import classify
import fabric_client

class ConductorTests(unittest.TestCase):
    def test_reflex(self):
        self.assertEqual(classify("what is the time?", requires=["text"]).tier, "reflex")
    def test_deep_code(self):
        self.assertEqual(classify("debug this Python traceback and explain the architecture", requires=["text","tools"]).tier, "deep")
    def test_vision_is_deep(self):
        self.assertEqual(classify("what is this?", requires=["text","vision"], has_images=True).tier, "deep")
    def test_reflex_prefers_small_warm_measured_model(self):
        snap={"self":{"name":"small","runtime":{"ok":True},"inference":{"available":True,"preferred_model":"tiny","models":[{"name":"tiny","size":2_000_000_000,"resident":True,"features":{"text":True},"qualification":{"ttft_ms":100,"generation_tok_s":100}}]},"supervisor":{"active":None}},"peers":[{"name":"big","dns":"big.ts.net","node":{"runtime":{"ok":True},"inference":{"available":True,"preferred_model":"big","models":[{"name":"big","size":20_000_000_000,"resident":True,"features":{"text":True},"qualification":{"ttft_ms":120,"generation_tok_s":60}}]},"supervisor":{"active":None}}}]}
        _,name,_,models=fabric_client._choose_from_snapshot(snap,requires=["text"],tier="reflex")
        self.assertEqual(name,"small")
        self.assertEqual(models[0]["name"],"tiny")
    def test_deep_prefers_capacity_when_latency_is_close(self):
        snap={"self":{"name":"small","runtime":{"ok":True},"inference":{"available":True,"models":[{"name":"tiny","size":2_000_000_000,"resident":True,"features":{"text":True},"qualification":{"ttft_ms":100,"generation_tok_s":80}}]},"supervisor":{"active":None}},"peers":[{"name":"big","dns":"big.ts.net","node":{"runtime":{"ok":True},"inference":{"available":True,"models":[{"name":"big","size":20_000_000_000,"resident":True,"features":{"text":True},"qualification":{"ttft_ms":120,"generation_tok_s":80}}]},"supervisor":{"active":None}}}]}
        _,name,_,_=fabric_client._choose_from_snapshot(snap,requires=["text"],tier="deep")
        self.assertEqual(name,"big")

if __name__=='__main__': unittest.main()
