import importlib.machinery
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
LOADER = importlib.machinery.SourceFileLoader("look_lk_model_scope", str(ROOT / "look" / "lk"))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
look = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(look)


class ModelScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        state = Path(self.tmp.name)
        self.old_model_file = look.OLLAMA_MODEL_FILE
        self.old_host_models_file = look.OLLAMA_HOST_MODELS_FILE
        look.OLLAMA_MODEL_FILE = state / "ollama_model"
        look.OLLAMA_HOST_MODELS_FILE = state / "ollama_host_models.json"

    def tearDown(self):
        look.OLLAMA_MODEL_FILE = self.old_model_file
        look.OLLAMA_HOST_MODELS_FILE = self.old_host_models_file
        self.tmp.cleanup()

    def test_remote_choice_does_not_overwrite_local_choice(self):
        look._save_active_ollama_model("small-local")
        remote = "https://3090.example.ts.net:11435"
        look._save_model_preference_for_base(remote, "big-remote")
        self.assertEqual(look._active_ollama_model(), "small-local")
        self.assertEqual(look._preferred_model_for_base(remote), "big-remote")

    def test_remote_without_preference_uses_resident_host_model(self):
        look._save_active_ollama_model("small-local")
        remote = "https://3090.example.ts.net:11435"
        selected = look._preferred_model_for_base(
            remote,
            installed=[{"name": "large-a"}, {"name": "large-b"}],
            running=[{"name": "large-b"}],
        )
        self.assertEqual(selected, "large-b")

    def test_stale_local_preference_is_labeled_unavailable(self):
        look._save_active_ollama_model("big-remote")
        with patch.object(look, "_ollama_tags", return_value=[{"name": "small-local"}]):
            self.assertEqual(look._local_model_label(), "big-remote · not installed locally")

    def test_local_picker_is_forced_to_local_endpoint(self):
        seen = {}
        with patch.object(look, "_ensure_ollama_server", return_value=[]), \
             patch.object(look, "_ollama_tags", return_value=[{"name": "small-local"}]), \
             patch.object(look, "_ollama_ps", return_value=[]), \
             patch.object(look, "_ollama_set_model", side_effect=lambda base, model: seen.update(base=base, model=model)), \
             patch.object(look, "_ollama_capabilities", return_value=["text"]):
            rc = look.ollama_models("small-local", base_override=look.LOCAL_OLLAMA_URL)
        self.assertEqual(rc, 0)
        self.assertEqual(seen["base"], look.LOCAL_OLLAMA_URL)
        self.assertEqual(seen["model"], "small-local")

    def test_local_model_is_not_portable_profile_state(self):
        self.assertNotIn("ollama_model", look.PROFILE_STATE_FILES)


if __name__ == "__main__":
    unittest.main()
