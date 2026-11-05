import io
import json
import subprocess
from unittest.mock import Mock

import pytest
from test_albert_trust_750 import ROOT, load_server


def test_dismiss_survives_reload_and_preserves_other_turns_saved_and_sessions(tmp_path,monkeypatch):
    server=load_server(tmp_path,monkeypatch)
    first=server._session_append('main','old question','old answer')
    newer=server._session_append('main','new question','new answer')
    server._session_append('other','other question','other answer')
    server.saved_upsert({'id':'saved','title':'Kept separately','text':'old answer'})
    saved=server.SAVED_FILE.read_bytes()
    assert server._session_dismiss('main',first)['removed']==2
    server._SESSIONS.clear();server._SESSIONS.update(server._load_threads())
    assert [row['content'] for row in server._session_history('main')]==['new question','new answer']
    assert server._session_rows('main')[0]['id']==newer[0]
    assert server._session_history('other')[0]['content']=='other question'
    assert server.SAVED_FILE.read_bytes()==saved
    assert server._session_dismiss('main',first)['removed']==0


def test_legacy_threads_get_stable_dismissal_ids(tmp_path,monkeypatch):
    server=load_server(tmp_path,monkeypatch)
    server.THREAD_FILE.write_text(json.dumps({'main':{'stamp':server.time.time(),'rows':[{'role':'user','content':'legacy'},{'role':'assistant','content':'answer'}]}}))
    a=server._load_threads();b=server._load_threads()
    assert a==b
    server._SESSIONS.update(a)
    ids=[row['id'] for row in server._session_rows('main')]
    server._session_dismiss('main',ids)
    assert server._load_threads()['main'][1]==[]


@pytest.mark.parametrize('ids',[[],['bad'],['a'*32]*41,'a'*32])
def test_invalid_dismissal_preserves_thread(tmp_path,monkeypatch,ids):
    server=load_server(tmp_path,monkeypatch);server._session_append('main','hi','hello')
    before=server.THREAD_FILE.read_bytes()
    with pytest.raises(ValueError):server._session_dismiss('main',ids)
    assert server.THREAD_FILE.read_bytes()==before


def test_dismiss_route_requires_authorization_and_same_origin(tmp_path,monkeypatch):
    server=load_server(tmp_path,monkeypatch)
    handler=server.Handler.__new__(server.Handler);handler.path='/api/thread/dismiss'
    handler._require_endpoint=Mock(return_value=False);handler.send_json=Mock()
    handler.rfile=Mock();handler.do_POST();handler.rfile.read.assert_not_called()
    handler._require_endpoint.return_value=True
    handler.headers={'Content-Type':'application/json','Origin':'https://evil.example','Host':'fabric.example','Content-Length':'2'}
    handler.rfile=io.BytesIO(b'{}');handler.do_POST()
    assert handler.send_json.call_args.args[0]==400


def test_browser_dismiss_then_restore_never_resurrects_and_failure_keeps_card():
    source=(ROOT/'albert/index.html').read_text()
    dismiss=source[source.index('async function dismissFold('):source.index('async function pinFold(')]
    restore=source[source.index('async function restoreThread('):source.index('\nrestoreThread();')]
    normalize=source[source.index('function normalizeResult('):source.index('\n',source.index('function normalizeResult('))]
    script=r'''
const assert=require('assert');let serverRows=[{id:'a'.repeat(32),role:'user',content:'hi'},{id:'a'.repeat(32),role:'assistant',content:'hello'}];
const ALBERT_SESSION='main',state={folds:[]},document={getElementById:()=>null};let notice='',fail=false,sent;
const teardownMedia=()=>{},render=()=>{},setTimeout=fn=>fn(),statusLine=text=>notice=text;
function addFold(f){state.folds.push({...f,id:'fold'+state.folds.length})}
async function fetch(url,options){if(url==='/api/thread/dismiss'){sent=JSON.parse(options.body);if(fail)return {ok:false};serverRows=serverRows.filter(row=>!sent.ids.includes(row.id));return {ok:true,json:async()=>({ok:true})}}return {ok:true,json:async()=>({session:'main',turns:serverRows})}}
''' + normalize+'\n'+dismiss+'\n'+restore+r'''
(async()=>{
await restoreThread();assert.equal(state.folds.length,1);assert.deepEqual(state.folds[0].thread_ids,['a'.repeat(32)]);
fail=true;await dismissFold('fold0');assert.ok(!state.folds[0].dismissed);assert.ok(notice.includes('Could not dismiss permanently'));
fail=false;await dismissFold('fold0');assert.ok(state.folds[0].dismissed);assert.equal(sent.session,'main');
state.folds=[];await restoreThread();assert.equal(state.folds.length,0);
const normalized=normalizeResult({type:'answer',text:'new',thread_ids:['b'.repeat(32)],thread_session:'other'});assert.equal(normalized.thread_session,'other');assert.deepEqual(normalized.thread_ids,['b'.repeat(32)]);
})().catch(e=>{console.error(e);process.exit(1)});
'''
    subprocess.run(['node','-e',script],check=True)
