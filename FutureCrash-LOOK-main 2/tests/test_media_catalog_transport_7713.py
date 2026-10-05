from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def _source_block():
    text=(ROOT/"look/lk").read_text()
    return text[text.index("def _media_entry_source"):text.index("def _media_wait_for_local_queue")]

def test_remote_catalog_id_precedes_checksum_artifact_transport():
    block=_source_block()
    item=block.index('if node and entry_id:')
    artifact=block.index('if node and _digest:')
    assert item < artifact
    assert '/v1/media/item?' in block

def test_artifact_fallback_remains_for_artifact_only_entries():
    block=_source_block()
    assert '/v1/media/artifact?' in block
