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
LEASES=STATE/'ai_leases'
STARTED=time.time()
RUN=True
CURRENT='idle'
WAKE=True
BACKOFF_UNTIL=0.0

ERROR_LOG=STATE/'ai_errors.log'


def _log_error(where,exc):
    try:
        STATE.mkdir(parents=True,exist_ok=True)
        with ERROR_LOG.open('a',encoding='utf-8') as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {where}: {type(exc).__name__}: {exc}\n")
    except Exception:
        pass


def _socket_broker_alive():
    """The socket protocol, not PID reuse, is the authority for singleton state."""
    if not SOCKET.exists():
        return False
    sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    sock.settimeout(.25)
    try:
        sock.connect(str(SOCKET))
        sock.sendall(b'{"command":"status"}\n')
        data=b''
        while not data.endswith(b'\n') and len(data)<65536:
            chunk=sock.recv(4096)
            if not chunk:
                break
            data+=chunk
        reply=json.loads(data.decode() or '{}')
        return bool(reply.get('ok'))
    except Exception:
        return False
    finally:
        try: sock.close()
        except Exception: pass



os.environ["LOOK_AI_BROKER_PROCESS"]="1"


def load_core():
    loader=importlib.machinery.SourceFileLoader('look_living_ai_core',str(LK_PATH))
    spec=importlib.util.spec_from_loader(loader.name,loader)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[loader.name]=mod
    loader.exec_module(mod)
    return mod

core=load_core()


def _pid_alive(pid):
    try:
        os.kill(int(pid),0)
        return True
    except Exception:
        return False


def _client_leases():
    """Return live external inference leases; remove stale/crashed clients."""
    live=[]
    try:
        LEASES.mkdir(parents=True,exist_ok=True)
        for path in LEASES.glob('*.json'):
            try:
                data=json.loads(path.read_text())
                age=time.time()-float(data.get('time',0))
                pid=int(data.get('pid',0))
                if age>900 or not _pid_alive(pid):
                    path.unlink(missing_ok=True)
                    continue
                live.append(data)
            except Exception:
                try: path.unlink()
                except OSError: pass
    except OSError:
        pass
    return live


def foreground_busy():
    # Legacy LOOK foreground lease remains supported unchanged.
    try:
        data=json.loads(FOREGROUND.read_text())
        age=time.time()-float(data.get('time',0))
        pid=int(data.get('pid',0))
        if age>180 or not _pid_alive(pid):
            try: FOREGROUND.unlink()
            except OSError: pass
        else:
            return True
    except Exception:
        pass
    return bool(_client_leases())


def _set_client_lease(msg):
    """Per-process lease so independent AI surfaces can coordinate without identity sharing."""
    try:
        LEASES.mkdir(parents=True,exist_ok=True)
        pid=int(msg.get('pid',0))
        if pid<=0:
            return False
        path=LEASES/f'{pid}.json'
        if bool(msg.get('active')):
            data={
                'pid':pid,
                'label':str(msg.get('label') or 'client')[:80],
                'priority':str(msg.get('priority') or 'interactive')[:32],
                'time':time.time(),
            }
            tmp=path.with_suffix('.tmp')
            tmp.write_text(json.dumps(data))
            os.chmod(tmp,0o600)
            tmp.replace(path)
        else:
            try: path.unlink()
            except OSError: pass
        return True
    except Exception:
        return False


def _permit(priority='ambient'):
    """Interactive work may start immediately; background only enters a truly idle lane."""
    priority=str(priority or 'ambient').lower()
    if priority=='interactive':
        return True
    if foreground_busy():
        return False
    if CURRENT!='idle':
        return False
    if time.time()<BACKOFF_UNTIL:
        return False
    return not any(counts())


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
    leases=_client_leases()
    schedules=len([j for j in core._load_schedule() if j.get('enabled',True)])
    return {
        'ok':True,'state':'running','pid':os.getpid(),'foreground':foreground_busy(),
        'jobs':jobs,'memory':memory,'skills':skills,'schedules':schedules,'current':CURRENT,
        'clients':len(leases),
        'client_labels':[str(x.get('label','client')) for x in leases[:6]],
        'core_version':str(getattr(core,'VERSION','unknown')),
        'protocol_version':2,
        'uptime':time.time()-STARTED,
    }


def process_schedule():
    global CURRENT
    CURRENT='schedule'
    try:
        return bool(core._schedule_dispatch_due())
    except Exception as exc:
        _log_error("schedule",exc)
        return False
    finally:
        CURRENT='idle'


def process_lo_job():
    global CURRENT
    try: paths=sorted(core.LO_JOBS_DIR.glob('*.json'))
    except OSError: return False
    for path in paths:
        try: job=json.loads(path.read_text())
        except Exception: continue
        if job.get('status')!='queued': continue
        CURRENT=f"background job {job.get('id','?')}"
        try:
            core._run_lo_job(path)
            return True
        except Exception as exc:
            _log_error("background job",exc)
            return False
        finally:
            CURRENT='idle'
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


def memory_compile_due():
    """Use idle cycles for periodic memory compaction, never more than every six hours."""
    try:
        memory=core._load_memory()
        if not memory.get("durable"):
            return False
        if not memory.get("compiler_base") or not memory.get("compiler_model"):
            return False
        return time.time()-float(memory.get("last_compiled_at",0) or 0) >= 6*3600
    except Exception:
        return False


def process_memory_compile():
    global CURRENT,BACKOFF_UNTIL
    if not memory_compile_due():
        return False
    CURRENT='memory compile'
    try:
        memory=core._load_memory()
        base=str(memory.get("compiler_base") or "")
        model=str(memory.get("compiler_model") or "")
        core._ollama_tags(base)
        memory,changed=core._compile_memory(base,model,memory,force=True)
        core._save_memory(memory)
        if changed:
            core._emit_event('memory', 'memory summaries compacted')
        return True
    except Exception as exc:
        _log_error("memory compile",exc)
        BACKOFF_UNTIL=time.time()+60.0
        return False
    finally:
        CURRENT='idle'


def next_background_work():
    # Explicit user background jobs outrank housekeeping.
    if process_schedule(): return True
    if process_lo_job(): return True
    if process_memory(): return True
    if process_skill(): return True
    if process_memory_compile(): return True
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
        elif cmd=='permit':
            priority=str(msg.get('priority') or 'ambient')
            reply={'ok':True,'allowed':_permit(priority),'priority':priority,'current':CURRENT}
        elif cmd=='lease':
            ok=_set_client_lease(msg)
            WAKE=True
            reply={'ok':ok}
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

    # The socket protocol is authoritative. A stale PID can point to an
    # unrelated reused process and must never prevent Living AI from starting.
    if _socket_broker_alive():
        return 0

    # No responsive broker exists: clear stale runtime identity and claim it.
    try: SOCKET.unlink()
    except OSError: pass
    try: PID.unlink()
    except OSError: pass

    try:
        fd=os.open(PID,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        os.write(fd,str(os.getpid()).encode()); os.close(fd)
    except FileExistsError:
        # A simultaneous starter won the race. Trust it only if it becomes
        # responsive; otherwise this invocation fails softly and the caller's
        # one-shot fallback can still process durable work.
        for _ in range(10):
            time.sleep(.05)
            if _socket_broker_alive():
                return 0
        return 1

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
            try:
                if foreground_busy(): continue
                if time.time()<BACKOFF_UNTIL: continue
                # Drain one unit at a time so foreground can win between calls.
                schedule_due=bool(core._schedule_due())
                if WAKE or any(counts()) or schedule_due or memory_compile_due():
                    next_background_work()
                    WAKE=False
            except Exception as exc:
                # A malformed job or unexpected helper error must never kill the
                # resident coordinator. Durable queues remain for the next pass.
                _log_error("serve loop",exc)
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
