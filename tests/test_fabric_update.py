import io,json,time,zipfile
from pathlib import Path
from unittest.mock import Mock
import pytest
from core import fabric_update as update

@pytest.fixture
def state(tmp_path,monkeypatch):
    monkeypatch.setattr(update,'root',lambda:tmp_path)
    return tmp_path

def test_plan_is_read_only_selects_latest_installed_owner(state,monkeypatch):
    node=Mock();node.http_json.return_value={}
    get=Mock();post=Mock();monkeypatch.setattr(update,'clients',lambda:(node,get,post))
    monkeypatch.setattr(update.fabric_care,'inspect',lambda *a:{'nodes':[{'node':'home','release':{'digest':'a','commit':'old'}},{'node':'away','release':{'digest':'b','commit':'new'}}],'local':'home','releases_match':False})
    monkeypatch.setattr(update,'github_latest',lambda:{'state':'checked','commit':'new'})
    plan=update.plan();assert plan['source']['node']=='away' and plan['review']
    post.assert_not_called()
    monkeypatch.setattr(update,'github_latest',Mock(side_effect=OSError('offline')))
    assert update.plan()['source']['kind']=='unresolved'
    assert update.plan('home')['source']['digest']=='a'
    with pytest.raises(ValueError):update.plan('unknown')

def test_start_requires_recent_local_review_and_deduplicates(state,monkeypatch):
    with pytest.raises(ValueError):update.start(review='../bad')
    token='a'*32;(state/('review-'+token+'.json')).write_text(json.dumps({'checked':0}))
    with pytest.raises(ValueError,match='expired'):update.start(review=token)
    (state/('review-'+token+'.json')).write_text(json.dumps({'checked':time.time()}))
    monkeypatch.setattr(update,'status',lambda *a:{'state':'running','id':'same'})
    spawn=Mock();monkeypatch.setattr(update.subprocess,'Popen',spawn)
    assert update.start(review=token)['id']=='same';spawn.assert_not_called()

def test_worker_records_failure_and_skips_without_false_success(state,monkeypatch):
    (state/'local.json').write_text(json.dumps({'id':'job','steps':[]}))
    def work(step):
        step('okay',lambda:{'ok':True})
        step('conflict',lambda:{'peers':[{'conflicts':['revision']}]})
        step('disabled',lambda:{'state':'disabled'})
        step('pending',lambda:{'state':'queued'})
    monkeypatch.setattr(update,'local_work',work)
    update.worker('local','job');result=json.loads((state/'local.json').read_text())
    assert result['state']=='partial'
    assert [s['state'] for s in result['steps']]==['verified','failed','skipped','pending']
    assert (state/'job.json').exists()

def test_wait_rejects_failed_receipts_and_waits_for_expected_identity(monkeypatch):
    monkeypatch.setattr(update.time,'sleep',lambda _:None)
    with pytest.raises(ValueError):update.wait_for(lambda:{'state':'rolled_back'},lambda r:r.get('state')=='healthy')
    values=iter([{'state':'healthy','digest':'old'},{'state':'healthy','digest':'new'}])
    assert update.wait_for(lambda:next(values),lambda r:r.get('digest')=='new')['digest']=='new'

def test_prepare_pins_commit_preserves_modes_and_validates_bundle(state,tmp_path,monkeypatch):
    paths={'.local/share/look/lk':('look/lk',b'print("hi")',0o755),'.local/share/future-crash-look/core/node.py':('core/node.py',b'# node',0o755),'.local/share/future-crash-look/core/maintenance.py':('core/maintenance.py',b'# updater',0o644),'.local/share/future-crash-look/RELEASE':('VERSION',b'1.0',0o644)}
    registry=tmp_path/'registry';registry.write_text(json.dumps({'files':[{'path':p,'mode':v[2]} for p,v in paths.items()]}));monkeypatch.setattr(update.maintenance,'registry',lambda:registry)
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,'w') as z:
        for src,data,mode in paths.values():z.writestr('repo-sha/'+src,data)
        z.writestr('repo-sha/core/new.py',b'# new module')
    urls=[]
    def fetch(req,**kwargs):urls.append(req.full_url);return io.BytesIO(archive.getvalue())
    monkeypatch.setattr(update.urllib.request,'urlopen',fetch)
    result=update.prepare('a'*40);manifest,payload=update.maintenance.validate_bundle(update.prepared(result['digest']),result['digest'])
    assert urls[0].endswith('/'+'a'*40)
    assert next(f for f in manifest['files'] if f['path'].endswith('/lk'))['mode']==0o755
    assert '.local/share/future-crash-look/core/new.py' in payload
    with pytest.raises(ValueError):update.prepared('../x')

def test_browser_gateway_rejects_cross_origin_before_network(monkeypatch):
    h=Mock();h.path='/api/fabric/update';h.headers={'Content-Type':'application/json','Origin':'https://evil.test','Host':'local.test','Content-Length':'2'}
    fetch=Mock();monkeypatch.setattr(update.urllib.request,'urlopen',fetch)
    with pytest.raises(ValueError,match='Same-origin'):update.web(h,'http://localhost',True)
    fetch.assert_not_called()

def test_local_control_boundary():
    from core import node
    handler=Mock();handler.server.plane='ingress';handler.headers={}
    node.API._fabric_update(handler,{'confirm':True,'review':'a'*32})
    assert handler.sendj.call_args.args[0]==403


def test_coordinator_updates_before_upkeep_and_checks_receipts(monkeypatch):
    calls=[]
    def get(target,path):
        if path.endswith('/status'):return {'state':'healthy','digest':'new'}
        if path.endswith('/services'):return {'services':{}}
        if path.endswith('/upkeep'):return {'id':'job','state':'complete'}
        raise AssertionError(path)
    def post(target,path,data):calls.append((target,path,data));return {'id':'job'}
    monkeypatch.setattr(update,'clients',lambda:(Mock(),get,post))
    job={'plan':{'local':'home','source':{'kind':'node','node':'away','digest':'new'},'nodes':[{'node':'home','release':{'digest':'old'}},{'node':'away','release':{'digest':'new'}}]}}
    steps=[]
    def step(label,fn):
        result=fn();steps.append(label);return {'state':'verified','result':result}
    update.fabric_work(job,step)
    assert calls[0][1]=='/v1/maintenance/update' and calls[0][0]=='local'
    assert [x[0] for x in calls if x[1]=='/v1/upkeep']==['local','away']
    assert steps[-1]=='away service health'


def test_remote_local_upkeep_still_requires_browser_authorization():
    from test_browser_fabric_views import load
    for surface in ('signal-window','albert'):
        server=load(surface);handler=server.Handler.__new__(server.Handler)
        handler.path='/api/fabric/update';handler._require_endpoint=Mock(return_value=False)
        handler.do_POST();handler._require_endpoint.assert_called_once_with('lo.use')


def test_partial_receipt_remains_structured_for_reporting():
    receipt={'state':'partial','steps':[{'label':'Backup','state':'needs_setup'}]}
    with pytest.raises(update.ReceiptError) as error:update.wait_for(lambda:receipt,lambda r:r.get('state')=='complete')
    assert error.value.receipt==receipt and str(error.value)=='Backup: needs_setup'


def test_busy_sync_is_followed_until_finished(monkeypatch):
    monkeypatch.setattr(update.time,'sleep',lambda _:None)
    values=iter([{'ok':True,'state':'sync already running'},{'ok':True,'peers':[]}])
    result=update.wait_for(lambda:next(values),lambda r:r.get('state')!='sync already running',120)
    assert result=={'ok':True,'peers':[]}
