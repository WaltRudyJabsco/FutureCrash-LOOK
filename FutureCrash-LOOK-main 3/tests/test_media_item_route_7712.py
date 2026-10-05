from pathlib import Path

def test_remote_media_item_stays_item_across_proxy_hop():
    src=Path("core/node.py").read_text(encoding="utf-8")
    start=src.index("    def _serve_media_item(")
    end=src.index("\n    def ",start+8)
    block=src[start:end]
    assert 'url=base+"/v1/media/item?"+urllib.parse.urlencode(params)' in block
    assert 'url=base+"/v1/media/audio?"+urllib.parse.urlencode(params)' not in block

def test_working_special_media_commands_remain_intact():
    src=Path("look/lk").read_text(encoding="utf-8")
    assert 'raw in {"classics","classical"}' in src
    assert 'https://allclassical.streamguys1.com/ac128kmp3' in src
    assert 'raw in {"arts","showcase","classic-arts"}' in src
    assert 'https://www.classicartsshowcase.org/watch-classic-arts-showcase/' in src
