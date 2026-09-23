from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[1]

spec=importlib.util.spec_from_file_location("media_core", ROOT/"look"/"media_core.py")
media_core=importlib.util.module_from_spec(spec)
spec.loader.exec_module(media_core)


def test_artist_article_is_conversational_not_catalog_identity():
    lib={"entries":[
        {"path":"/music/talking.mp3","artist":"Talking Heads","album":"Remain in Light","title":"Once in a Lifetime"},
        {"path":"/music/beatles.mp3","artist":"The Beatles","album":"Abbey Road","title":"Because"},
    ]}
    assert media_core.resolve_query(lib,"the talking heads")[0]["artist"] == "Talking Heads"
    assert media_core.resolve_query(lib,"beatles")[0]["artist"] == "The Beatles"


def test_player_source_resolver_uses_merged_locations_and_reports_failures():
    text=(ROOT/"look"/"lk").read_text()
    source_block=text[text.index("def _media_entry_source"):text.index("def _media_mpv_binary")]
    assert 'for loc in entry.get("locations") or []:' in source_block
    assert 'for label,error in missing[:5]:' in text


def test_lo_explicit_lk_command_bypasses_inference():
    text=(ROOT/"look"/"lk").read_text()
    assert 'if prompt == "lk" or prompt.startswith("lk "):' in text
    assert 'subprocess.run([exe,*argv])' in text
    assert 'nested `lk lo` is disabled' in text
