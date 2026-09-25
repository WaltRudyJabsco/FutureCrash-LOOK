from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def load_node():
    from core import node
    return node


def test_web_search_capability_is_explicit(monkeypatch):
    node=load_node()
    monkeypatch.setattr(node,"binary",lambda name: None)
    monkeypatch.setattr(node,"probe",lambda host,port: port==8888)
    assert node.capabilities()["web.search"] is True


def test_local_web_search_normalizes_results(monkeypatch):
    node=load_node()
    monkeypatch.setattr(node,"identity",lambda:{"name":"test-node"})
    class Response:
        def __enter__(self): return self
        def __exit__(self,*a): pass
        def read(self,n=-1): return b'{"results":[{"title":"  Result  ","url":"https://example.test","content":"lots   of   space"}]}'
    monkeypatch.setattr(node.urllib.request,"urlopen",lambda *a,**k: Response())
    result=node._local_web_search("hello",8)
    assert result["provider"]=="searxng"
    assert result["results"][0]["title"]=="Result"
    assert result["results"][0]["content"]=="lots of space"


def test_readme_no_longer_starts_as_release_log():
    text=(ROOT/"README.md").read_text()
    assert text.startswith("# Future Crash + LOOK")
    assert "Accountless by default" not in text  # wording stays descriptive, not promotional boilerplate
    assert "accountless by default" in text.lower()
