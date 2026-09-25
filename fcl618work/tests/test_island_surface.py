from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LK=(ROOT/"look"/"lk").read_text()

def test_island_doctor_is_public_and_local_first():
    assert 'def doctor_island()' in LK
    assert 'http://127.0.0.1:11434' in LK
    assert '("127.0.0.1",8791)' in LK
    assert 'lk doctor island' in LK
    assert 'return doctor_island() if rest and rest[0]=="island" else doctor()' in LK
