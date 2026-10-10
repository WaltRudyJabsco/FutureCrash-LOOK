import io
import json
from pathlib import Path
import subprocess
import pytest
from unittest.mock import Mock

from core import node
from look.notebook_core import Notebook

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def installed_notebook_layout(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT/'look'))


def request(store, monkeypatch, payload):
    monkeypatch.setattr(node,'_notebook_store',lambda:store)
    api=node.API.__new__(node.API)
    api.path='/v1/notebook/answer'
    api._authorized_ingress=lambda path:True
    api.body=lambda:payload
    api.sendj=Mock()
    api.do_POST()
    return api.sendj.call_args.args


def test_api_requires_current_revision_before_ack(tmp_path,monkeypatch):
    store=Notebook(tmp_path); row=store.create('Due',remind_at=1000)
    status,result=request(store,monkeypatch,{'id':row['note'],'choice':'done'})
    assert status==400
    status,result=request(store,monkeypatch,{'id':row['note'],'revision':row['id'],'choice':'snooze'})
    assert status==200 and result['ok']
    status,result=request(store,monkeypatch,{'id':row['note'],'revision':row['id'],'choice':'done'})
    assert status==400
    assert store.list()[0]['status']=='open'


def test_tick_emits_one_event_per_local_occurrence(tmp_path,monkeypatch):
    store=Notebook(tmp_path,'Mac'); store.create('Due',remind_at=1000)
    monkeypatch.setattr(node,'_notebook_store',lambda:store)
    monkeypatch.setattr(node,'identity',lambda:{'name':'Mac'})
    from core import notifications
    monkeypatch.setattr(notifications,'deliver',Mock(return_value={'ok':True,'delivery':[]}))
    beacon=Mock(); events=Mock()
    monkeypatch.setattr(node,'_beacon_record',beacon)
    monkeypatch.setattr(node.FABRIC_STORE,'event',events)
    node._notebook_tick(); node._notebook_tick()
    assert beacon.call_count==1
    assert [call.args[1] for call in events.call_args_list].count('reminder')==1
    assert events.call_args_list[0].args[1:3]==('reminder','due')


def test_sync_uses_only_paired_nodes_and_exchanges_edits(tmp_path,monkeypatch):
    local=Notebook(tmp_path/'local'); remote=Notebook(tmp_path/'remote')
    local.create('Local'); remote.create('Remote')
    monkeypatch.setattr(node,'_notebook_store',lambda:local)
    monkeypatch.setattr(node,'node_info',lambda:{'name':'Mac'})
    monkeypatch.setattr(node.PEERS,'public',lambda:[{'name':'3090','trusted':True,'node':{'ready':True}},
                                                 {'name':'Stranger','trusted':False,'node':{'ready':True}}])
    monkeypatch.setattr(node,'_peer_json',lambda *args,**kwargs:{'ids':[r['id'] for r in remote.snapshot()]})
    monkeypatch.setattr(node,'_remote_url',lambda snapshot,name,path:'https://paired'+path)
    def post(url,data,**kwargs): return remote.exchange(data['revisions'],data['have'])
    monkeypatch.setattr(node,'http_json',post)
    result=node._notebook_sync()
    assert result['ok'] and len(result['peers'])==1
    assert {r['title'] for r in local.list()}=={'Local','Remote'}
    assert {r['title'] for r in remote.list()}=={'Local','Remote'}


@pytest.mark.parametrize('surface',['signal','albert'])
def test_browser_reminder_text_and_ack_controls(tmp_path,surface):
    source=(ROOT/('signal-window/app.js' if surface=='signal' else 'albert/index.html')).read_text()
    end=source.index('async function pollFabricLight') if surface=='signal' else source.index("let lastBeacon=''")
    ui=source[source.index("let notebookReminderKey=''"):end]
    script=r'''
const assert=require('node:assert/strict');
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.style={};this.hidden=false}
 setAttribute(){}
 appendChild(child){child.parent=this;this.children.push(child);return child}
 append(...children){children.forEach(child=>this.appendChild(child))}
 replaceChildren(){this.children=[]}
 remove(){this.parent.children=this.parent.children.filter(child=>child!==this)}
}
const document={body:new Element('body'),createElement:tag=>new Element(tag)};
let submitted;
const window={};let notices=[];
function Notification(title,options){notices.push({title,options})}
Notification.permission='granted';window.Notification=Notification;
const fetch=async(url,options)=>{submitted={url,payload:JSON.parse(options.body)};return {ok:true,json:async()=>({ok:true})}};
'''+ui+r'''
(async()=>{
 const row={id:'note',revision:'revision',event_id:'occurrence',title:'<script>saved text</script>',body:'Long note',remind_at:1};
 renderNotebookReminders([row]);
 assert.equal(notebookReminderPanel.hidden,false);
 const card=notebookReminderPanel.children.find(child=>child.tag==='article');
 assert.ok(card.children[0].textContent.includes('<script>saved text</script>'));
 assert.equal(card.children[1].children[1].textContent,'Long note');
 renderNotebookReminders([row]);assert.equal(notebookReminderPanel.children.find(child=>child.tag==='article'),card);
 await card.children[2].onclick();
 assert.deepEqual(submitted,{url:'/api/notebook/answer',payload:{id:'note',revision:'revision',choice:'done'}});
 assert.equal(notebookReminderPanel.hidden,true);
 renderNotebookReminders([]);assert.equal(notebookReminderPanel.children.length,0);
 enableReminderAlerts();renderNotebookReminders([row]);
 renderNotebookReminders([{...row,revision:'new-revision'}]);
 assert.equal(notices.length,1);assert.equal(notices[0].options.tag,'occurrence');
})().catch(error=>{console.error(error);process.exit(1)});
'''
    subprocess.run(['node','-e',script],check=True)
