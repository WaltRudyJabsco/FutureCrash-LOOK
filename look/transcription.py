"""Optional local speech input. Models stay behind a file-to-text boundary."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from urllib.parse import urlsplit
import wave

MODEL='phonon-2'
RUNTIME_VERSION='0.2.11'
TRANSCRIBE_TIMEOUT=3600
MAX_SERVER_AUDIO_BYTES=32*1024*1024


def root():return Path.home()/'.local/share/look/transcription'
def config_path():return Path.home()/'.config/look/transcription.json'


def server_url(value):
    parsed=urlsplit(value)
    if parsed.scheme!='http' or parsed.hostname not in {'localhost','127.0.0.1','::1'} or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Use a local HTTP transcription server, such as http://127.0.0.1:8000/v1')
    return value.rstrip('/')


def settings():
    try:data=json.loads(config_path().read_text())
    except FileNotFoundError:data={}
    if not isinstance(data,dict):raise ValueError('Invalid transcription settings')
    if data.get('server'):data['server']=server_url(data['server'])
    return data


def executable():
    installed=root()/'venv/bin/fermion'
    return str(installed) if installed.is_file() else shutil.which('fermion')


def offline_env():return dict(os.environ,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')


def setup():
    """Explicit dependency/model download; never invoked during normal install."""
    destination=root()/'venv'
    if not (destination/'bin/python').is_file():
        python=shutil.which('python3.12') or sys.executable
        subprocess.run([python,'-m','venv',str(destination)],check=True)
    packages=['fermion-research=='+RUNTIME_VERSION,'soundfile','scipy','zstandard','sounddevice']
    if sys.platform=='darwin' and os.uname().machine=='arm64':packages+=['mlx','mlx-audio','mlx-lm']
    else:
        if sys.platform.startswith('linux'):
            # Avoid pulling CUDA libraries into the default CPU speech setup.
            subprocess.run([str(destination/'bin/python'),'-m','pip','install','--no-deps','torch','--index-url','https://download.pytorch.org/whl/cpu'],check=True)
        packages+=['torch','safetensors']
    print('Installing optional local speech runtime: about 1.3 GB on the tested Mac, plus the 164 MB model download.',file=sys.stderr)
    subprocess.run([str(destination/'bin/python'),'-m','pip','install',*packages],check=True)
    with tempfile.TemporaryDirectory(prefix='look-speech-') as temporary:
        sample=Path(temporary)/'silence.wav'
        with wave.open(str(sample),'wb') as audio:
            audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000);audio.writeframes(b'\0\0'*1600)
        subprocess.run([str(destination/'bin/fermion'),'transcribe',MODEL,str(sample),'--download-only'],check=True)
    print('Speech files downloaded. lk transcribe FILE runs offline; lk dictate starts the microphone explicitly.')


def transcribe(path,model=None):
    """Return transcript text; never execute it or modify the source recording."""
    source=Path(path).expanduser().resolve()
    if not source.is_file():raise ValueError('Audio file does not exist')
    config=settings()
    # Normalize locally for consistent engines, including movie/voice-note input.
    with tempfile.TemporaryDirectory(prefix='look-transcribe-') as temporary:
        audio=source
        if source.suffix.casefold() not in {'.wav','.flac','.ogg','.aiff','.aif'}:
            ffmpeg=shutil.which('ffmpeg')
            if not ffmpeg:raise ValueError('Install ffmpeg to transcribe this format, or supply WAV/FLAC/OGG/AIFF')
            audio=Path(temporary)/'audio.wav'
            subprocess.run([ffmpeg,'-nostdin','-v','error','-i',str(source),'-vn','-ac','1','-ar','16000',str(audio)],check=True)
        if config.get('server'):
            if audio.stat().st_size>MAX_SERVER_AUDIO_BYTES:raise ValueError('Local server upload exceeds 32 MiB; use the file engine for longer recordings')
            data=audio.read_bytes()
            boundary='look-transcription-upload'
            model=str(model or config.get('model') or MODEL)
            if any(c in model for c in '\r\n'):raise ValueError('Invalid model name')
            body=(f'--{boundary}\r\nContent-Disposition: form-data; name="model"\r\n\r\n{model}\r\n'
                  f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="audio{audio.suffix}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()+data+f'\r\n--{boundary}--\r\n'.encode()
            request=urllib.request.Request(config['server']+'/audio/transcriptions',data=body,headers={'Content-Type':'multipart/form-data; boundary='+boundary})
            with urllib.request.urlopen(request,timeout=TRANSCRIBE_TIMEOUT) as response:result=json.load(response)
            text=result.get('text')
        else:
            command=executable()
            if not command:raise ValueError('Speech engine not installed. Run lk transcribe setup, or lk transcribe configure --server LOCAL_URL')
            result=subprocess.run([command,'transcribe',str(model or config.get('model') or MODEL),str(audio),'--json'],capture_output=True,text=True,env=offline_env(),timeout=TRANSCRIBE_TIMEOUT)
            if result.returncode:raise ValueError(result.stderr.strip() or 'Local transcription failed; run lk transcribe setup to download the model')
            decoded=json.loads(result.stdout)
            if decoded.get('truncated'):raise ValueError('Engine reports a truncated transcript; source recording was retained')
            text=decoded.get('text')
        if not isinstance(text,str):raise ValueError('Speech engine returned no transcript text')
        from notebook_markdown import safe_text
        return safe_text(text.strip())


# Capture runs in the optional speech environment, keeping audio dependencies out
# of LOOK's Python process. Samples stream to a temporary file, not system output.
CAPTURE_PROGRAM = r"""
import sys, queue
try:
    import sounddevice as sd
    import soundfile as sf
    from threading import Event
    pending=queue.Queue(maxsize=128)
    overflow=Event()
    def receive(data,frames,timing,status):
        if status:overflow.set()
        try:pending.put_nowait(data.copy())
        except queue.Full:overflow.set()
    with sf.SoundFile(sys.argv[1],mode='w',samplerate=16000,channels=1,subtype='PCM_16',format='WAV') as output:
        try:
            with sd.InputStream(samplerate=16000,channels=1,callback=receive):
                print('Recording microphone · Ctrl-C finishes',file=sys.stderr,flush=True)
                while True:
                    try:output.write(pending.get(timeout=.1))
                    except queue.Empty:pass
                    if overflow.is_set():raise RuntimeError('Audio capture could not keep up; recording stopped')
        except KeyboardInterrupt:
            while not pending.empty():output.write(pending.get_nowait())
except Exception as exc:
    print('Microphone unavailable: '+str(exc)+'; check speech setup, PortAudio and microphone permissions.',file=sys.stderr)
    raise SystemExit(1)
"""


def speech_process(command):
    process=subprocess.Popen(command,stdout=subprocess.PIPE,text=True,env=offline_env(),start_new_session=True)
    try:
        try:text,_=process.communicate()
        except KeyboardInterrupt:
            process.send_signal(signal.SIGINT);text,_=process.communicate(timeout=20)
        if process.returncode not in {0,130,-signal.SIGINT}:raise ValueError('Dictation failed; check engine setup and microphone permission')
        return text
    finally:
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)


def recorded_dictation(model=None):
    python=root()/'venv/bin/python'
    if not python.is_file():raise ValueError('Run lk transcribe setup to install microphone capture dependencies')
    with tempfile.TemporaryDirectory(prefix='look-dictate-') as temporary:
        path=Path(temporary)/'recording.wav'
        try:
            speech_process([str(python),'-c',CAPTURE_PROGRAM,str(path)])
            with wave.open(str(path),'rb') as audio:
                if not audio.getnframes():return ''
            print('Transcribing local recording…',file=sys.stderr)
            return transcribe(path,model)
        except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:
            if path.is_file() and path.stat().st_size>44:
                recovery=root()/'recovery';recovery.mkdir(parents=True,exist_ok=True,mode=0o700)
                saved=recovery/(str(time.time_ns())+'.wav')
                shutil.copyfile(path,saved);saved.chmod(0o600)
                raise ValueError('Dictation failed; recording kept at '+str(saved)+' · '+str(exc)) from exc
            raise



def dictate(model=None):
    config=settings()
    print('Microphone dictation · Ctrl-C finishes · no commands are executed',file=sys.stderr)
    # The pinned Fermion listen implementation uses MLX. Other platforms and
    # alternate local servers use capture-then-transcribe through the same API.
    if sys.platform!='darwin' or os.uname().machine!='arm64' or config.get('server'):
        return recorded_dictation(model)
    command=executable()
    if not command:raise ValueError('Run lk transcribe setup before microphone dictation')
    from notebook_markdown import safe_text
    return safe_text(speech_process([command,'listen',str(model or config.get('model') or MODEL)]).strip())


def main(argv=None,live=False):
    parser=argparse.ArgumentParser(prog='lk dictate' if live else 'lk transcribe',description='Optional offline speech input; never executes the words you say.')
    parser.add_argument('target',nargs='?',help='Audio/video file, status, setup, or configure')
    parser.add_argument('--server',help='Loopback OpenAI-compatible /v1 base URL')
    parser.add_argument('--model',help='Override the configured model for this command')
    parser.add_argument('--output',help='Create a new UTF-8 transcript file; never overwrite')
    parser.add_argument('--note',metavar='TITLE',help='Save the transcript as a new Notebook note')
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args(argv)
    if live and args.target:parser.error('dictate takes options only; use lk transcribe FILE for a recording')
    try:
        if not live and args.target=='setup':setup();return 0
        if not live and args.target=='configure':
            data={'model':args.model or MODEL}
            if args.server:data['server']=server_url(args.server)
            config_path().parent.mkdir(parents=True,exist_ok=True)
            with tempfile.NamedTemporaryFile('w',dir=config_path().parent,delete=False) as stream:
                json.dump(data,stream);temporary=stream.name
            os.chmod(temporary,0o600);os.replace(temporary,config_path())
            print('Saved local transcription settings');return 0
        if not live and args.target in {None,'status'}:
            config=settings();print(json.dumps({'engine':'local-server' if config.get('server') else 'fermion','model':config.get('model') or MODEL,'installed':bool(config.get('server') or executable()),'setup':'lk transcribe setup','note':'Runtime presence does not verify model readiness. Setup downloads; transcription runs offline.'},indent=2));return 0
        text=dictate(args.model) if live else transcribe(args.target,args.model)
        if args.output:
            with Path(args.output).expanduser().open('x',encoding='utf-8') as output:output.write(text+'\n')
        result={'text':text}
        if args.note:
            if not text:raise ValueError('No speech detected; no note created')
            from notebook import Notebook,nudge_sync
            result['note_id']=Notebook().create(args.note+'\n\n'+text,project='Transcripts')['note'];nudge_sync()
        print(json.dumps(result,ensure_ascii=False) if args.json else text)
        if args.note and not args.json:print('Saved note: '+result['note_id'],file=sys.stderr)
        return 0
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as exc:
        print('LOOK TRANSCRIPTION · '+str(exc),file=sys.stderr);return 1
    except KeyboardInterrupt:return 130

if __name__=='__main__':raise SystemExit(main())
