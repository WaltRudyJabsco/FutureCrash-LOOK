from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def declared_version(rel: str) -> str:
    text = (ROOT / rel).read_text()
    match = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    assert match, f'{rel} has no VERSION declaration'
    return match.group(1)


def test_all_runtime_release_surfaces_match_root_version():
    expected = (ROOT / 'VERSION').read_text().strip()

    for rel in ('albert/VERSION',):
        assert (ROOT / rel).read_text().strip() == expected

    for rel in ('core/node.py', 'core/ingress.py', 'core/tailcat.py', 'core/rendezvous.py'):
        assert declared_version(rel) == expected, f'{rel} release mismatch'

    rendezvous_text = (ROOT / 'core/rendezvous.py').read_text()
    assert f'FCLRendezvous/{expected}' in rendezvous_text
