import unittest
from unittest.mock import patch
from core import fabric_client

class FabricClientRoutingTests(unittest.TestCase):
    def test_latency_prefers_small_idle_worker(self):
        snap={"self":{"name":"local","inference":{"available":True,"models":[{"name":"big","size":20_000_000_000,"resident":True,"features":{"text":True}}]},"supervisor":{"active":None}},"peers":[{"dns":"m4.example","node":{"identity":{"name":"m4"},"inference":{"available":True,"models":[{"name":"small","size":2_000_000_000,"resident":True,"features":{"text":True}}]},"supervisor":{"active":None}}}]}
        with patch.object(fabric_client,"_nodes",return_value=snap):
            _,name,_,_=fabric_client.choose_node(latency=True)
        self.assertEqual(name,"m4")

    def test_busy_worker_loses_to_idle(self):
        snap={"self":{"name":"local","inference":{"available":True,"models":[{"name":"same","size":2,"resident":True,"features":{"text":True}}]},"supervisor":{"active":{"id":"x"}}},"peers":[{"dns":"peer.example","node":{"identity":{"name":"peer"},"inference":{"available":True,"models":[{"name":"same","size":2,"resident":True,"features":{"text":True}}]},"supervisor":{"active":None}}}]}
        with patch.object(fabric_client,"_nodes",return_value=snap):
            _,name,_,_=fabric_client.choose_node(model="same")
        self.assertEqual(name,"peer")

    def test_choose_node_api_stays_four_tuple(self):
        with patch.object(fabric_client, "_nodes", return_value={"self":{"name":"m4","inference":{"available":True,"models":[{"name":"tiny","size":2,"features":{"text":True}}]},"supervisor":{"active":None}},"peers":[]}):
            self.assertEqual(len(fabric_client.choose_node()), 4)

class FabricClientPlacementTests(unittest.TestCase):
    def test_exclude_skips_failed_worker(self):
        snap={"self":{"name":"local","inference":{"available":True,"models":[{"name":"m","size":2,"features":{"text":True}}]},"supervisor":{"active":None}},"peers":[{"dns":"peer.example","node":{"identity":{"name":"peer"},"inference":{"available":True,"models":[{"name":"m","size":2,"features":{"text":True}}]},"supervisor":{"active":None}}}]}
        with patch.object(fabric_client,"_nodes",return_value=snap):
            _,name,_,_=fabric_client.choose_node(model="m", exclude={"local"})
        self.assertEqual(name,"peer")

    def test_infer_submits_to_selected_worker(self):
        calls=[]
        def fake_json(url,payload=None,timeout=5.0):
            calls.append(url)
            if url.endswith('/v1/nodes'):
                return {"self":{"name":"origin","inference":{"available":True,"models":[]}},"peers":[{"dns":"worker.example","node":{"identity":{"name":"worker"},"inference":{"available":True,"preferred_model":"m","models":[{"name":"m","size":2,"features":{"text":True}}]},"supervisor":{"active":None}}}]}
            if url.endswith('/v1/jobs'):
                return {"job":{"id":"j1"}}
            if url.endswith('/v1/jobs/j1'):
                return {"status":"ok","result":{"work":{"output":{"message":{"content":"ok"}}}}}
            raise AssertionError(url)
        with patch.object(fabric_client,"_json",side_effect=fake_json):
            out=fabric_client.infer([{"role":"user","content":"hi"}],model="m",timeout=1)
        self.assertEqual(out["fabric_node"],"worker")
        self.assertIn('https://worker.example:7332/v1/jobs',calls)
