from pathlib import Path


def test_endpoint_mutations_live_in_post_dispatcher():
    text=(Path(__file__).parents[1]/"core"/"node.py").read_text()
    get=text.split("    def do_GET(self):",1)[1].split("    def do_POST(self):",1)[0]
    post=text.split("    def do_POST(self):",1)[1]
    for route in (
        "/v1/endpoints/fabric/allow",
        "/v1/endpoints/fabric/revoke",
        "/v1/endpoints/allow",
        "/v1/endpoints/revoke",
    ):
        assert route not in get
        assert route in post
