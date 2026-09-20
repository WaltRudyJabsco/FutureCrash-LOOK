import unittest
from unittest import mock
from core import node


class ModelCuratorTests(unittest.TestCase):
    def setUp(self):
        self.models=[
            {"name":"tiny:1b","size":1*1024**3,"resident":False,"features":{"text":True},
             "benchmark":{"fit":"EXCELLENT","ttft":0.2,"rate":120.0,"reasoning":1,"tools":1,"agent":False,"exact":True}},
            {"name":"middle:8b","size":6*1024**3,"resident":False,"features":{"text":True},
             "benchmark":{"fit":"GOOD","ttft":0.8,"rate":65.0,"reasoning":3,"tools":3,"agent":True,"exact":True}},
            {"name":"deep:27b","size":18*1024**3,"resident":False,"features":{"text":True},
             "benchmark":{"fit":"GOOD","ttft":1.2,"rate":45.0,"reasoning":3,"tools":3,"agent":True,"exact":True}},
        ]
        self.budget={"kind":"vram","total":24*1024**3,"used":0,"external":0,"reserve":1*1024**3,"model_budget":16*1024**3}

    def test_balanced_prefers_medium_plus_small(self):
        with mock.patch.object(node,"_gpu_budget",return_value=self.budget), \
             mock.patch.object(node,"_curator_disabled_models",return_value=set()):
            plan=node.curator_plan("balanced",models=self.models)
        self.assertEqual(plan["target"],["middle:8b","tiny:1b"])

    def test_deep_large_worker_runs_alone(self):
        with mock.patch.object(node,"_gpu_budget",return_value=self.budget), \
             mock.patch.object(node,"_curator_disabled_models",return_value=set()):
            plan=node.curator_plan("deep",models=self.models)
        self.assertEqual(plan["target"],["deep:27b"])

    def test_reflex_prefers_small_responsive_worker(self):
        with mock.patch.object(node,"_gpu_budget",return_value=self.budget), \
             mock.patch.object(node,"_curator_disabled_models",return_value=set()):
            plan=node.curator_plan("reflex",models=self.models)
        self.assertEqual(plan["target"],["tiny:1b"])


if __name__ == "__main__":
    unittest.main()
