from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/"look"/"lk").read_text(encoding="utf-8")


def test_model_benchmark_has_reasoning_probes():
    assert "def _benchmark_reasoning(" in SOURCE
    assert 'results["reasoning"]' in SOURCE
    assert '"reasoning":row.get("reasoning")' in SOURCE


def test_resident_set_probe_never_cold_loads_models():
    start=SOURCE.index("def ollama_test_resident_set(")
    end=SOURCE.index("def _settings_share_state(",start)
    block=SOURCE[start:end]
    assert "_ollama_ps(base)" in block
    assert "ThreadPoolExecutor" in block
    assert "_ollama_set_model" not in block
    assert '"keep_alive":0' not in block


def test_ollama_test_exposes_resident_set_flag():
    assert '"--resident-set" in rest[1:]' in SOURCE
