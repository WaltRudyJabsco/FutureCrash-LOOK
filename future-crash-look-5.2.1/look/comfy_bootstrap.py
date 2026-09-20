#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HOME=Path.home()
ASSUME_YES="--yes" in sys.argv
ASSUME_INSTALL="--install" in sys.argv or ASSUME_YES
DISCOVER_ONLY="--discover" in sys.argv
STATE=HOME/".local"/"share"/"look"
SERVICE_ROOT=STATE/"services"/"comfyui"
COMFY_ROOT=SERVICE_ROOT/"ComfyUI"
VENV=SERVICE_ROOT/"venv"
CONFIG=STATE/"comfy.json"

MODEL_EXTS={".safetensors",".ckpt",".pt",".pth",".gguf"}
COMFY_NAMES={"ComfyUI","comfyui"}
A1111_NAMES={"stable-diffusion-webui","stable-diffusion-webui-forge","automatic1111"}

SCAN_ROOTS=[
    HOME,
    Path("/mnt"),
    Path("/media")/os.environ.get("USER",""),
    Path("/run/media")/os.environ.get("USER",""),
]
SKIP_NAMES={".cache",".git","node_modules","venv",".venv","site-packages","proc","sys","dev"}

SDXL_URL="https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors?download=true"
SDXL_SHA256="31e35c80fc4829d14f90153f4c74cd59c90b779f6afe05a74cd6120b893f7e5b"
FLUX_SCHNELL_FP8_URL="https://huggingface.co/Comfy-Org/flux1-schnell/resolve/main/flux1-schnell-fp8.safetensors?download=true"
FLUX_SCHNELL_FP8_SHA256="ead426278b49030e9da5df862994f25ce94ab2ee4df38b556ddddb3db093bf72"


def ask(prompt:str, default=True)->bool:
    if ASSUME_YES:
        return True
    if ASSUME_YES or not sys.stdin.isatty():
        return default
    suffix=" [Y/n] " if default else " [y/N] "
    try:
        answer=input(prompt+suffix).strip().lower()
    except (EOFError,KeyboardInterrupt):
        print()
        return False
    return (answer not in {"n","no"}) if default else answer in {"y","yes"}


def choose(prompt:str, options:list[tuple[str,str]], default:str)->str:
    print(prompt)
    for key,label in options:
        mark="*" if key==default else " "
        print(f"  [{key}] {label}{'  ← default' if mark=='*' else ''}")
    if not sys.stdin.isatty():
        return default
    try:
        answer=input(f"Choose [{default}] › ").strip()
    except (EOFError,KeyboardInterrupt):
        print()
        return default
    return answer or default


def run(*args:str, cwd:Path|None=None):
    print("  →"," ".join(str(a) for a in args))
    subprocess.run([str(a) for a in args], cwd=str(cwd) if cwd else None, check=True)


def gpu_name()->str:
    try:
        out=subprocess.check_output(
            ["nvidia-smi","--query-gpu=name,memory.total","--format=csv,noheader,nounits"],
            text=True, stderr=subprocess.DEVNULL, timeout=4
        ).strip().splitlines()
        return "; ".join(x.strip() for x in out if x.strip())
    except Exception:
        return ""


def _walk_candidate_roots(root:Path, max_depth=5):
    if not root.exists():
        return
    base_depth=len(root.parts)
    for current, dirs, files in os.walk(root, followlinks=False):
        path=Path(current)
        depth=len(path.parts)-base_depth
        dirs[:]=[
            d for d in dirs
            if d not in SKIP_NAMES and not d.startswith(".Trash")
        ]
        if depth>=max_depth:
            dirs[:]=[]
        yield path, dirs, files


def discover():
    installs=[]
    a1111=[]
    model_dirs=set()
    model_files=[]
    seen=set()
    for root in SCAN_ROOTS:
        try:
            resolved=root.expanduser().resolve()
        except Exception:
            continue
        if str(resolved) in seen or not resolved.exists():
            continue
        seen.add(str(resolved))
        for path,dirs,files in _walk_candidate_roots(resolved,5):
            name=path.name
            if name in COMFY_NAMES and (path/"main.py").exists():
                installs.append(path)
                for rel in ("models/checkpoints","models/diffusion_models","models/unet","models/vae","models/loras","models/text_encoders"):
                    p=path/rel
                    if p.exists(): model_dirs.add(p)
                # Don't recurse deep into Comfy internals after recognition.
                dirs[:]=[d for d in dirs if d=="models"]
            elif name in A1111_NAMES:
                a1111.append(path)
                for rel in ("models/Stable-diffusion","models/VAE","models/Lora","models/ControlNet","embeddings"):
                    p=path/rel
                    if p.exists(): model_dirs.add(p)
            # Cheap model discovery: only likely model directories.
            if name.casefold() in {"checkpoints","stable-diffusion","diffusion_models","unet"}:
                model_dirs.add(path)
                # Old collections often organize checkpoints into subfolders by
                # model family. Scan a small bounded depth below a recognized
                # model root rather than assuming all weights sit at its top level.
                root_depth=len(path.parts)
                for current2,dirs2,files2 in os.walk(path,followlinks=False):
                    p2=Path(current2)
                    depth2=len(p2.parts)-root_depth
                    dirs2[:]=[d for d in dirs2 if d not in SKIP_NAMES and not d.startswith(".Trash")]
                    if depth2>=3:
                        dirs2[:]=[]
                    for f in files2:
                        fp=p2/f
                        if fp.suffix.casefold() in MODEL_EXTS:
                            try:
                                model_files.append((fp.stat().st_size,fp))
                            except OSError:
                                pass
                # Avoid descending through the same recognized model tree again.
                dirs[:]=[]

    installs=sorted(set(p.resolve() for p in installs))
    a1111=sorted(set(p.resolve() for p in a1111))
    model_dirs=sorted(set(p.resolve() for p in model_dirs))
    model_files=sorted(model_files, reverse=True)[:60]
    return installs,a1111,model_dirs,model_files


def print_discovery(installs,a1111,model_dirs,model_files):
    print("\nCOMFY DISCOVERY")
    print(f"  GPU          {gpu_name() or 'no NVIDIA GPU detected'}")
    print(f"  managed      {COMFY_ROOT if COMFY_ROOT.exists() else 'not installed'}")
    print(f"  old Comfy    {len(installs)}")
    for p in installs[:8]: print(f"    {p}")
    print(f"  A1111/Forge  {len(a1111)}")
    for p in a1111[:8]: print(f"    {p}")
    print(f"  model dirs   {len(model_dirs)}")
    for p in model_dirs[:12]: print(f"    {p}")
    print(f"  large models {len(model_files)}")
    for size,p in model_files[:12]:
        print(f"    {size/1024**3:5.1f} GB  {p.name}  ·  {p.parent}")


def ensure_managed_comfy():
    SERVICE_ROOT.mkdir(parents=True,exist_ok=True)
    if COMFY_ROOT.exists() and (COMFY_ROOT/".git").exists():
        print(f"  ✓ managed ComfyUI exists: {COMFY_ROOT}")
        if ask("  Update managed ComfyUI?", True):
            run("git","pull","--ff-only",cwd=COMFY_ROOT)
    elif COMFY_ROOT.exists():
        raise SystemExit(f"Refusing to replace non-git directory: {COMFY_ROOT}")
    else:
        run("git","clone","--depth=1","https://github.com/Comfy-Org/ComfyUI.git",str(COMFY_ROOT))

    if not VENV.exists():
        run(sys.executable,"-m","venv",str(VENV))
    py=VENV/"bin"/"python"
    pip=VENV/"bin"/"pip"
    run(str(py),"-m","pip","install","--upgrade","pip","wheel")
    # Current official NVIDIA manual-install recommendation.
    run(str(pip),"install","torch","torchvision","torchaudio","--extra-index-url","https://download.pytorch.org/whl/cu130")
    run(str(pip),"install","-r","requirements.txt",cwd=COMFY_ROOT)
    if (COMFY_ROOT/"manager_requirements.txt").exists():
        run(str(pip),"install","-r","manager_requirements.txt",cwd=COMFY_ROOT)
    return py


def write_extra_paths(installs,a1111,model_dirs):
    # Prefer structural roots because Comfy can map their subdirectories correctly.
    sections=[]
    idx=0
    covered=[]
    for p in installs:
        if p.resolve()==COMFY_ROOT.resolve():
            continue
        idx+=1
        covered.append(p.resolve())
        sections.append(
f"""look_comfy_{idx}:
    base_path: {json.dumps(str(p))}
    checkpoints: models/checkpoints
    diffusion_models: |
        models/diffusion_models
        models/unet
    vae: models/vae
    loras: models/loras
    text_encoders: models/text_encoders
    controlnet: models/controlnet
""")
    for p in a1111:
        idx+=1
        covered.append(p.resolve())
        sections.append(
f"""look_a1111_{idx}:
    base_path: {json.dumps(str(p))}
    checkpoints: models/Stable-diffusion
    vae: models/VAE
    loras: models/Lora
    controlnet: models/ControlNet
    embeddings: embeddings
""")

    # Loose checkpoint directories on mounted drives are useful too. Map only
    # folders whose names communicate the Comfy model type; never guess for
    # arbitrary directories.
    for p in model_dirs:
        rp=p.resolve()
        if any(root==rp or root in rp.parents for root in covered):
            continue
        name=rp.name.casefold()
        if name in {"checkpoints","stable-diffusion"}:
            field="checkpoints"
        elif name in {"diffusion_models","unet"}:
            field="diffusion_models"
        else:
            continue
        idx+=1
        sections.append(
f"""look_models_{idx}:
    base_path: {json.dumps(str(rp.parent))}
    {field}: {rp.name}
""")
    if not sections:
        return None
    target=COMFY_ROOT/"extra_model_paths.yaml"
    target.write_text(
        "# Generated by LOOK. Existing model libraries remain in place.\n\n"+
        "\n".join(sections),
        encoding="utf-8"
    )
    return target


def _sha256(path:Path):
    import hashlib
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def download(url:str,dest:Path,expected_sha256=""):
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists() and dest.stat().st_size>100_000_000:
        if not expected_sha256 or _sha256(dest)==expected_sha256:
            print(f"  ✓ already present: {dest.name}")
            return
        print(f"  ! checksum mismatch; redownloading {dest.name}")
        dest.unlink()
    curl=shutil.which("curl")
    wget=shutil.which("wget")
    if curl:
        run(curl,"-L","--fail","--continue-at","-","-o",str(dest),url)
    elif wget:
        run(wget,"-c","-O",str(dest),url)
    else:
        raise SystemExit("Need curl or wget to download a starter image model.")
    if expected_sha256:
        actual=_sha256(dest)
        if actual!=expected_sha256:
            raise SystemExit(f"Checksum verification failed for {dest.name}: {actual}")
        print(f"  ✓ verified SHA-256 · {dest.name}")


def starter_models(model_files):
    names={p.name.casefold() for _,p in model_files}
    have_sdxl=any("sd_xl_base_1.0" in n or "sdxl" in n for n in names)
    have_flux=any("flux1-schnell" in n or "flux.1-schnell" in n for n in names)

    print("\nSTARTER IMAGE MODEL")
    if have_sdxl or have_flux:
        print("  Existing generation-capable files were detected.")
        if have_sdxl: print("  ✓ SDXL-like model detected")
        if have_flux: print("  ✓ FLUX Schnell-like model detected")

    choice=choose(
        "Choose an optional starter download:",
        [
            ("1","Reuse existing models only · no large download"),
            ("2","SDXL 1.0 base · ready-to-run LOOK starter · ~6.9 GB"),
            ("3","FLUX.1 Schnell FP8 · modern fast checkpoint · ~17.2 GB"),
            ("4","Both SDXL + FLUX Schnell FP8 · ~24 GB"),
            ("5","Skip model setup"),
        ],
        "1" if (have_sdxl or have_flux) else "2",
    )
    checkpoints=COMFY_ROOT/"models"/"checkpoints"
    installed_sdxl=have_sdxl
    if choice in {"2","4"}:
        download(SDXL_URL,checkpoints/"sd_xl_base_1.0.safetensors",SDXL_SHA256)
        installed_sdxl=True
    if choice in {"3","4"}:
        download(FLUX_SCHNELL_FP8_URL,checkpoints/"flux1-schnell-fp8.safetensors",FLUX_SCHNELL_FP8_SHA256)
    return installed_sdxl


def write_runtime(configure_sdxl=False):
    STATE.mkdir(parents=True,exist_ok=True)
    current={}
    if CONFIG.exists():
        try: current=json.loads(CONFIG.read_text())
        except Exception: current={}
    current.update({
        "host":"http://127.0.0.1:8188",
        "install_path":str(COMFY_ROOT),
        "python":str(VENV/"bin"/"python"),
        "output_dir":str(HOME/"Pictures"/"LOOK"),
        "auto_preview":True,
    })
    if configure_sdxl:
        source=Path(__file__).resolve().parent/"workflows"/"sdxl-api.json"
        target=STATE/"workflows"/"sdxl-api.json"
        if source.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)
            current["workflow"]=str(target)
    current.setdefault("workflow","")
    CONFIG.write_text(json.dumps(current,indent=2)+"\n")
    os.chmod(CONFIG,0o600)

    launcher=HOME/".local"/"bin"/"look-comfy"
    launcher.parent.mkdir(parents=True,exist_ok=True)
    import shlex
    launcher.write_text(
f"""#!/usr/bin/env bash
set -euo pipefail
cd {shlex.quote(str(COMFY_ROOT))}
exec {shlex.quote(str(VENV/'bin'/'python'))} main.py --listen 127.0.0.1 --port 8188 --enable-manager "$@"
""")
    launcher.chmod(0o755)


def main():
    print("LOOK COMFY WORKSTATION BOOTSTRAP")
    installs,a1111,model_dirs,model_files=discover()
    print_discovery(installs,a1111,model_dirs,model_files)
    if DISCOVER_ONLY:
        return 0

    if sys.platform!="linux":
        print("\n  Managed Comfy install is offered only on Linux in this bootstrap.")
        print("  Configure a remote GPU host with: lk comfy host http://HOST:8188")
        return 0
    if not gpu_name():
        print("\n  No NVIDIA GPU detected. Skipping managed GPU installation.")
        return 0

    if not ASSUME_INSTALL and not ask("\nInstall/update managed ComfyUI for this NVIDIA workstation?", True):
        print("  · skipped managed ComfyUI")
        return 0

    ensure_managed_comfy()

    if (installs or a1111) and ask("\nReuse discovered model libraries without copying them?", True):
        path=write_extra_paths(installs,a1111,model_dirs)
        if path: print(f"  ✓ wrote {path}")

    sdxl_ready=starter_models(model_files)
    write_runtime(configure_sdxl=sdxl_ready)

    print("\nLOOK COMFY READY")
    print(f"  install   {COMFY_ROOT}")
    print(f"  launcher  {HOME/'.local/bin/look-comfy'}")
    print("  local API http://127.0.0.1:8188")
    print("  start     look-comfy")
    print("  inspect   lk comfy")
    cfg=json.loads(CONFIG.read_text()) if CONFIG.exists() else {}
    if cfg.get("workflow"):
        print(f"  workflow  {cfg['workflow']} · ready for `lk generate ...`")
    else:
        print("  NOTE: configure an API-format workflow with `lk comfy workflow PATH` before LO generation.")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
