import ast
from pathlib import Path


def _method_source(text, tree, name):
    api=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='API')
    method=next(node for node in api.body if isinstance(node,ast.FunctionDef) and node.name==name)
    return ast.get_source_segment(text,method) or ''


def test_endpoint_mutations_live_in_post_dispatcher():
    text=(Path(__file__).parents[1]/'core'/'node.py').read_text()
    tree=ast.parse(text)
    api=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='API')
    get=_method_source(text,tree,'do_GET')
    post_parts=[]
    for node in api.body:
        if isinstance(node,ast.FunctionDef) and (node.name=='do_POST' or node.name.startswith('_post_')):
            post_parts.append(ast.get_source_segment(text,node) or '')
    post='\n'.join(post_parts)
    for route in (
        '/v1/endpoints/fabric/allow',
        '/v1/endpoints/fabric/revoke',
        '/v1/endpoints/allow',
        '/v1/endpoints/revoke',
    ):
        assert route not in get
        assert route in post
