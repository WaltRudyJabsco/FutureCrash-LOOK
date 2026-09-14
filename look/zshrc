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

# Terminal ownership indicator. Uses standard OSC title escapes and stays out of
# the prompt itself, so unsupported terminals simply ignore it.
_look_owner_title() {
  printf '\e]0;%s\a' "$1"
}

_look_shell_title() {
  if [[ -n "${FUTURE_CRASH_SHELL:-}" ]]; then
    _look_owner_title "◌ FUTURE CRASH · SHELL · ${PWD:t}"
  else
    _look_owner_title "LOOK · ${PWD:t}"
  fi
}

# Small command glossary. Keep it short enough to actually be useful.
commands() {
  print -P '%F{cyan}%BLOOK SHELL%b%f  %F{244}filesystem + navigation%f'
  print ''
  print -P '%F{75}  lk%f       smart view          %F{75}lkl%f      details'
  print -P '%F{75}  lkd%f      directories         %F{75}lkf%f      files'
  print -P '%F{75}  lkt%f      tree                %F{75}lkr%f      recent'
  print -P '%F{75}  lkz%f      sizes               %F{75}zll WORD%f jump + look'
  print -P '%F{75}  cdl WORD%f jump + details      %F{75}fznv%f     fuzzy edit'
  print -P '%F{75}  f%f        find anywhere → LOOK'

  _look_shortcut_is_look l  && print -P '%F{75}  l%f        look around'
  _look_shortcut_is_look lh && print -P '%F{75}  lh%f       LOOK home'
  _look_shortcut_is_look lo && print -P '%F{75}  lo%f       ask LO'
  _look_shortcut_is_look fc && print -P '%F{75}  fc%f       Future Crash'
  print -P '%F{75}  lk home%f  LOOK home           %F{75}lk o%f     ask LO'
  print -P '%F{75}  fcr%f      Future Crash        %F{75}rst%f      Future Crash'
  print -P '%F{75}  rs%f       reset ritual        %F{75}rb%f       reload zsh'
  print -P '%F{75}  lmk%f      smart make · file or dir'
  print ''
  print -P "%F{244}shortcut policy: ${_LOOK_SHORTCUT_POLICY}%f"
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


# Keep Unix cd deterministic. Zoxide stays available as `z` for fuzzy/history
# navigation, but must never intercept a new exact path that is not in its DB.
# `nocorrect` also prevents Zsh from suggesting an older similarly named folder
# before entering a freshly downloaded/extracted directory.
alias cd='nocorrect builtin cd'
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
  _look_owner_title "● LOOK"
  "$LOOK" "$@"
  local rc=$?
  _look_shell_title

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

# Human-facing smart-view implementation. Public short names are installed
# later through the collision-aware shortcut layer.
_look_smart() {
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

# Collision-resistant LOOK namespace. These are ours and are always installed.
lkl() { _look_view detail "$@"; }
lkd() { _look_view dirs "$@"; }
lkf() { _look_view files "$@"; }
lkt() { _look_view tree "$@"; }
lkr() { _look_view recent "$@"; }
lkz() { _look_view size "$@"; }

# Ultra-short muscle-memory layer. LOOK is deliberately a guest in the user's
# shell: by default a pre-existing alias/function/builtin/executable wins.
# `lk shortcuts force` opts into replacing aliases/functions and a tiny explicit
# allowlist of shell builtins whose replacement is intentional (currently `fc`).
# Real executables remain protected.
_LOOK_SHORTCUT_POLICY_FILE="$HOME/.local/share/look/shortcut_policy"
_LOOK_SHORTCUT_POLICY="polite"
[[ -r "$_LOOK_SHORTCUT_POLICY_FILE" ]] && _LOOK_SHORTCUT_POLICY="$(<"$_LOOK_SHORTCUT_POLICY_FILE")"

_look_short_name_kind() {
  local name="$1"
  (( $+builtins[$name] )) && { print builtin; return; }
  (( $+commands[$name] )) && { print executable; return; }
  (( $+aliases[$name] )) && { print alias; return; }
  (( $+functions[$name] )) && { print function; return; }
  print free
}

_look_short_install() {
  local name="$1" target="$2" kind
  kind="$(_look_short_name_kind "$name")"
  case "$kind" in
    executable)
      return 1
      ;;
    builtin)
      [[ "$_LOOK_SHORTCUT_POLICY" == "force" && "$name" == "fc" ]] || return 1
      disable "$name" 2>/dev/null || return 1
      ;;
    alias|function)
      [[ "$_LOOK_SHORTCUT_POLICY" == "force" ]] || return 1
      unalias "$name" 2>/dev/null
      unfunction "$name" 2>/dev/null
      ;;
  esac
  eval "${name}() { ${target} \"\$@\"; }"
}

_look_short_install l _look_smart
_look_short_install ll lkl
_look_short_install ld lkd
_look_short_install lf lkf
_look_short_install lt lkt
_look_short_install lr lkr
_look_short_install lz lkz
_look_short_install lh '_look home'
_look_short_install fc fcr

# Historical LOOK aliases are intentionally no longer installed: lsd collides
# with the established lsd utility, and lc/lsf add little beyond lk*/lk commands.

# `ls` is canonical Unix territory; LOOK never shadows it. Use `lk`, `lkl`, or optional `l`.

# Zoxide jump + immediate orientation. These are worth keeping exactly.
zll() {
  z "$@" || return
  _look_smart
}

cdl() {
  z "$@" || return
  lkl
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

# Shared streaming global finder.
# fd/find begins producing paths immediately; fzf is interactive before the
# catalog is complete, so typing never waits on a full-home scan.
_look_global_pick() {
  local prompt="${1:-FIND › }"

  if (( $+commands[fd] )); then
    fd --hidden --follow --absolute-path \
      --exclude .git --exclude node_modules --exclude .Trash \
      --exclude Library/Caches --exclude .cache \
      . "$HOME" 2>/dev/null |
    fzf \
      --prompt="$prompt" \
      --height=100% \
      --layout=reverse \
      --info=inline \
      --border=none \
      --pointer='▸' \
      --marker='✓' \
      --color='fg:#d7dde5,bg:#0f141a,hl:#67d6ee,fg+:#081218,bg+:#48bcd6,hl+:#081218,prompt:#67d6ee,pointer:#67d6ee,marker:#8bd691,spinner:#67d6ee,info:#808b9a'
    return ${pipestatus[2]}
  fi

  command find "$HOME" \
    \( -path "$HOME/.git" -o -path '*/.git' -o -path '*/node_modules' \
       -o -path "$HOME/.Trash" -o -path "$HOME/Library/Caches" -o -path "$HOME/.cache" \) -prune -o \
    -mindepth 1 -print 2>/dev/null |
  fzf \
    --prompt="$prompt" \
    --height=100% \
    --layout=reverse \
    --info=inline \
    --border=none \
    --pointer='▸' \
    --marker='✓' \
    --color='fg:#d7dde5,bg:#0f141a,hl:#67d6ee,fg+:#081218,bg+:#48bcd6,hl+:#081218,prompt:#67d6ee,pointer:#67d6ee,marker:#8bd691,spinner:#67d6ee,info:#808b9a'
  return ${pipestatus[2]}
}

fznv() {
  (( $+commands[nvim] )) || return 127
  local selection
  selection=$(_look_global_pick 'FIND+NVIM › ') || return
  [[ -n "$selection" ]] || return
  _look_nvim_intro
  nvim -- "$selection"
}

# Global retrieval stays streaming, then hands the exact result to LOOK.
f() {
  local selection
  selection=$(_look_global_pick 'FIND › ') || return
  [[ -n "$selection" ]] || return

  # LOOK owns the post-selection action language and preview.
  _look "${selection:h}" --mode smart --interactive --select "$selection"
}


# ── LOOK file actions ───────────────────────────────────────────────────────
# One-line LOOK prompt with a real bare-Esc cancel.
# Zsh's normal `read` treats Esc as line-editor input, which is wrong for actions.
_look_prompt() {
  local prompt="$1"
  REPLY=""

  # Dedicated ZLE keymap: normal shell completion, but bare Escape always means
  # "cancel this LOOK action" rather than becoming an unfinished editor prefix.
  if [[ -o interactive ]] && (( $+widgets[complete-word] )); then
    bindkey -N look-prompt emacs
    bindkey -M look-prompt '^I' expand-or-complete
    bindkey -M look-prompt '^[' send-break
    if vared -M look-prompt -p "$prompt" REPLY; then
      bindkey -D look-prompt
      return 0
    fi
    local rc=$?
    bindkey -D look-prompt
    REPLY=""
    return 130
  fi

  # Fallback for unusual/non-ZLE shells.
  local ch value=""
  print -n -- "$prompt"
  while true; do
    IFS= read -rsk1 ch || { print; return 1; }
    case "$ch" in
      $'\e') print; return 130 ;;
      $'\r'|$'\n') print; REPLY="$value"; return 0 ;;
      $'\177'|$'\b')
        if [[ -n "$value" ]]; then
          value="${value[1,-2]}"
          print -n $'\b \b'
        fi
        ;;
      *) value+="$ch"; print -n -- "$ch" ;;
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
  local -a sources
  if (( $# >= 2 )); then
    sources=("$@")
    dest="${sources[-1]}"
    sources[-1]=()
    if (( ${#sources[@]} == 1 )); then
      lk _move "${sources[1]}" "$dest"
    else
      lk _batch move "$dest" "${sources[@]}"
    fi
    return
  fi
  src=$(_look_source "$@") || return
  print -P "%F{cyan}MOVE%f  $src"
  _look_prompt "to › " || { print -P "%F{242}· cancelled%f"; return 1; }
  dest="$REPLY"
  [[ -n "$dest" ]] || return
  lk _move "$src" "$dest"
}

lcp() {
  local src dest
  local -a sources
  if (( $# >= 2 )); then
    sources=("$@")
    dest="${sources[-1]}"
    sources[-1]=()
    if (( ${#sources[@]} == 1 )); then
      lk _copy "${sources[1]}" "$dest"
    else
      lk _batch copy "$dest" "${sources[@]}"
    fi
    return
  fi
  src=$(_look_source "$@") || return
  print -P "%F{cyan}COPY%f  $src"
  _look_prompt "to [here] › " || { print -P "%F{242}· cancelled%f"; return 1; }
  dest="$REPLY"
  [[ -n "$dest" ]] || dest="."
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
  local -a sources
  if (( $# > 1 )); then
    sources=("$@")
    print -P "%F{red}REMOVE%f  ${#sources[@]} items"
    _look_prompt "remove these paths? [r confirms · Enter/Esc cancels] › " || {
      print -P "%F{242}· cancelled%f"; return 1
    }
    answer="$REPLY"
    [[ "${answer:l}" == "r" ]] || { print -P "%F{242}· cancelled%f"; return 1; }
    lk _batch remove -- "${sources[@]}"
    return
  fi
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

# File-action helpers intentionally accept several path operands. Let Zsh do
# ordinary filesystem completion for every position; lcp/lmv interpret the
# final operand as the destination when multiple operands are supplied.
# Every operand in LOOK file-action helpers is a filesystem path.
# Use Zsh's native path completer repeatedly, including after each space.
compdef _files lcp lmv lrm lscp


# Living AI broker — resident local coordinator. Silent, cheap, and optional.
# It owns background memory/skill/job scheduling; the durable queues remain on disk.
_look_ai_boot() {
  local cli="$HOME/.local/bin/lk"
  [[ -x "$cli" ]] || return 0
  # Let lk perform the real socket/PID health check; background it so shell
  # startup never waits on broker startup or stale-socket recovery.
  "$cli" ai start >/dev/null 2>&1 &!
}
_look_ai_boot

# Surface completed background LO work at the next normal shell prompt.
autoload -Uz add-zsh-hook
_look_lo_events_precmd() {
  local event_dir="$HOME/.local/share/look/events"
  if [[ -d "$event_dir" ]] && [[ -n "$(command find "$event_dir" -type f -maxdepth 1 -name '*.json' -print -quit 2>/dev/null)" ]]; then
    "$HOME/.local/bin/lk" events --drain
  fi
}
add-zsh-hook precmd _look_lo_events_precmd
add-zsh-hook precmd _look_shell_title

# LOOK unified command.
# A shell being reloaded may already contain aliases from an older LOOK release.
# Zsh expands aliases while sourcing, so clear all names that become functions
# BEFORE their function definitions are parsed.
unalias lk lo rst fcr future-crash commands 2>/dev/null
unfunction future-crash fcr rst 2>/dev/null
# `fc` remains Zsh's history builtin by default. The explicit `force` shortcut
# policy may disable/reclaim it later as the Future Crash convenience command.

alias lk='nocorrect lk'
commands() { "$HOME/.local/bin/lk" commands; }

# LOOK Ollama — minimal on-demand chat; a resident model is reused when available.
lo() {
  _look_owner_title "● LO"
  noglob "$HOME/.local/bin/lk" o "$@"
  local rc=$?
  _look_shell_title
  return $rc
}
# Natural-language arguments must never be subjected to Zsh spelling correction.
# Alias recursion is suppressed by Zsh, so the inner `lo` resolves to the function.
alias lo='nocorrect lo'

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
# All entry points mean the same thing:
#   outside Future Crash → launch it
#   inside Future Crash's escaped shell → return to the existing parent session
_future_crash_owned() {
  if [[ -n "${FUTURE_CRASH_SHELL:-}" ]]; then
    # This shell was spawned by Future Crash. Exiting it is the cleanest possible
    # "return" signal: the parent Future Crash resumes without recursion.
    exit 0
  fi

  _look_owner_title "● FUTURE CRASH"
  command future-crash "$@"
  local rc=$?
  _look_shell_title
  return $rc
}

# Canonical and convenience spellings intentionally share one semantic action.
future-crash() { _future_crash_owned "$@"; }
rst()          { _future_crash_owned "$@"; }
fcr()          { _future_crash_owned "$@"; }

_look_shortcut_is_look() {
  local name="$1"
  case "$name" in
    l|ll|ld|lf|lt|lr|lz|lh|fc)
      (( $+functions[$name] )) || return 1
      ;;
    lo)
      (( $+functions[lo] )) || return 1
      ;;
    lk)
      (( $+aliases[lk] || $+commands[lk] )) || return 1
      ;;
    *)
      return 1
      ;;
  esac
  return 0
}

_look_export_shortcut_state() {
  local names=(l ll ld lf lt lr lz lh lo lk fc)
  local active=() missing=() name kind
  for name in $names; do
    if _look_shortcut_is_look "$name"; then
      active+=("$name")
    else
      kind="$(_look_short_name_kind "$name")"
      missing+=("${name}:${kind}")
    fi
  done
  export LOOK_ACTIVE_SHORTCUTS="${(j:,:)active}"
  export LOOK_INACTIVE_SHORTCUTS="${(j:,:)missing}"
  export LOOK_SHORTCUT_POLICY="$_LOOK_SHORTCUT_POLICY"
}
_look_export_shortcut_state

