from pathlib import Path
import importlib.util
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('memory_store_661', ROOT/'core'/'memory_store.py')
mem=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(mem)


def test_memory_store_has_machine_native_atoms_and_large_budget():
    assert mem.VERSION == 2
    assert mem.MAX_ATOMS >= 4096
    with tempfile.TemporaryDirectory() as td:
        store=mem.FabricMemory(Path(td)/'memory.json')
        a=store.add_atom('shared','resolver','stones','resolves_to','The Rolling Stones',92,'m4')
        b=store.add_atom('shared','resolver','stones','resolves_to','The Rolling Stones',92,'m4')
        assert a['id']==b['id']
        assert store.public(include_local=False)['atoms'][0]['u']==2


def test_machine_atoms_merge_across_fabric_scope():
    with tempfile.TemporaryDirectory() as td:
        store=mem.FabricMemory(Path(td)/'memory.json')
        result=store.merge_atoms([
            {'scope':'shared','k':'action','s':'media_play','r':'succeeded_for','v':'play The Clash','c':100,'u':1,'updated_at':10},
            {'scope':'node:other','k':'fact','s':'private','v':'nope','c':80,'updated_at':10},
        ])
        assert result['count']==1
        assert store.public(include_local=False)['atoms'][0]['s']=='media_play'


def test_lk_has_social_zero_tool_and_continuation_state():
    text=(ROOT/'look'/'lk').read_text()
    assert 'def _lo_social_ack' in text
    assert 'pending_media_clarification' in text
    assert 'continuation_of=dict(pending_media_clarification)' in text
    assert 'Pure acknowledgement is a zero-tool turn' in text


def test_receipt_authority_includes_media_and_speech():
    text=(ROOT/'look'/'lk').read_text()
    assert 'authoritative_action_tools={' in text
    assert '"media_play"' in text
    assert '"audio_speak"' in text
    assert 'not authoritative_action_success' in text


def test_memory_schema_four_is_generous_but_retrieval_bounded():
    text=(ROOT/'look'/'lk').read_text()
    assert 'MEMORY_SCHEMA_VERSION=4' in text
    assert 'MEMORY_CANDIDATE_LIMIT=128' in text
    assert 'MEMORY_DURABLE_LIMIT=1024' in text
    assert 'MEMORY_ATOM_LIMIT=4096' in text
    assert 'MEMORY_RETRIEVED_MACHINE_ATOMS=24' in text
    assert '45*60' in text


def test_memory_learned_projection_exists():
    text=(ROOT/'look'/'lk').read_text()
    assert 'args[0]=="learned"' in text
    assert 'MACHINE ATOMS' in text
    assert 'memory is cheap; attention is budgeted' in text


def test_node_syncs_machine_atoms_with_prose_memory():
    text=(ROOT/'core'/'node.py').read_text()
    assert 'combined_atoms' in text
    assert 'FABRIC_MEMORY.merge_atoms' in text
    assert '"atoms": union_atoms' in text
