#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PRODUCT_VERSION="5.6.2"
LOOK_VERSION="4.48.0"
FUTURE_CRASH_VERSION="1.2.2"

DRY=0
ASSUME_YES=0
NO_OPTIONAL=0
FORCE_DOWNGRADE=0
BREW_BOOTSTRAPPED=0
installed_packages=()
created_dirs=()
ZSH_BACKUP=""

usage() {
  cat <<'EOF'
LOOK + FUTURE CRASH — system installer

Usage:
  ./install.sh [--dry-run] [--yes] [--no-optional] [--force-downgrade] [--openjev=MODE] [--uninstall]

  --dry-run          show what the installer would do
  --yes              accept optional component prompts
  --no-optional      install without optional Remote + AI/media components
  --force-downgrade  deliberately install over a newer unified release
  --openjev=MODE     unified installer option; LOOK accepts and defers it
  --uninstall        remove Future Crash + LOOK owned files
EOF
}

while (($#)); do
  case "$1" in
    --dry-run) DRY=1 ;;
    --yes|-y) ASSUME_YES=1 ;;
    --no-optional) NO_OPTIONAL=1 ;;
    --force-downgrade) FORCE_DOWNGRADE=1 ;;
    --openjev=off|--openjev=auto|--openjev=adopt|--openjev=install) : ;;
    --uninstall)
      if command -v lk >/dev/null 2>&1; then
        exec lk uninstall
      fi
      echo "LOOK is not installed; nothing to uninstall."
      exit 0
      ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown option: $1"; usage; exit 2 ;;
  esac
  shift
done

have(){ command -v "$1" >/dev/null 2>&1; }
run(){ if ((DRY)); then printf '  →'; printf ' %q' "$@"; printf '\n'; else "$@"; fi; }
ask() {
  local prompt="$1" default="$2" answer
  if ((NO_OPTIONAL)); then return 1; fi
  if ((ASSUME_YES)); then return 0; fi
  if ((DRY)) || [[ ! -t 0 ]]; then
    [[ "$default" == "Y" ]]
    return
  fi
  if [[ "$default" == "Y" ]]; then
    read -r -p "$prompt [Y/n] " answer
    [[ ! "$answer" =~ ^[Nn] ]]
  else
    read -r -p "$prompt [y/N] " answer
    [[ "$answer" =~ ^[Yy] ]]
  fi
}


version_lt() {
  local a="$1" b="$2"
  local a1=0 a2=0 a3=0 b1=0 b2=0 b3=0
  IFS=. read -r a1 a2 a3 <<< "${a%%[-+]*}"
  IFS=. read -r b1 b2 b3 <<< "${b%%[-+]*}"
  a1=${a1:-0}; a2=${a2:-0}; a3=${a3:-0}
  b1=${b1:-0}; b2=${b2:-0}; b3=${b3:-0}
  (( a1 < b1 )) && return 0
  (( a1 > b1 )) && return 1
  (( a2 < b2 )) && return 0
  (( a2 > b2 )) && return 1
  (( a3 < b3 ))
}

installed_release_version() {
  local manifest="$HOME/.local/share/look/install_manifest.json"
  [[ -f "$manifest" ]] || return 1
  local value=""
  value="$(sed -n 's/.*"release"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$manifest" | head -n1)"
  if [[ -z "$value" ]]; then
    value="$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"future-crash-look-\([^"]*\)".*/\1/p' "$manifest" | head -n1)"
  fi
  [[ -n "$value" ]] || return 1
  printf '%s\n' "$value"
}

preflight_version_guard() {
  local installed=""
  installed="$(installed_release_version || true)"
  [[ -n "$installed" ]] || return 0

  if version_lt "$PRODUCT_VERSION" "$installed"; then
    echo
    echo "VERSION GUARD"
    echo "  installed: Future Crash + LOOK $installed"
    echo "  requested: Future Crash + LOOK $PRODUCT_VERSION"
    if ((FORCE_DOWNGRADE)); then
      echo "  ! deliberate downgrade allowed by --force-downgrade"
    else
      echo "  Refusing to overwrite a newer unified installation."
      echo "  Use --force-downgrade only if you intentionally want the older release."
      exit 3
    fi
  elif [[ "$PRODUCT_VERSION" == "$installed" ]]; then
    echo "  ✓ Future Crash + LOOK $PRODUCT_VERSION already installed; reconciling files"
  else
    echo "  ↑ updating Future Crash + LOOK $installed → $PRODUCT_VERSION"
  fi
}

preflight_version_guard

echo "FUTURE CRASH + LOOK $PRODUCT_VERSION — terminal environment installer"
echo "LOOK $LOOK_VERSION · Future Crash $FUTURE_CRASH_VERSION · $(uname -s) · $(uname -m)"
echo
echo "One install: LOOK underneath, Future Crash on top."
echo "Remote access and local AI remain optional."

if ! have brew; then
  if ((DRY)); then
    echo "✗ Homebrew/Linuxbrew (would bootstrap)"
  else
    echo
    echo "BOOTSTRAP"
    echo "  LOOK uses Homebrew/Linuxbrew as its package layer."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    BREW_BOOTSTRAPPED=1
    [[ -x /opt/homebrew/bin/brew ]] && eval "$(/opt/homebrew/bin/brew shellenv)"
    [[ -x /home/linuxbrew/.linuxbrew/bin/brew ]] && eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
  fi
fi

package_for() {
  case "$1" in
    python3) printf '%s\n' python ;;
    nvim) printf '%s\n' neovim ;;
    pdftotext) printf '%s\n' poppler ;;
    *) printf '%s\n' "$1" ;;
  esac
}

echo
echo "LOOK WORKSTATION"
core=(zsh python3 git zoxide fzf fd nvim bat fortune cowsay fastfetch chafa pdftotext ttyd lsof mpv)
missing=()
for c in "${core[@]}"; do
  if have "$c"; then
    printf '  ✓ %s\n' "$c"
  else
    printf '  ✗ %s\n' "$c"
    missing+=("$(package_for "$c")")
  fi
done
if ((${#missing[@]})); then
  run brew install "${missing[@]}"
  if ((!DRY)); then installed_packages+=("${missing[@]}"); fi
fi

# Remote is deliberately offered rather than silently assumed: installation is
# useful only after the user authenticates this machine into a tailnet.
echo
echo "LOOK REMOTE"
if have tailscale; then
  echo "  ✓ tailscale"
else
  echo "  webterm() can expose this shell securely to your own devices."
  if ask "  Install Tailscale?" Y; then
    run brew install tailscale
    if ((!DRY)); then installed_packages+=("tailscale"); fi
  else
    echo "  · skipped tailscale"
  fi
fi

# Ollama is a larger choice. LOOK supports it deeply but does not require it.
echo
echo "LOOK AI"
if have ollama; then
  echo "  ✓ ollama"
else
  echo "  lo adds local chat, workspace tools, memory, search, and PDF reading."
  if ask "  Install Ollama?" N; then
    run brew install ollama
    if ((!DRY)); then installed_packages+=("ollama"); fi
  else
    echo "  · skipped ollama"
  fi
fi

# On a Linux NVIDIA workstation, LOOK can own a clean isolated ComfyUI service.
# Discovery runs before install so old model libraries on mounted drives can be reused.
echo
echo "LOOK GENERATIVE MEDIA"
if [[ "$(uname -s)" == "Linux" ]] && have nvidia-smi; then
  gpu_line="$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits 2>/dev/null | head -n1 || true)"
  echo "  ✓ NVIDIA GPU${gpu_line:+ · $gpu_line}"
  echo "  ComfyUI enables local image generation; old model folders can be reused without copying."
  if ask "  Set up local ComfyUI image generation on this GPU?" Y; then
    comfy_args=(--install)
    ((ASSUME_YES)) && comfy_args+=(--yes)
    if ((DRY)); then
      echo "  → python3 $ROOT/look/comfy_bootstrap.py ${comfy_args[*]}"
    else
      python3 "$ROOT/look/comfy_bootstrap.py" "${comfy_args[@]}"
    fi
  else
    echo "  · skipped ComfyUI setup"
  fi
else
  echo "  · no Linux NVIDIA GPU detected on this machine"
  echo "  A client can still use ComfyUI hosted on another LOOK machine."
fi

echo
echo "LOOK MEDIA"
if have mpv; then
  echo "  ✓ mpv · canonical local/Fabric playback edge"
else
  echo "  ! mpv should have been installed with the workstation dependencies"
  echo "    media control remains available, but this node will not advertise playback until mpv is present"
fi

ZDIR="${ZSH:-$HOME/.oh-my-zsh}"
if [[ ! -d "$ZDIR" ]]; then
  run git clone --depth=1 https://github.com/ohmyzsh/ohmyzsh.git "$ZDIR"
  if ((!DRY)); then created_dirs+=("$ZDIR"); fi
fi
CUSTOM="${ZSH_CUSTOM:-$ZDIR/custom}"
clone() {
  if [[ ! -d "$2" ]]; then
    run git clone --depth=1 "$1" "$2"
    if ((!DRY)); then created_dirs+=("$2"); fi
  fi
}
clone https://github.com/romkatv/powerlevel10k.git "$CUSTOM/themes/powerlevel10k"
clone https://github.com/zsh-users/zsh-autosuggestions.git "$CUSTOM/plugins/zsh-autosuggestions"
clone https://github.com/zsh-users/zsh-syntax-highlighting.git "$CUSTOM/plugins/zsh-syntax-highlighting"

if have lk; then
  existing_lk="$(command -v lk)"
  case "$existing_lk" in
    "$HOME/.local/bin/lk"|"$HOME/.local/share/look/lk") ;;
    *)
      echo "WARNING: 'lk' already exists at: $existing_lk"
      echo "LOOK will install ~/.local/bin/lk; review this collision if that command matters to you."
      ;;
  esac
fi

run mkdir -p "$HOME/.local/share/look" "$HOME/.local/bin"

# A resident Living AI process has imported the currently installed LOOK code.
# Stop it BEFORE replacing those files so an upgrade can never leave old policy
# executing against new on-disk state.
if ((!DRY)); then
  OLD_LOOK="$HOME/.local/share/look/lk"
  if [[ -x "$OLD_LOOK" ]]; then
    "$OLD_LOOK" ai stop >/dev/null 2>&1 || true
    for _ in {1..50}; do
      [[ ! -S "$HOME/.local/share/look/ai.sock" && ! -f "$HOME/.local/share/look/ai.pid" ]] && break
      sleep 0.05
    done
  fi

  MEMORY="$HOME/.local/share/look/ollama_memory.json"
  if [[ ! -f "$MEMORY" ]]; then
    printf '{"long":"","recent":[]}\n' > "$MEMORY"
    chmod 600 "$MEMORY"
  fi
fi

run cp "$ROOT/look/lk" "$HOME/.local/share/look/lk"
run cp "$ROOT/look/look_renderer.py" "$HOME/.local/share/look/look_renderer.py"
run cp "$ROOT/look/look_ai.py" "$HOME/.local/share/look/look_ai.py"
run cp "$ROOT/look/lo_engine.py" "$HOME/.local/share/look/lo_engine.py"
run cp "$ROOT/look/media_core.py" "$HOME/.local/share/look/media_core.py"
run cp "$ROOT/look/file_catalog.py" "$HOME/.local/share/look/file_catalog.py"
run cp "$ROOT/look/comfy_bootstrap.py" "$HOME/.local/share/look/comfy_bootstrap.py"
run chmod +x "$HOME/.local/share/look/look_ai.py" "$HOME/.local/share/look/comfy_bootstrap.py"
run mkdir -p "$HOME/.local/share/look/workflows"
run cp "$ROOT/look/workflows/sdxl-api.json" "$HOME/.local/share/look/workflows/sdxl-api.json"
run chmod +x "$HOME/.local/share/look/lk"
if ((!DRY)); then
  ln -sfn "$HOME/.local/share/look/lk" "$HOME/.local/bin/lk"
  # Start the newly installed broker now. The shell hook remains a fallback.
  "$HOME/.local/share/look/lk" ai start >/dev/null 2>&1 || true
  # Reconcile an already-configured Ollama tailnet share into the native user
  # service manager. This is topology discovery, not a Linux assumption: LOOK
  # chooses systemd on Linux, launchd on macOS, and process fallback elsewhere.
  if command -v tailscale >/dev/null 2>&1 && tailscale serve status 2>/dev/null | grep -q ':11435'; then
    "$HOME/.local/share/look/lk" ollama share >/dev/null 2>&1 || true
  fi
fi

LOOK_ZSH_DIR="$HOME/.config/look"
LOOK_ZSH_FILE="$LOOK_ZSH_DIR/look.zsh"
LOOK_HOOK_START="# >>> LOOK Shell >>>"
LOOK_HOOK_END="# <<< LOOK Shell <<<"

run mkdir -p "$LOOK_ZSH_DIR"

if [[ -f "$HOME/.zshrc" ]]; then
  B="$HOME/.zshrc.backup.$(date +%Y%m%d-%H%M%S)"
  run cp "$HOME/.zshrc" "$B"
  ZSH_BACKUP="$B"
  echo "Backed up ~/.zshrc → $B"
fi

# LOOK owns this fragment; the user's ~/.zshrc remains theirs.
run cp "$ROOT/look/zshrc" "$LOOK_ZSH_FILE"
run mkdir -p "$LOOK_ZSH_DIR/completions"
run cp "$ROOT/look/completions/_lk" "$LOOK_ZSH_DIR/completions/_lk"
run cp "$ROOT/look/completions/_lo" "$LOOK_ZSH_DIR/completions/_lo"
run cp "$ROOT/look/completions/_lmk" "$LOOK_ZSH_DIR/completions/_lmk"

if ((!DRY)); then
  touch "$HOME/.zshrc"
  python3 - "$HOME/.zshrc" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text() if path.exists() else ""
start = "# >>> LOOK Shell >>>"
end = "# <<< LOOK Shell <<<"

while start in text:
    a = text.find(start)
    b = text.find(end, a)
    if b < 0:
        text = text[:a].rstrip() + "\n"
        break
    b += len(end)
    left = text[:a].rstrip()
    right = text[b:].lstrip("\n")
    text = (left + "\n\n" if left else "") + right

hook = """# >>> LOOK Shell >>>
[[ -f "$HOME/.config/look/look.zsh" ]] && source "$HOME/.config/look/look.zsh"
# <<< LOOK Shell <<<
"""
text = text.rstrip()
if text:
    text += "\n\n"
text += hook
path.write_text(text)
PY
fi

[[ -f "$HOME/.zsh_secrets" ]] || run cp "$ROOT/look/zsh_secrets.example" "$HOME/.zsh_secrets"
run chmod 600 "$HOME/.zsh_secrets"

if ((!DRY)); then
  zsh -n "$LOOK_ZSH_FILE"
  zsh -n "$HOME/.zshrc"

  # Seed LO intelligence without overwriting local memory or learned craft.
  LOOK_STATE="$HOME/.local/share/look"
  run mkdir -p "$LOOK_STATE"
  [[ -f "$LOOK_STATE/core.md" ]] || run cp "$ROOT/look/core.md" "$LOOK_STATE/core.md"
  [[ -f "$LOOK_STATE/skills.md" ]] || run cp "$ROOT/look/skills.md" "$LOOK_STATE/skills.md"
  run mkdir -p "$LOOK_STATE/personalities"
  # Bundled personalities are release-owned instruction packs; user selection is stored separately.
  for personality in "$ROOT"/look/personalities/*.md; do
    [[ -f "$personality" ]] && run cp "$personality" "$LOOK_STATE/personalities/"
  done
  [[ -f "$LOOK_STATE/ollama_memory.json" ]] || run cp "$ROOT/look/memory.json" "$LOOK_STATE/ollama_memory.json"

  FUTURE_DIR="$HOME/.local/share/future-crash"
  run mkdir -p "$FUTURE_DIR"
  run cp "$ROOT/future-crash/future_crash.py" "$FUTURE_DIR/future_crash.py"
run cp "$ROOT/future-crash/personality.md" "$FUTURE_DIR/personality.md"
  run cp "$ROOT/future-crash/future-crash" "$HOME/.local/bin/future-crash"
  run chmod +x "$HOME/.local/bin/future-crash"

  # Record only what this installer can prove it added. `lk uninstall` uses
  # this manifest so it never guesses that a pre-existing package belongs to LOOK.
  export LOOK_MANIFEST_PACKAGES="$(printf '%s\n' "${installed_packages[@]-}")"
  export LOOK_MANIFEST_DIRS="$(printf '%s\n' "${created_dirs[@]-}")"
  export LOOK_MANIFEST_ZSH_BACKUP="$ZSH_BACKUP"
  export LOOK_MANIFEST_BREW_BOOTSTRAPPED="$BREW_BOOTSTRAPPED"
  export FCL_RELEASE_VERSION="$PRODUCT_VERSION"
  export FCL_LOOK_VERSION="$LOOK_VERSION"
  export FCL_FUTURE_CRASH_VERSION="$FUTURE_CRASH_VERSION"
  python3 - <<'PY'
import json, os
from pathlib import Path

state = Path.home()/".local/share/look"
state.mkdir(parents=True, exist_ok=True)
old = {}
old_path = state/"install_manifest.json"
try:
    old = json.loads(old_path.read_text())
except Exception:
    old = {}

old_packages = old.get("packages") if isinstance(old.get("packages"), list) else []
old_dirs = old.get("created_dirs") if isinstance(old.get("created_dirs"), list) else []

manifest = {
    "product": "future-crash-look",
    "release": os.environ.get("FCL_RELEASE_VERSION", "3.1.0"),
    "components": {
        "look": os.environ.get("FCL_LOOK_VERSION", "4.31.0"),
        "future_crash": os.environ.get("FCL_FUTURE_CRASH_VERSION", "1.1.14"),
    },
    "packages": sorted(set(old_packages + [x for x in os.environ.get("LOOK_MANIFEST_PACKAGES","").splitlines() if x])),
    "created_dirs": sorted(set(old_dirs + [x for x in os.environ.get("LOOK_MANIFEST_DIRS","").splitlines() if x])),
    "zsh_backup": os.environ.get("LOOK_MANIFEST_ZSH_BACKUP","") or old.get("zsh_backup",""),
    "brew_bootstrapped": (os.environ.get("LOOK_MANIFEST_BREW_BOOTSTRAPPED","0") == "1") or bool(old.get("brew_bootstrapped", False)),
}
tmp = state/"install_manifest.json.tmp"
tmp.write_text(json.dumps(manifest, indent=2) + "\n")
tmp.chmod(0o600)
tmp.replace(state/"install_manifest.json")
PY

  # Optional reference terminal experience. Core remains independent.
  TERMINAL_OS="$(uname -s 2>/dev/null || echo unknown)"
  echo
  echo "TERMINAL EXPERIENCE"
  if [[ "$TERMINAL_OS" == "Darwin" ]]; then
    echo "  Recommended: iTerm2 · Zsh · Powerlevel10k · MesloLGS NF"
  else
    echo "  Recommended: Kitty · Zsh · Powerlevel10k · MesloLGS NF"
  fi
  echo "  Future Crash + LOOK works without these."
  echo
  if ask "  Install/check recommended terminal components?" N; then
    if [[ "$TERMINAL_OS" == "Darwin" ]] && command -v brew >/dev/null 2>&1; then
      [[ -d "/Applications/iTerm.app" || -d "$HOME/Applications/iTerm.app" ]] \
        && echo "  ✓ iTerm2" \
        || run brew install --cask iterm2
      if system_profiler SPFontsDataType 2>/dev/null | grep -qi "MesloLGS"; then
        echo "  ✓ MesloLGS NF"
      else
        echo "  Installing MesloLGS NF…"
        if [[ "${DRY_RUN:-0}" == "1" ]]; then
          echo "  [dry-run] brew install --cask font-meslo-lg-nerd-font"
        else
          brew install --cask font-meslo-lg-nerd-font || echo "  Optional font install failed; continuing."
        fi
      fi
    elif [[ "$TERMINAL_OS" != "Darwin" ]]; then
      if command -v kitty >/dev/null 2>&1; then
        echo "  ✓ Kitty"
      elif command -v apt-get >/dev/null 2>&1; then
        run sudo apt-get install -y kitty
      elif command -v dnf >/dev/null 2>&1; then
        run sudo dnf install -y kitty
      elif command -v pacman >/dev/null 2>&1; then
        run sudo pacman -S --noconfirm kitty
      else
        echo "  Kitty not found; install it with your distribution's package manager."
      fi
      if command -v fc-list >/dev/null 2>&1 && fc-list | grep -qi "MesloLGS"; then
        echo "  ✓ MesloLGS NF"
      else
        echo "  MesloLGS NF recommended; font installation left user-controlled on Linux."
      fi
    fi

    if [[ -d "${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k" \
       || -d "$HOME/powerlevel10k" || -d "$HOME/.powerlevel10k" ]]; then
      echo "  ✓ Powerlevel10k"
    else
      echo "  Powerlevel10k recommended; prompt configuration remains user-owned."
    fi
    echo "  Terminal/font preferences remain untouched."
  fi

  echo
  echo "LOOK + FUTURE CRASH installed."
  echo "  future-crash  # launch the workstation"
  echo "  rst           # same launch, after exec zsh"
  echo "  fcr           # short Future Crash launcher"
  echo "  lk            # LOOK shell"
  echo "  lo            # LOOK Ollama"
  echo "  lk settings   # configure AI / hosts / access"
  echo "  lk comfy discover   # optional: find an older ComfyUI install/models"
  echo "  lk schedule         # persistent delayed/recurring LO jobs"
  echo "  lk shortcuts  # inspect optional shell shortcut collisions/policy"
  echo
  echo "  1. exec zsh"
  echo "  2. lk doctor"
  echo "  3. future-crash"
  echo
  echo "Reference: lk help"
fi


# User-owned man page: no sudo, and harmless if the source is absent.
LOOK_MAN_SRC="$ROOT/look/lk.1"
LOOK_MAN_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/man/man1"
if [[ -f "$LOOK_MAN_SRC" ]]; then
  run mkdir -p "$LOOK_MAN_DIR"
  run cp "$LOOK_MAN_SRC" "$LOOK_MAN_DIR/lk.1"
fi

