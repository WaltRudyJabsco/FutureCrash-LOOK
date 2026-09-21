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
        self.assertEqual(sum(url.endswith('/v1/nodes') for url in calls),1,
                         'one placement must consume one routing snapshot')

class FabricVisionArtifactTests(unittest.TestCase):
    def test_image_blobs_stage_as_artifact_refs(self):
        import base64
        calls=[]
        encoded=base64.b64encode(b'not-really-a-png').decode('ascii')
        def fake_json(url,payload=None,timeout=5.0):
            calls.append((url,payload))
            return {"artifact":{"digest":"sha256:"+"a"*64}}
        payload={"messages":[{"role":"user","content":"what is this","images":[encoded]}]}
        with patch.object(fabric_client,"_json",side_effect=fake_json):
            messages,refs=fabric_client._stage_image_artifacts(payload,"http://worker:7332")
        self.assertNotIn("images",messages[0])
        self.assertEqual(messages[0]["image_artifacts"],refs)
        self.assertEqual(len(refs),1)
        self.assertTrue(calls[0][0].endswith('/v1/artifacts'))

class FabricBusyGraceTests(unittest.TestCase):
    def test_interactive_busy_worker_gets_bounded_retry(self):
        import io, urllib.error

        snap={"self":{"name":"local","inference":{"available":True,"preferred_model":"m","models":[{"name":"m","size":2,"resident":True,"features":{"text":True}}]},"supervisor":{"active":None}},"peers":[]}
        calls={"n":0}

        class Headers(dict):
            def get(self,key,default=None): return super().get(key,default)

        class Response:
            headers=Headers({"X-Fabric-Node":"local"})
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def __iter__(self):
                yield b'{"message":{"role":"assistant","content":"ok"},"done":true}\n'

        def fake_urlopen(req, timeout=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise urllib.error.HTTPError(req.full_url,409,"busy",{},io.BytesIO(b'{"error":"worker busy"}'))
            return Response()

        payload={"model":"m","messages":[{"role":"user","content":"hi"}],"options":{}}
        with patch.object(fabric_client,"_nodes",return_value=snap), \
             patch.object(fabric_client.urllib.request,"urlopen",side_effect=fake_urlopen), \
             patch.object(fabric_client.time,"sleep",return_value=None):
            events=list(fabric_client.stream_infer(payload,timeout=1))
        self.assertGreaterEqual(calls["n"],2)
        self.assertTrue(any(e.get("done") for e in events if isinstance(e,dict)))
