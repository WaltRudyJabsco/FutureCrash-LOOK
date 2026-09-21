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
    assert "statistics.median" in block
    assert "physical ceiling" in block
    assert "range(3)" in block


def test_ollama_test_exposes_resident_set_flag():
    assert '"--resident-set" in rest[1:]' in SOURCE


def test_all_model_sweep_isolated_and_restores_residency():
    start=SOURCE.index("def ollama_test(all_models=False")
    end=SOURCE.index("def ollama_test_resident_set(",start)
    block=SOURCE[start:end]
    assert "isolated=bool(all_models)" in block
    assert "_benchmark_guard(True)" in block
    assert "_benchmark_one_model(base,model,isolated=isolated)" in block
    assert "_restore_resident_set(base,resident_before)" in block
    assert "_benchmark_guard(False)" in block


def test_isolated_benchmark_stabilizes_then_uses_three_warm_samples():
    start=SOURCE.index("def _benchmark_one_model(")
    end=SOURCE.index("def _benchmark_runtime_fit(",start)
    block=SOURCE[start:end]
    assert '"options":{"num_ctx":4096}' in block
    assert "_benchmark_speed(base,model)" in block
    assert "for _ in range(3)" in block
    assert "statistics.median" in block
    assert 'results["load_s"]' in block
    assert 'results["gpu_pct"]' in block
