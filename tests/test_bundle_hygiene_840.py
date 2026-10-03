from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_release_has_package_hygiene_policy():
    install=(ROOT/'install.sh').read_text()
    assert '8.5.4' in install
    # Packaging is built from an explicit cleaned staging tree; pycache is never runtime input.
    assert (ROOT/'look/media_art.py').is_file()
