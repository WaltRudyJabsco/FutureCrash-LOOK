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
