import json,subprocess
from pathlib import Path
from core.radio import Radio
from test_ytr import Downloads

ROOT=Path(__file__).resolve().parents[1]

def test_add_receipt_deduplicates_without_playback(tmp_path):
    downloads=Downloads();radio=Radio(downloads,tmp_path)
    first=radio.change({'action':'add','url':'https://youtu.be/abcdefghijk'})
    second=radio.change({'action':'add','url':'https://youtube.com/watch?v=abcdefghijk&t=10'})
    assert first['radio_added']=={'id':first['items'][0]['id'],'already_present':False}
    assert second['radio_added']==dict(first['radio_added'],already_present=True)
    assert len(downloads.jobs)==1
    assert second['items'][0]['position']==0 and second['items'][0]['bookmark_revision']==0


def test_direct_chat_parser_and_owner_receipt():
    helper=(ROOT/'signal-window/browser-views.js').read_text()
    script=r'''
const vm=require('vm'),assert=require('assert');let requests=[],saved='studio',fail=false;
const context={URL,URLSearchParams,location:{href:'https://example.test/'},localStorage:{getItem:()=>JSON.stringify(saved)},fetch:async(url,opts)=>{
 requests.push([url,opts]);if(url==='/api/ytr/config')return {ok:true,json:async()=>({owner:'default-owner'})};
 return {ok:!fail,json:async()=>fail?{error:'Owner offline'}:{ok:true,node:'studio',items:[{id:'abc',title:'A talk'}],radio_added:{id:'abc',already_present:false}}};
},open:()=>{throw Error('Must not open player')}};
vm.createContext(context);vm.runInContext(HELPER,context);const view=context.FabricBrowserViews;
(async()=>{
 for(const text of ['https://youtu.be/abcdefghijk add this to YouTube Radio','Please add https://youtu.be/abcdefghijk to our YouTube Radio queue','Can you add this to YouTube Radio?\nhttps://youtu.be/abcdefghijk','save this to ytr https://youtu.be/abcdefghijk']){
  const command=view.radioAddCommand(text);assert.equal(command?.url,'https://youtu.be/abcdefghijk',text);
 }
 for(const text of ['do not add this to YouTube Radio https://youtu.be/abcdefghijk','how do I add this to YouTube Radio?','https://youtu.be/abcdefghijk','play https://youtu.be/abcdefghijk','summarize this https://youtu.be/abcdefghijk'])assert.equal(view.radioAddCommand(text),null,text);
 assert.ok(view.radioAddCommand('add this to YouTube Radio').error);
 assert.ok(view.radioAddCommand('add this to YouTube Radio https://youtu.be/abcdefghijk https://youtu.be/12345678901').error);
 const result=await view.addRadio({url:'https://youtu.be/abcdefghijk'});assert.ok(result.includes('A talk'));assert.ok(result.includes('Playback has not started'));
 assert.equal(requests.length,1);assert.equal(requests[0][0],'/api/ytr?target=studio');assert.deepEqual(JSON.parse(requests[0][1].body),{action:'add',url:'https://youtu.be/abcdefghijk'});
 requests=[];saved=null;await view.addRadio({url:'https://youtu.be/abcdefghijk'});assert.equal(requests[1][0],'/api/ytr?target=default-owner');
 fail=true;await assert.rejects(()=>view.addRadio({url:'https://youtu.be/abcdefghijk'}),/Owner offline/);
})().catch(error=>{console.error(error);process.exit(1)});
'''.replace('HELPER',json.dumps(helper))
    result=subprocess.run(['node','-e',script],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
