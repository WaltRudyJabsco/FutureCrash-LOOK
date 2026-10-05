from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def test_signal_native_lo_keeps_generated_artifact_path_in_answer_contract():
    text=(ROOT/'signal-window'/'server.py').read_text()
    assert 'preserve the exact saved path from the tool result in the final answer' in text


def test_fabric_client_remote_requests_own_node_auth():
    text=(ROOT/'core'/'fabric_client.py').read_text()
    assert 'headers.update(FABRIC_IDENTITY.auth_headers_for_url(url))' in text
    assert 'FABRIC_IDENTITY.ssl_context_for_url(url)' in text
    assert 'headers.update(FABRIC_IDENTITY.auth_headers_for_url(endpoint))' in text
