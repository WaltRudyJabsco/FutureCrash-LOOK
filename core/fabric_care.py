"""Bounded Fabric upkeep: installed releases and configured essential-state backups."""
from __future__ import annotations
import fcntl,json,os,re,subprocess,sys,time,uuid
from pathlib import Path
try:from . import recovery,recovery_setup
except ImportError:import recovery,recovery_setup

SCHEMA='fabric-care-v1'
BACKUP_MAX_AGE=24*3600


def intent(text):
    low=' '.join(str(text).casefold().split()).strip(' .!?')
    low=re.sub(r'^(?:please |can you |could you )','',low)
    context=bool(re.search(r'\b(fabric|computers|nodes|devices)\b',low) or re.search(r"\b(we|we're|we are)\b",low))
    if not context:return None
    backup=bool(re.search(r'\b(backups?|back up|backed up)\b',low))
    updates=bool(re.search(r'\b(updates?|up to date|up-to-date)\b',low))
    if low.startswith(('check ','inspect ','are we ','is our ','is my ')) or low in {'fabric status','our fabric status','my fabric status'}:
        return {'operation':'status'}
    if low.startswith(('make sure ','ensure ')) and (backup or updates or 'protected' in low):return {'operation':'ensure'}
    if low.startswith(('back up ','backup ','run backups')) and backup:return {'operation':'backup'}
    if low.startswith(('update ','synchronize ','sync ')):
        source=re.search(r'\bfrom (this computer|this node|local|[a-z0-9_.-]+)$',low)
        return {'operation':'sync','source':('local' if source and source[1] in {'this computer','this node','local'} else source[1] if source else '')}
    return None


def tools():
    return [
      {'type':'function','function':{'name':'fabric_status','description':'Check trusted Fabric nodes, installed releases, updater receipts and restore-tested essential-state backups. Read-only; does not check GitHub or claim documents/media are backed up.','parameters':{'type':'object','properties':{}}}},
      {'type':'function','function':{'name':'fabric_maintain','description':'Only after an explicit upkeep request: run already configured backups, synchronize installed runtime from a named trusted source, or ensure backups and inspect releases. No new drive setup, firmware, package upgrades, GitHub downloads or arbitrary shell. Accepted jobs remain pending until receipts verify completion.','parameters':{'type':'object','properties':{'operation':{'type':'string','enum':['backup','sync','ensure']},'source':{'type':'string','description':'Required for synchronization; local or a trusted node name explicitly named by the user.'}},'required':['operation']}}}
    ]


def backup_status(home):
    raw=recovery.status(home);state=recovery.root(home)
    job={}
    try:job=json.loads((state/'care-job.json').read_text())
    except (OSError,ValueError):pass
    if job.get('state') in {'queued','running'} and job.get('pid'):
        try:os.kill(int(job['pid']),0)
        except ProcessLookupError:job.update(state='failed',error='Backup worker stopped before publishing a result')
        except PermissionError:pass
    receipts=[raw.get('last_backup'),raw.get('last_sent'),*raw.get('received',[])]
    return {'configured':raw.get('configured',False),'role':raw.get('role'),'connected':raw.get('connected'),
            'owner':recovery.capsule_owner(home),'scope':'fabric-essential','excluded':['documents','photos','media'],
            'receipts':[r for r in receipts if isinstance(r,dict)],'job':job,
            'setup': 'lk fabric backup add' if not raw.get('configured') else 'lk fabric backup configure'}


def start_backup(home):
    state=recovery.root(home);state.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (state/'care-submit.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        status=backup_status(home)
        if status['job'].get('state') in {'queued','running'}:return {'ok':True,**status['job'],'already_running':True}
        if not status['configured']:return {'ok':False,'state':'needs_setup','next':status['setup']}
        if not status['connected']:return {'ok':False,'state':'disconnected','next':'Connect/unlock the configured backup drive'}
        job={'id':uuid.uuid4().hex,'state':'queued','created':time.time()}
        recovery.private_json(state/'care-job.json',job)
        try:
            with (state/'care-job.log').open('ab') as log:
                proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'worker',job['id']],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
            job['pid']=proc.pid;recovery.private_json(state/'care-job.json',job)
        except OSError as exc:
            job.update(state='failed',error=str(exc));recovery.private_json(state/'care-job.json',job);raise
        return {'ok':True,**job}


def worker(home,identifier):
    state=recovery.root(home);path=state/'care-job.json'
    # Submit owns the receipt until it has recorded the worker PID.
    with (state/'care-submit.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX);job=json.loads(path.read_text())
        if job['id']!=identifier:return
        job.update(state='running',started=time.time());recovery.private_json(path,job)
    try:
        result=recovery_setup.run_configured(home,due=False) if (state/'setup.json').exists() else recovery.backup(home)
        results=result.get('results',[result])
        verified=bool(results) and not result.get('errors') and all(row.get('restore_tested') for row in results)
        job.update(state='complete' if verified else 'incomplete',verified=verified,result=result,finished=time.time())
    except Exception as exc:job.update(state='failed',error=str(exc),finished=time.time())
    recovery.private_json(path,job)


def inspect(snapshot,get):
    local=str((snapshot.get('self') or {}).get('name') or ((snapshot.get('self') or {}).get('identity') or {}).get('name') or 'local')
    names=[local]
    for peer in snapshot.get('peers') or []:
        if not peer.get('trusted'):continue
        name=str(((peer.get('node') or {}).get('identity') or {}).get('name') or peer.get('name') or '')
        if name and name not in names:names.append(name)
    rows=[];receipts=[]
    for name in names:
        row={'node':name}
        for key,path in [('release','/v1/maintenance/release'),('update','/v1/maintenance/status'),('backup','/v1/recovery/status')]:
            try:
                value=get('local' if name==local else name,path)
                if not isinstance(value,dict):raise ValueError('Invalid status response')
                row[key]=value
            except Exception as exc:
                row.setdefault('errors',[]).append({'check':key,'error':str(exc)})
                # An unreachable node cannot answer the other checks either.
                if key=='release':break
        values=(row.get('backup') or {}).get('receipts') or []
        if isinstance(values,list):receipts.extend(r for r in values if isinstance(r,dict))
        rows.append(row)
    now=time.time()
    for row in rows:
        backup=row.get('backup') or {};owner=backup.get('owner')
        matching=[]
        for receipt in receipts:
            try:age=now-float(receipt.get('verified_at') or 0)
            except (TypeError,ValueError):continue
            if owner and receipt.get('node')==owner and receipt.get('restore_tested') and 0<=age<=BACKUP_MAX_AGE:matching.append(receipt)
        backup['verified_recently']=bool(matching)
        backup['verified_at']=max((r.get('verified_at',0) for r in matching),default=None)
    digests={row.get('release',{}).get('digest') if isinstance(row.get('release',{}).get('digest'),str) else None for row in rows}
    return {'schema':SCHEMA,'local':local,'nodes':rows,'releases_match':bool(rows) and None not in digests and len(digests)==1,
            'scope':'Installed Fabric runtime and essential-state backups; excludes documents, photos and media. No GitHub latest-release check.',
            'actions':[]}


def operate(operation,source,snapshot,get,post):
    if not isinstance(source,str) or (source and not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',source)):raise ValueError('Use a trusted node name for the update source')
    if not isinstance(operation,str) or operation not in {'status','backup','sync','ensure'}:raise ValueError('Unknown Fabric care operation')
    report=inspect(snapshot,get)
    if operation=='status':return report
    if operation in {'backup','ensure'}:
        needs_backup=operation=='backup' or any(not (row.get('backup') or {}).get('verified_recently') for row in report['nodes'])
        for row in report['nodes']:
            backup=row.get('backup') or {}
            if backup.get('configured') and needs_backup:
                try:result=post(row['node'],'/v1/recovery/run',{})
                except Exception as exc:result={'ok':False,'state':'failed','error':str(exc)}
                report['actions'].append({'node':row['node'],'action':'backup',**result})
    if operation in {'sync','ensure'} and (operation=='sync' or not report['releases_match']):
        if not source:
            report['next']='Name the verified source: “update all computers from this computer” or “update all computers from NODE”. Synchronization does not fetch GitHub.'
            return report
        if source=='local':source=report['local']
        origin=next((r for r in report['nodes'] if r['node'].casefold()==source.casefold()),None)
        if origin:source=origin['node']
        release=(origin or {}).get('release') or {}
        if not release.get('digest'):raise ValueError('Update source must be a reachable trusted node with a registered release')
        for row in report['nodes']:
            if row['node']==source or row.get('release',{}).get('digest')==release['digest']:continue
            try:result=post(row['node'],'/v1/maintenance/update',{'source':source,'digest':release['digest'],'confirm':True})
            except Exception as exc:result={'ok':False,'state':'failed','error':str(exc)}
            report['actions'].append({'node':row['node'],'action':'update',**result})
    return report


def describe(report):
    lines=['Fabric check · installed releases '+('match' if report.get('releases_match') else 'differ or cannot all be checked')]
    for row in report.get('nodes') or []:
        release=row.get('release') or {};backup=row.get('backup') or {};update=row.get('update') or {}
        state=('restore-tested within 24 hours' if backup.get('verified_recently') else 'no recent restore-tested backup found') if row.get('backup') else 'backup status unavailable'
        release_label=str(release['commit'])[:7] if release.get('commit') else 'unavailable'
        if backup.get('configured') and not backup.get('connected'):state+=' · drive disconnected'
        if backup.get('job'):state+=' · backup job '+str(backup['job'].get('state'))
        lines.append(f"{row['node']}: release {release_label} · {state}"+(f" · updater {update['state']}" if update.get('state') else ''))
        for error in row.get('errors') or []:
            detail='node unreachable / request timed out' if 'timed out' in error['error'].casefold() else error['error'][:160]
            lines.append('  '+error['check']+': '+detail)
    for action in report.get('actions') or []:lines.append(f"{action['node']}: {action['action']} {action.get('state','accepted')}"+(' · '+action['error'] if action.get('error') else ''))
    if any(a.get('state') in {'queued','staged','running','restarting'} for a in report.get('actions') or []):lines.append('Work is pending; ask “check our Fabric” again to verify completion.')
    if report.get('next'):lines.append(report['next'])
    lines.append('Backup scope: Fabric identity, Notes and settings—not documents, photos or media.')
    if any(r.get('backup') and not r['backup'].get('configured') and not r['backup'].get('verified_recently') for r in report.get('nodes') or []):lines.append('Unprotected nodes need inclusion in a configured backup plan; use lk fabric backup add/configure.')
    return '\n'.join(lines)


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='worker':worker(Path.home(),sys.argv[2])
    else:raise SystemExit('Use fcl-node care or Albert/Lo/Signal')
