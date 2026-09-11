# ─────────────────────────────────────────────────────────────────────────────
# LOOK + Future Crash — terminal environment shell integration.
# ─────────────────────────────────────────────────────────────────────────────

# Powerlevel10k instant prompt: keep near the top.
export PATH="$HOME/.local/bin:$PATH"
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# Homebrew: Apple Silicon, Intel Mac, or Linuxbrew.
if (( $+commands[brew] )); then
  eval "$(brew shellenv)"
elif [[ -x /opt/homebrew/bin/brew ]]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
elif [[ -x /usr/local/bin/brew ]]; then
  eval "$(/usr/local/bin/brew shellenv)"
elif [[ -x /home/linuxbrew/.linuxbrew/bin/brew ]]; then
  eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
fi

# Prefer Homebrew Ruby without hard-coding a Ruby ABI such as 3.4.0.
if (( $+commands[brew] )) && brew --prefix ruby &>/dev/null; then
  path=("$(brew --prefix ruby)/bin" $path)
fi

# Optional Node 18 if installed through Homebrew.
if (( $+commands[brew] )) && brew --prefix node@18 &>/dev/null; then
  path=("$(brew --prefix node@18)/bin" $path)
fi

# Secrets never belong in this file.
[[ -r "$HOME/.zsh_secrets" ]] && source "$HOME/.zsh_secrets"

export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="powerlevel10k/powerlevel10k"
ENABLE_CORRECTION="true"
plugins=(git zsh-syntax-highlighting zsh-autosuggestions web-search)
source "$ZSH/oh-my-zsh.sh"

# ── Navigation ────────────────────────────────────────────────────────────────
if (( $+commands[zoxide] )); then
  eval "$(zoxide init zsh)"
fi

alias rb='exec zsh'
alias c='clear'
alias neo='neofetch'
# Small command glossary. Keep it short enough to actually be useful.
commands() {
  print -P '%F{cyan}%BLOOK SHELL%b%f  %F{244}filesystem + navigation%f'
  print ''
  print -P '%F{75}  l / ls%f   smart view          %F{75}ll%f       details'
  print -P '%F{75}  ld%f       directories         %F{75}lf%f       files'
  print -P '%F{75}  lt%f       tree                %F{75}lr%f       recent'
  print -P '%F{75}  lz%f       sizes               %F{75}zll WORD%f jump + look'
  print -P '%F{75}  cdl WORD%f jump + details      %F{75}fznv%f     fuzzy edit'
  print -P '%F{75}  f%f        find anywhere → LOOK'
  print -P '%F{75}  lh%f       LOOK home           %F{75}lo%f       Ollama chat'
  print -P '%F{75}  rst%f      Future Crash        %F{75}fc%f       Future Crash'
  print -P '%F{75}  lo ASK%f   ask immediately     %F{75}rs%f       reset ritual'
  print -P '%F{75}  rb%f       reload zsh          %F{75}lmk%f      smart make · file or dir'
  print ''
  print -P '%F{244}Inside a long LOOK view: Space page · b back · ↑↓/jk row · g/G ends · q quit%f'
  print -P '%F{244}Real Unix ls is always available as: command ls%f'
}

rs() {
  c
  (( $+commands[neofetch] )) && neo
  if (( $+commands[fortune] && $+commands[cowsay] )); then
    fortune | cowsay -r
  fi
  print -P '%F{244}commands  →  quick shell glossary%f'
}


# These two are intentionally yours. They make interactive navigation wonderful.
alias cd='z'
alias ..='cd ..'
alias zz='z -'

# ── LOOK: dynamic filesystem renderer ────────────────────────────────────────
# Install helper at ~/.local/bin/look.py. It never pipes rendered output through
# less/colorls; it owns terminal layout and paging itself.
LOOK="$HOME/.local/bin/lk"

_look() {
  if [[ ! -x "$LOOK" ]]; then
    print -P "%F{red}LOOK helper missing:%f $LOOK"
    print "Install look.py into ~/.local/bin/look.py and chmod +x it."
    return 127
  fi

  local cd_request="$HOME/.local/share/look/cd_request"
  command rm -f -- "$cd_request"
  "$LOOK" "$@"
  local rc=$?

  # Renderer subprocesses cannot change the parent shell directory. G writes
  # one deliberate handoff; the shell consumes it immediately and deletes it.
  if [[ -r "$cd_request" ]]; then
    local target
    target="$(<"$cd_request")"
    command rm -f -- "$cd_request"
    if [[ -n "$target" && -d "$target" ]]; then
      builtin cd -- "$target" || return
    fi
  fi
  return $rc
}

# Oh My Zsh may own some of these names; clear them before function parsing.
# (This line must stay before the function definitions.)
unalias ls l ll ld lf lt lr lz lsd lsf lc 2>/dev/null

# Human-facing filesystem vocabulary.
l() {
  if (( $# == 0 )); then
    _look . --mode smart --interactive
    return
  fi

  # `l WORD` means navigate there, then LOOK. Explicit directories win;
  # otherwise let zoxide resolve previously visited shorthand.
  if (( $# == 1 )) && [[ -d "$1" ]]; then
    builtin cd -- "$1" || return
    _look . --mode smart --interactive
    return
  fi

  local target
  target="$(zoxide query -- "$@" 2>/dev/null)" || {
    print -P "%F{red}LOOK:%f no directory match for $*"
    return 1
  }
  builtin cd -- "$target" || return
  _look . --mode smart --interactive
}
# Specialized LOOK views use the same directory language as `l`:
# explicit path first, otherwise resolve shorthand through zoxide.
_look_view() {
  local mode="$1"
  shift

  local target="."
  if (( $# > 0 )); then
    if (( $# == 1 )) && [[ -d "$1" ]]; then
      target="$1"
    else
      target="$(zoxide query -- "$@" 2>/dev/null)" || {
        print -P "%F{red}LOOK:%f no directory match for $*"
        return 1
      }
    fi
  fi

  if [[ "$mode" == "tree" ]]; then
    _look "$target" --mode tree --depth 3 --interactive
  else
    _look "$target" --mode "$mode" --interactive
  fi
}

ll()  { _look_view detail "$@"; }
ld()  { _look_view dirs "$@"; }
lf()  { _look_view files "$@"; }
lt()  { _look_view tree "$@"; }
lr()  { _look_view recent "$@"; }
lz()  { _look_view size "$@"; }
lh()  { _look home; }

# Keep your old names too: muscle memory is an API.
lsd() { ld "$@"; }
lsf() { lf "$@"; }
lc()  { ll "$@"; }

# Your original idea survives: normal interactive `ls` means smart LOOK.
# `command ls` always reaches the real Unix command when you need it.
ls() {
  if (( $# == 0 )); then
    lk
  else
    command ls "$@"
  fi
}

# Zoxide jump + immediate orientation. These are worth keeping exactly.
zll() {
  z "$@" || return
  l
}

cdl() {
  z "$@" || return
  ll
}

# Neovim's most famous usability bug is not knowing how to leave it.
# LOOK teaches the escape hatch once, then never interrupts again.
_look_nvim_intro() {
  local flag="$HOME/.local/share/look/nvim_intro"
  [[ -e "$flag" ]] && return
  print ''
  print -P '%F{cyan}%BLOOK is opening Neovim.%b%f'
  print 'To leave: Esc  :q  Enter'
  print "You'll only be told this once."
  print ''
  mkdir -p -- "${flag:h}"
  : >| "$flag"
}

# ── Fuzzy files ──────────────────────────────────────────────────────────────
displayFZFFiles() {
  fzf --preview 'bat --theme=gruvbox-dark --color=always --style=header,grid --line-range :400 -- {}'
}

fznv() {
  (( $+commands[nvim] )) || return 127
  local selection
  selection=$(displayFZFFiles) || return
  if [[ -n "$selection" ]]; then
    _look_nvim_intro
    nvim -- "$selection"
  fi
}

# Global retrieval: find from anywhere, then hand the result to LOOK.
# fd is preferred because it is fast and respects the usual project junk;
# find is the portable fallback.
f() {
  local selection
  if (( $+commands[fd] )); then
    selection=$(
      fd --hidden --follow --absolute-path \
        --exclude .git --exclude node_modules --exclude .Trash \
        --exclude Library/Caches --exclude .cache \
        . "$HOME" 2>/dev/null |
      fzf --prompt='FIND › ' --height=100% --layout=reverse
    ) || return
  else
    selection=$(
      command find "$HOME" \
        \( -path "$HOME/.git" -o -path '*/.git' -o -path '*/node_modules' -o -path "$HOME/.Trash" -o -path "$HOME/Library/Caches" -o -path "$HOME/.cache" \) -prune -o \
        -mindepth 1 -print 2>/dev/null |
      fzf --prompt='FIND › ' --height=100% --layout=reverse
    ) || return
  fi

  [[ -n "$selection" ]] || return

  # Hand the exact result to LOOK's existing object-action language.
  # Opening its parent lets both files and folders arrive already selected.
  _look "${selection:h}" --mode smart --interactive --select "$selection"
}


# ── LOOK file actions ───────────────────────────────────────────────────────
# One-line LOOK prompt with a real bare-Esc cancel.
# Zsh's normal `read` treats Esc as line-editor input, which is wrong for actions.
_look_prompt() {
  local prompt="$1" ch value=""
  REPLY=""
  print -n -- "$prompt"

  while true; do
    # -s keeps the terminal from echoing the key; LOOK owns the display.
    IFS= read -rsk1 ch || { print; return 1; }
    case "$ch" in
      $'\e')
        print
        return 130
        ;;
      $'\r'|$'\n')
        print
        REPLY="$value"
        return 0
        ;;
      $'\177'|$'\b')
        if [[ -n "$value" ]]; then
          value="${value[1,-2]}"
          print -n $'\b \b'
        fi
        ;;
      *)
        value+="$ch"
        print -n -- "$ch"
        ;;
    esac
  done
}

# Immediate one-key choice for LOOK action prompts.
_look_choice() {
  local prompt="$1" ch
  REPLY=""
  print -n -- "$prompt"
  IFS= read -rsk1 ch || { print; return 1; }
  print
  case "$ch" in
    $'\e') return 130 ;;
    *) REPLY="${ch:l}"; return 0 ;;
  esac
}

# Mutation stays explicit: LOOK selects/frames the intent, Unix does the work.
_look_pick_path() {
  local picked
  picked=$(find . -mindepth 1 -maxdepth 1 -print 2>/dev/null | sed 's#^\./##' | fzf --prompt='LOOK › ') || return
  [[ -n "$picked" ]] && print -r -- "$picked"
}

_look_source() {
  if (( $# )); then
    print -r -- "$1"
  else
    _look_pick_path
  fi
}

lmv() {
  local src dest
  if (( $# >= 2 )); then
    src="$1"; dest="$2"
  else
    src=$(_look_source "$@") || return
    print -P "%F{cyan}MOVE%f  $src"
    _look_prompt "to › " || { print -P "%F{242}· cancelled%f"; return 1; }
    dest="$REPLY"
    [[ -n "$dest" ]] || return
  fi
  lk _move "$src" "$dest"
}

lcp() {
  local src dest
  if (( $# >= 2 )); then
    src="$1"; dest="$2"
  else
    src=$(_look_source "$@") || return
    print -P "%F{cyan}COPY%f  $src"
    _look_prompt "to [here] › " || { print -P "%F{242}· cancelled%f"; return 1; }
    dest="$REPLY"
    [[ -n "$dest" ]] || dest="."
  fi
  lk _copy "$src" "$dest"
}

lscp() {
  local src dest
  if (( $# >= 2 )); then
    src="$1"; dest="$2"
  else
    src=$(_look_source "$@") || return
    print -P "%F{cyan}SEND%f  $src"
    _look_prompt "to (host:path) › " || { print -P "%F{242}· cancelled%f"; return 1; }
    dest="$REPLY"
    [[ -n "$dest" ]] || return
  fi
  if [[ -d "$src" ]]; then
    command scp -r -- "$src" "$dest"
  else
    command scp -- "$src" "$dest"
  fi
}

lmk() {
  local force="" dest answer result parent

  if [[ "$1" == "-d" || "$1" == "--dir" ]]; then
    force="dir"; shift
  elif [[ "$1" == "-f" || "$1" == "--file" ]]; then
    force="file"; shift
  fi

  dest="$*"
  if [[ -z "$dest" ]]; then
    _look_prompt "make › " || { print -P "%F{242}· cancelled%f"; return 1; }
    dest="$REPLY"
  fi
  [[ -n "$dest" ]] || return

  # Existing paths are not an intent question; report the filesystem fact first.
  if [[ -e "$dest" ]]; then
    if [[ -d "$dest" ]]; then
      print "LOOK make · already exists as a directory: $dest"
    else
      print "LOOK make · already exists as a file: $dest"
    fi
    return 1
  fi

  # A trailing slash is native Unix directory intent.
  if [[ "$force" == "dir" || "$dest" == */ ]]; then
    dest="${dest%/}"
    [[ -n "$dest" ]] || { print "LOOK make · invalid directory"; return 2; }
    lk _mkdir "$dest" || return
    [[ -d "$dest" ]] || { print "LOOK make · directory was not created: $dest"; return 1; }
    builtin cd -- "$dest"
    return
  fi

  if [[ "$force" != "file" ]]; then
    local leaf="${dest:t}"
    # Dotfiles and names with a suffix are strong file intent.
    if [[ "$leaf" != .* && "$leaf" != *.* ]]; then
      print -P "%F{cyan}LOOK make%f · %B$dest%b is ambiguous"
      _look_choice "[d] directory + enter · [f] file · Esc cancel › " || {
        print -P "%F{242}· cancelled%f"; return 1
      }
      answer="$REPLY"
      case "$answer" in
        d|dir|directory)
          lk _mkdir "$dest" || return
          [[ -d "$dest" ]] || { print "LOOK make · directory was not created: $dest"; return 1; }
          builtin cd -- "$dest"
          return
          ;;
        f|file) ;;
        *) print -P "%F{242}· cancelled%f"; return 1 ;;
      esac
    fi
  fi

  # File intent. If parents are missing, ask before creating them.
  result="$(lk _touch "$dest")"
  if [[ "$result" == CREATE_DIR_REQUIRED* ]]; then
    parent="${dest:h}"
    print -P "%F{cyan}LOOK make%f · parent directory does not exist: %B$parent%b"
    _look_choice "create parent path? [y/n] › " || { print -P "%F{242}· cancelled%f"; return 1; }
    answer="$REPLY"
    if [[ "$answer" == y ]]; then
      result="$(lk _touch --parents "$dest")"
    else
      print -P "%F{242}· cancelled%f"; return 1
    fi
  fi
  print -r -- "$result"
}

mkd() {
  [[ $# -ge 1 ]] || { print "usage: mkd <directory>"; return 2; }
  lmk -d "$@"
}

lrm() {
  local src answer
  src=$(_look_source "$@") || return
  print -P "%F{red}REMOVE%f  $src"
  _look_prompt "remove this path? [r/Enter/Esc cancels] › " || {
    print -P "%F{242}· cancelled%f"; return 1
  }
  answer="$REPLY"
  [[ "${answer:l}" == "r" ]] || { print -P "%F{242}· cancelled%f"; return 1; }
  lk _remove "$src"
}

# ── Personal tools / projects ────────────────────────────────────────────────
alias trackflight='flightProgress'
[[ "$OSTYPE" == darwin* ]] && alias love='/Applications/love.app/Contents/MacOS/love'

flightProgress() {
  while true; do
    ./flight.sh "$1" "$2" | ./parse_flight_progress.sh
    sleep 60
  done
}

# Optional helpers should never break shell startup.
(( $+commands[thefuck] )) && eval "$(thefuck --alias)"
[[ -f ~/.fzf.zsh ]] && source ~/.fzf.zsh
[[ -f ~/.p10k.zsh ]] && source ~/.p10k.zsh


# LOOK context-sensitive completion.
fpath=("$HOME/.config/look/completions" $fpath)
autoload -Uz compinit
(( $+functions[compdef] )) || compinit -i
autoload -Uz _lk _lo _lmk
compdef _lk lk
# lo is a noglob alias; COMPLETE_ALIASES lets its own grammar complete before expansion.
setopt COMPLETE_ALIASES
compdef _lo lo
compdef _lmk lmk mkd

# LOOK unified command
alias lk='nocorrect lk'
commands() { "$HOME/.local/bin/lk" help; }

# LOOK Ollama — minimal on-demand chat; a resident model is reused when available.
alias lo='noglob lk o'

# Fast media transport
alias mm='lk media toggle'
alias mn='lk media next'
alias mp='lk media prev'

webterm() {
  (( $+commands[ttyd] )) || { print "LOOK: webterm needs ttyd. Re-run the LOOK installer."; return 127; }
  (( $+commands[tailscale] )) || { print "LOOK: webterm needs Tailscale. Re-run ./install.sh or install Tailscale."; return 127; }
  (( $+commands[lsof] )) || { print "LOOK: webterm needs lsof. Re-run the LOOK installer."; return 127; }

  if ! lsof -iTCP:7681 -sTCP:LISTEN >/dev/null 2>&1; then
    ttyd -W zsh >/tmp/ttyd.log 2>&1 &
  fi

  tailscale serve --https=8443 7681
}



# ── Future Crash ─────────────────────────────────────────────────────────────
alias rst='future-crash'
alias fc='future-crash'
