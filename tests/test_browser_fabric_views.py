import importlib.util
import io
import json
from pathlib import Path
import subprocess
from unittest.mock import Mock

import pytest
from core import browser_presentations as presentations, maintenance

ROOT=Path(__file__).resolve().parents[1]


def load(surface):
    spec=importlib.util.spec_from_file_location('browser_views_'+surface,ROOT/surface/'server.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    if surface=='signal-window': module.Handler=module.App
    return module


def test_unicode_spaces_and_tool_receipt_paths_are_presentable(tmp_path):
    source=tmp_path/'generated art 日本語.png';source.write_bytes(b'image')
    events=[{'event':'tool_result','tool':'generate_image','result':json.dumps({'path':str(source)},ensure_ascii=True)}]
    assert presentations.candidates('Saved '+str(source),events)==[source]
    assert presentations.candidates('No image produced',[])==[]
    assert presentations.candidates(str(source)+'.exe',[])==[]
    assert presentations.candidates(str(tmp_path/'missing.png'),[])==[]


def test_presentation_tokens_expire_and_do_not_disclose_paths(tmp_path,monkeypatch):
    source=tmp_path/'image.png';source.write_bytes(b'image')
    store=presentations.Presentations();ref=store.present(source)
    token=ref['url'].rsplit('/',1)[-1]
    assert str(tmp_path) not in json.dumps(ref) and ref['type']=='image/png'
    assert store.get(token)==source and store.get('not-a-token') is None
    monkeypatch.setattr(presentations.time,'time',lambda:store.rows[token][0]+1)
    assert store.get(token) is None


def test_albert_cognition_returns_image_artifact_not_worker_window(tmp_path,monkeypatch):
    server=load('albert')
    source=tmp_path/'new image.png';source.write_bytes(b'image')
    engine=type('Engine',(),{'route_intent':staticmethod(lambda query:'general')})
    monkeypatch.setattr(server,'_load_lo_engine',lambda:engine)
    monkeypatch.setattr(server,'cognition_json',lambda *args,**kw:{'text':'Saved '+str(source),'lo_events':[{'tool':'generate_image'}]})
    result=server.action('generate a picture of a reef')
    assert result['type']=='answer'
    assert result['artifacts'][0]['type']=='image/png'
    assert result['artifacts'][0]['url'].startswith('/api/present/')


@pytest.mark.parametrize('surface',['signal-window','albert'])
@pytest.mark.parametrize('path',['/api/fabric','/api/fabric/care','/api/present/test'])
def test_browser_routes_require_endpoint_authorization(surface,path,monkeypatch):
    server=load(surface);handler=server.Handler.__new__(server.Handler)
    handler.path=path;handler._require_endpoint=Mock(return_value=False)
    handler._media_ticket_allows=Mock(return_value=False)
    get=Mock();monkeypatch.setattr(server,'_node_get' if surface=='signal-window' else 'node_json',get)
    handler.do_GET()
    handler._require_endpoint.assert_called_once()
    get.assert_not_called()


@pytest.mark.parametrize('surface',['signal-window','albert'])
def test_dashboard_care_is_get_only_and_reports_unavailability(surface,monkeypatch):
    server=load(surface);handler=server.Handler.__new__(server.Handler)
    handler.path='/api/fabric/care';handler._require_endpoint=Mock(return_value=True)
    handler._media_ticket_allows=Mock(return_value=False)
    send=Mock();setattr(handler,'json' if surface=='signal-window' else 'send_json',send)
    getter=Mock(return_value={'nodes':[{'node':'laptop','errors':[{'check':'release','error':'offline'}]}]})
    monkeypatch.setattr(server,'_node_get' if surface=='signal-window' else 'node_json',getter)
    handler.do_GET()
    getter.assert_called_once_with('/v1/care',timeout=90)
    assert send.call_args.args[0]==200
    assert send.call_args.args[1]['nodes'][0]['errors']


@pytest.mark.parametrize('surface',['signal-window','albert'])
def test_presented_image_is_authenticated_and_serves_bytes(surface,tmp_path,monkeypatch):
    server=load(surface);store=server._PRESENTATIONS if surface=='signal-window' else server.PRESENTATIONS
    source=tmp_path/'generated.png';source.write_bytes(b'PNG image payload')
    handler=server.Handler.__new__(server.Handler);handler.path=store.present(source)['url']
    handler._require_endpoint=Mock(return_value=True);handler._media_ticket_allows=Mock(return_value=False)
    handler.send_response=Mock();handler.send_header=Mock();handler.end_headers=Mock();handler.wfile=io.BytesIO()
    handler.do_GET()
    assert handler.wfile.getvalue()==source.read_bytes()
    assert ('Content-Type','image/png') in [call.args for call in handler.send_header.call_args_list]
    assert ('Content-Security-Policy','sandbox') in [call.args for call in handler.send_header.call_args_list]


def test_shared_assets_are_installed_and_allowed_for_managed_updates():
    for name in ('browser-views.js','fabric.html','fabric-dashboard.js'):
        assert name in (ROOT/'signal-window/install.sh').read_text()
        assert name in (ROOT/'albert/install.sh').read_text()
        assert maintenance.allowed('.local/share/signal-window/'+name)
        assert maintenance.allowed('.local/share/albert/'+name)


def test_browser_popups_commands_and_failure_fallbacks_in_javascript():
    helper=(ROOT/'signal-window/browser-views.js').read_text()
    script=r'''
const vm=require('vm'),assert=require('assert');
const navigations=[],tabs=[],opens=[];
const scope={URL,location:{href:'https://fabric.example/',origin:'https://fabric.example'},open:(...args)=>{
 opens.push(args);const tab={closed:false,document:{body:{}},location:{replace:url=>navigations.push(url)},close(){this.closed=true}};tabs.push(tab);return tab;
}};
vm.createContext(scope);vm.runInContext(HELPER,scope);const view=scope.FabricBrowserViews;
for(const query of ['/fabric','show fabric','Show our Fabric!','open the fabric dashboard'])assert.ok(view.fabricCommand(query));
for(const query of ['show fabric settings and update everyone','how do I show fabric','play fabric'])assert.ok(!view.fabricCommand(query));
assert.equal(view.openFabric(),'https://fabric.example/fabric.html');assert.deepEqual(opens[0],['https://fabric.example/fabric.html','_blank','noopener']);
const ref={artifacts:[{type:'image/png',name:'reef.png',url:'/api/present/secret'}]};
const request=view.beginImage('generate a picture of a reef');assert.equal(tabs.length,2);assert.equal(tabs[1].opener,null);
assert.equal(request.finish(ref).opened,true);assert.equal(navigations[0],'https://fabric.example/api/present/secret');assert.ok(!tabs[1].closed);
const failed=view.beginImage('draw a cat');failed.cancel();assert.ok(tabs[2].closed);
const empty=view.beginImage('generate an image');empty.finish({text:'service failed'});assert.ok(tabs[3].closed);
const before=tabs.length;view.beginImage('play classical').finish({media:{}});assert.equal(tabs.length,before);
assert.equal(view.imageRequest('do not generate an image'),false);assert.equal(view.imageRequest('generate a report'),false);
scope.open=()=>null;const blocked=view.beginImage('generate an image');assert.equal(blocked.finish(ref).opened,false);
assert.equal(view.imageArtifacts({artifacts:[{type:'image/png',url:'javascript:alert(1)'},{type:'image/png',url:'https://evil.example/api/present/x'},{type:'text/html',url:'/api/present/x'}]}).length,0);
assert.equal(view.imageArtifacts({artifacts:[...ref.artifacts,...ref.artifacts]}).length,1);
'''.replace('HELPER',json.dumps(helper))
    subprocess.run(['node','-e',script],check=True)


def test_dashboard_renders_unknown_and_untrusted_names_as_text():
    source=(ROOT/'signal-window/fabric-dashboard.js').read_text()
    script=r'''
const vm=require('vm'),assert=require('assert');
class Element{constructor(tag){this.tag=tag;this.children=[];this.textContent='';}append(...children){this.children.push(...children)}replaceChildren(...children){this.children=children}}
const ids={};for(const id of ['nodes','care','status','careStatus','refresh'])ids[id]=new Element(id);
const offline='<img src=x onerror=alert(1)>';
const ctx={URL,AbortController,Date,Promise,setTimeout,clearTimeout,setInterval:()=>{},document:{hidden:false,getElementById:id=>ids[id],createElement:tag=>new Element(tag)},fetch:async path=>({ok:true,json:async()=>path.endsWith('/care')?{nodes:[{node:offline,errors:[{check:'release',error:'unreachable'}]}]}:{nodes:{self:{identity:{name:'host'}},peers:[{name:offline,node_error:'offline'}]}}})};
vm.createContext(ctx);vm.runInContext(SOURCE,ctx);
setImmediate(()=>{const strings=[];function visit(el){strings.push(el.textContent);for(const child of el.children)visit(child)}visit(ids.nodes);visit(ids.care);assert.ok(strings.includes(offline));assert.ok(strings.includes('Unreachable at last check'));assert.ok(strings.includes('Unknown'));assert.ok(ids.careStatus.textContent.includes('could not be checked'));assert.ok(!ids.refresh.disabled)});
'''.replace('SOURCE',json.dumps(source))
    subprocess.run(['node','-e',script],check=True)


@pytest.mark.parametrize('surface',['signal-window','albert'])
def test_actual_submit_handlers_use_local_views_before_inference(surface):
    helper=(ROOT/'signal-window/browser-views.js').read_text()
    if surface=='signal-window':
        source=(ROOT/surface/'app.js').read_text()
        handler=source[source.index("form.addEventListener('submit',"):source.index("\nlet mediaNode=")]
        setup="""
let submitted;const form={addEventListener:(name,fn)=>submitted=fn};
let endpointAuthorized=true,files=[],energy=0,art={born:0},visualTurn=0,mediaNode='',selectedMediaOutput='native';const signalSession='session';
const input={value:'',placeholder:''},log={append(){}},c={clearRect(){}},N=256;
const line=()=>{},chips=()=>{},event=()=>{},status=()=>{},pollMedia=()=>{},targetNode=()=>'';
async function run(query){input.value=query;await submitted({preventDefault(){}})}
"""
    else:
        source=(ROOT/surface/'index.html').read_text()
        handler=source[source.index('async function askFabric('):source.index('\nfunction consumeFabric(')]
        setup="""
const state={attachments:[],folds:[]},FABRIC_ENDPOINT='/api/cognition',ALBERT_SESSION='session';
const addFold=()=>{},addProgress=()=>1,replaceFold=()=>{},finishProgress=()=>{},sleep=async()=>{},clearAttachments=()=>{},consumeFabric=()=>{};
async function run(query){await askFabric(query)}
"""
    script=r'''
const vm=require('vm'),assert=require('assert');const order=[];
const tab={closed:false,document:{body:{}},location:{replace:url=>order.push('navigate')},close(){this.closed=true}};
const ctx={URL,AbortController,setTimeout,clearTimeout,location:{href:'https://fabric.example/',origin:'https://fabric.example'},open:()=>{order.push('open');return tab},document:{createElement:()=>({})},fetch:async()=>{order.push('fetch');return {ok:true,json:async()=>({text:'Saved image',artifacts:[{name:'reef',type:'image/png',url:'/api/present/result'}]})}}};
vm.createContext(ctx);vm.runInContext(HELPER,ctx);vm.runInContext(SETUP+'\n'+HANDLER,ctx);
(async()=>{await ctx.run('/fabric');assert.deepEqual(order,['open']);order.length=0;await ctx.run('generate a picture of a reef');assert.equal(order[0],'open');assert.ok(order.includes('fetch'));assert.ok(order.includes('navigate'))})().catch(error=>{console.error(error);process.exit(1)});
'''.replace('HELPER',json.dumps(helper)).replace('SETUP',json.dumps(setup)).replace('HANDLER',json.dumps(handler))
    result=subprocess.run(['node','-e',script],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
