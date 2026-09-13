#!/usr/bin/env python3
import argparse, importlib.machinery, importlib.util, json, os, signal, socket, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
LK_PATH=ROOT/'lk'
HOME=Path.home()
STATE=HOME/'.local/share/look'
SOCKET=STATE/'ai.sock'
PID=STATE/'ai.pid'
FOREGROUND=STATE/'ai_foreground.json'
STARTED=time.time()
RUN=True
CURRENT='idle'
WAKE=True
BACKOFF_UNTIL=0.0


os.environ["LOOK_AI_BROKER_PROCESS"]="1"


def load_core():
    loader=importlib.machinery.SourceFileLoader('look_living_ai_core',str(LK_PATH))
    spec=importlib.util.spec_from_loader(loader.name,loader)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[loader.name]=mod
    loader.exec_module(mod)
    return mod

core=load_core()


def foreground_busy():
    try:
        data=json.loads(FOREGROUND.read_text())
        age=time.time()-float(data.get('time',0))
        pid=int(data.get('pid',0))
        if age>180:
            try: FOREGROUND.unlink()
            except OSError: pass
            return False
        try:
            os.kill(pid,0)
        except OSError:
            try: FOREGROUND.unlink()
            except OSError: pass
            return False
        return True
    except Exception:
        return False


def counts():
    def n(path,pattern='*.json'):
        try: return len(list(path.glob(pattern)))
        except OSError: return 0
    jobs=0
    try:
        for p in core.LO_JOBS_DIR.glob('*.json'):
            try:
                if json.loads(p.read_text()).get('status')=='queued': jobs+=1
            except Exception: pass
    except OSError: pass
    return jobs,n(core.MEMORY_QUEUE),n(core.SKILL_FEEDBACK_QUEUE)


def status():
    jobs,memory,skills=counts()
    return {
        'ok':True,'state':'running','pid':os.getpid(),'foreground':foreground_busy(),
        'jobs':jobs,'memory':memory,'skills':skills,'current':CURRENT,
        'uptime':time.time()-STARTED,
    }


def process_lo_job():
    global CURRENT
    try: paths=sorted(core.LO_JOBS_DIR.glob('*.json'))
    except OSError: return False
    for path in paths:
        try: job=json.loads(path.read_text())
        except Exception: continue
        if job.get('status')!='queued': continue
        CURRENT=f"background job {job.get('id','?')}"
        core._run_lo_job(path)
        CURRENT='idle'
        return True
    return False


def process_memory():
    global CURRENT,BACKOFF_UNTIL
    jobs=core._memory_job_files()
    if not jobs: return False
    path=jobs[0]
    CURRENT='memory'
    try:
        job=json.loads(path.read_text(encoding='utf-8'))
        base=job.get('base','http://127.0.0.1:11434')
        # Queue durability rule: never consume an exchange unless the inference
        # endpoint is actually reachable. Extraction helpers intentionally fail
        # soft, so reachability must be established at this outer boundary.
        core._ollama_tags(base)
        memory=core._load_memory()
        core._remember_exchange(
            base,
            job.get('model',os.environ.get('LOOK_OLLAMA_MODEL','qwen3:8b')),
            memory,str(job.get('user','')),str(job.get('assistant','')),
            str(job.get('profile','workspace')),
        )
        path.unlink()
        return True
    except Exception as exc:
        try:
            memory=core._load_memory(); memory['last_worker_error']=str(exc)[:500]; core._save_memory(memory)
        except Exception: pass
        BACKOFF_UNTIL=time.time()+30.0
        return False
    finally:
        CURRENT='idle'


def process_skill():
    global CURRENT,BACKOFF_UNTIL
    jobs=core._skill_feedback_job_files()
    if not jobs: return False
    path=jobs[0]
    CURRENT='skill reflection'
    try:
        job=json.loads(path.read_text(encoding='utf-8'))
        action,skill=core._reflect_on_feedback(
            job.get('base','http://127.0.0.1:11434'),
            job.get('model',os.environ.get('LOOK_OLLAMA_MODEL','qwen3:8b')),job,
        )
        changed=False
        if action=='new' and skill:
            changed=core._append_learned_skill(skill,'positive' if job.get('polarity')=='positive' else 'new')
        elif action=='correct' and skill:
            changed=core._append_learned_skill(skill,'corrective')
        elif action=='reinforce' and skill:
            changed=core._update_skill_meta(skill,'positive')
        elif action=='weaken' and skill:
            changed=core._update_skill_meta(skill,'negative')
        if changed and skill:
            verb={'new':'learned','correct':'corrected','reinforce':'reinforced','weaken':'weakened'}.get(action,'updated')
            core._emit_event('learned',f'{verb}: {skill}')
        path.unlink()
        return True
    except Exception:
        BACKOFF_UNTIL=time.time()+30.0
        return False
    finally:
        CURRENT='idle'


def next_background_work():
    # Explicit user background jobs outrank housekeeping.
    if process_lo_job(): return True
    if process_memory(): return True
    if process_skill(): return True
    return False


def handle(conn):
    global RUN,WAKE,BACKOFF_UNTIL
    try:
        data=b''
        while not data.endswith(b'\n') and len(data)<65536:
            chunk=conn.recv(4096)
            if not chunk: break
            data+=chunk
        msg=json.loads(data.decode() or '{}')
        cmd=msg.get('command','status')
        if cmd=='status': reply=status()
        elif cmd=='wake': WAKE=True; BACKOFF_UNTIL=0.0; reply={'ok':True}
        elif cmd=='foreground': WAKE=True; reply={'ok':True}
        elif cmd=='stop': RUN=False; reply={'ok':True}
        else: reply={'ok':False,'error':'unknown command'}
        conn.sendall((json.dumps(reply)+'\n').encode())
    except Exception as exc:
        try: conn.sendall((json.dumps({'ok':False,'error':str(exc)})+'\n').encode())
        except Exception: pass


def cleanup(*_):
    global RUN
    RUN=False


def serve():
    global WAKE
    STATE.mkdir(parents=True,exist_ok=True)

    # Atomic singleton claim. Never unlink a live broker's socket during a
    # simultaneous shell startup race.
    while True:
        try:
            fd=os.open(PID,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            os.write(fd,str(os.getpid()).encode()); os.close(fd)
            break
        except FileExistsError:
            try:
                old=int(PID.read_text().strip()); os.kill(old,0)
                return 0
            except Exception:
                try: PID.unlink()
                except OSError: return 0
                try: SOCKET.unlink()
                except OSError: pass

    try: SOCKET.unlink()
    except OSError: pass
    signal.signal(signal.SIGTERM,cleanup)
    signal.signal(signal.SIGINT,cleanup)
    server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    server.bind(str(SOCKET)); os.chmod(SOCKET,0o600); server.listen(8); server.settimeout(.35)
    try:
        while RUN:
            try:
                conn,_=server.accept()
                with conn: handle(conn)
            except socket.timeout: pass
            if not RUN: break
            if foreground_busy(): continue
            if time.time()<BACKOFF_UNTIL: continue
            # Drain one unit at a time so foreground can win between calls.
            if WAKE or any(counts()):
                next_background_work()
                WAKE=False
    finally:
        server.close()
        try: SOCKET.unlink()
        except OSError: pass
        try: PID.unlink()
        except OSError: pass
    return 0


def main():
    ap=argparse.ArgumentParser(add_help=True)
    ap.add_argument('--daemon',action='store_true')
    ap.parse_args()
    return serve()

if __name__=='__main__': raise SystemExit(main())
