#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY=0
ASSUME_YES=0
NO_OPTIONAL=0
BREW_BOOTSTRAPPED=0
installed_packages=()
created_dirs=()
ZSH_BACKUP=""

usage() {
  cat <<'EOF'
LOOK + FUTURE CRASH — system installer

Usage:
  ./install.sh [--dry-run] [--yes] [--no-optional] [--uninstall]

  --dry-run      show what LOOK would do
  --yes          install offered Remote + AI components without prompting
  --no-optional  install without optional Remote + AI\n  --uninstall    remove LOOK + Future Crash
EOF
}

while (($#)); do
  case "$1" in
    --dry-run) DRY=1 ;;
    --yes|-y) ASSUME_YES=1 ;;
    --no-optional) NO_OPTIONAL=1 ;;
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

echo "LOOK + FUTURE CRASH — terminal environment installer"
echo "$(uname -s) · $(uname -m)"
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
core=(zsh python3 git zoxide fzf fd nvim bat fortune cowsay fastfetch chafa pdftotext ttyd lsof)
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
if ((!DRY)); then
  MEMORY="$HOME/.local/share/look/ollama_memory.json"
  if [[ ! -f "$MEMORY" ]]; then
    printf '{"long":"","recent":[]}\n' > "$MEMORY"
    chmod 600 "$MEMORY"
  fi
fi

run cp "$ROOT/look/lk" "$HOME/.local/share/look/lk"
run cp "$ROOT/look/look_renderer.py" "$HOME/.local/share/look/look_renderer.py"
run chmod +x "$HOME/.local/share/look/lk"
if ((!DRY)); then ln -sfn "$HOME/.local/share/look/lk" "$HOME/.local/bin/lk"; fi

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

  # Record only what this installer can prove it added. `lk uninstall` uses
  # this manifest so it never guesses that a pre-existing package belongs to LOOK.
  export LOOK_MANIFEST_PACKAGES="$(printf '%s\n' "${installed_packages[@]-}")"
  export LOOK_MANIFEST_DIRS="$(printf '%s\n' "${created_dirs[@]-}")"
  export LOOK_MANIFEST_ZSH_BACKUP="$ZSH_BACKUP"
  export LOOK_MANIFEST_BREW_BOOTSTRAPPED="$BREW_BOOTSTRAPPED"
  python3 - <<'PY'
import json, os
from pathlib import Path

state = Path.home()/".local/share/look"
state.mkdir(parents=True, exist_ok=True)
manifest = {
    "version": "future-crash-look-1.0.0",
    "packages": [x for x in os.environ.get("LOOK_MANIFEST_PACKAGES","").splitlines() if x],
    "created_dirs": [x for x in os.environ.get("LOOK_MANIFEST_DIRS","").splitlines() if x],
    "zsh_backup": os.environ.get("LOOK_MANIFEST_ZSH_BACKUP",""),
    "brew_bootstrapped": os.environ.get("LOOK_MANIFEST_BREW_BOOTSTRAPPED","0") == "1",
}
tmp = state/"install_manifest.json.tmp"
tmp.write_text(json.dumps(manifest, indent=2) + "\n")
tmp.chmod(0o600)
tmp.replace(state/"install_manifest.json")
PY

  FUTURE_DIR="$HOME/.local/share/future-crash"
  run mkdir -p "$FUTURE_DIR"
  run cp "$ROOT/future-crash/future_crash.py" "$FUTURE_DIR/future_crash.py"
  run cp "$ROOT/future-crash/future-crash" "$HOME/.local/bin/future-crash"
  run chmod +x "$HOME/.local/bin/future-crash"

  echo
  echo "LOOK + FUTURE CRASH installed."
  echo "  future-crash  # launch the workstation"
  echo "  rst           # same launch, after exec zsh"
  echo "  fc            # same launch, shorter"
  echo "  lk            # LOOK shell"
  echo "  lo            # LOOK Ollama"
  echo "  lk settings   # configure AI / hosts / access"
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
  mkdir -p "$LOOK_MAN_DIR"
  cp "$LOOK_MAN_SRC" "$LOOK_MAN_DIR/lk.1"
fi

