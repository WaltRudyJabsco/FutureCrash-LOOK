#!/usr/bin/env python3
"""
FUTURE CRASH // ZERO
One process. One model. One terminal. Zero dependencies.

Mac/Linux:
    python3 future_crash.py --model qwen3:4b
    python3 future_crash.py --model gemma3:4b
    python3 future_crash.py --model llama3.2:3b

Optional:
    --ollama http://127.0.0.1:11434
    --fps 12
    --no-ai-ambient

Controls:
    A   quick Ask
    X   Workstation conversation
    F   new fortune
    P   panic
    R   refresh observation
    Q   quit

The terminal is the idle state. The assistant is the machine underneath it.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import tempfile
import wave
import os
import queue
import random
import re
import select
import shlex
import shutil
import signal
import subprocess
import sys
import termios
import threading
import time
import tty
import urllib.error
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

ESC = "\x1b"
CSI = ESC + "["

# ---------- Palette ----------

RESET = CSI + "0m"
BOLD = CSI + "1m"
DIM = CSI + "2m"
GREEN = CSI + "38;5;121m"
GREEN2 = CSI + "38;5;78m"
CYAN = CSI + "38;5;117m"
AMBER = CSI + "38;5;221m"
MAGENTA = CSI + "38;5;213m"
RED = CSI + "38;5;203m"
WHITE = CSI + "38;5;255m"
GRAY = CSI + "38;5;245m"
DARK = CSI + "38;5;239m"

VERSION = "0.9.9"
GLYPHS = "0123456789ABCDEF"
SPARKS = "▁▂▃▄▅▆▇█"

FORTUNES = [
    "A sufficiently patient machine eventually becomes furniture.",
    "The difficult bug is currently pretending to be a design decision.",
    "Today is favorable for backups and unfavorable for assumptions.",
    "A small uncertainty has requested a much larger office.",
    "You will solve the problem shortly after blaming the wrong subsystem.",
    "The universe recommends saving your work before testing its sense of humor.",
    "A quiet terminal is only gathering material.",
    "Before debugging the universe, reproduce the universe.",
    "The shortest path between two bugs passes through a third bug.",
    "A warning ignored twice becomes interface decoration.",
    "Some doors open automatically; others require better error messages.",
    "Your next good idea is currently disguised as an inconvenience.",
    "The machine favors patience, backups, and clearly named variables.",
    "A mysterious result is often a familiar assumption wearing a hat.",
    "Today's impossible task has been downgraded to merely annoying.",
    "The future rewards those who save before experimenting.",
    "One elegant deletion is worth several clever additions.",
    "Beware the configuration file that describes its own replacement.",
    "A stable system is a temporary agreement among moving parts.",
    "The answer is nearby, but currently facing away.",
    "The universe has accepted your input without validating it.",
    "Good naming prevents minor hauntings.",
    "A problem measured becomes a problem with paperwork.",
    "The next reboot will remember nothing and imply otherwise.",
    "A process observed too closely may begin producing documentation.",
    "The bug you seek has already renamed itself.",
    "A careful backup is optimism with evidence.",
    "Never trust a progress bar that has learned confidence.",
    "You will soon discover why that value was hard-coded.",
    "An undocumented feature is merely a bug with tenure.",
    "Good tools disappear into the work. Great tools occasionally tell fortunes.",
    "A system can be deterministic and still hold a grudge.",
    "Today favors small functions and reversible decisions.",
    "A successful experiment is one that leaves useful wreckage.",
    "Your future self has requested clearer comments.",
    "A machine left running long enough will accumulate mythology.",
    "The path is valid. The destination has moved.",
    "One missing character currently controls the entire afternoon.",
    "An elegant interface is a treaty between complexity and impatience.",
    "A stale cache is yesterday insisting on voting.",
    "The machine recommends testing the boring explanation first.",
    "A good deletion leaves the remaining code standing straighter.",
    "The universe prefers reproducible bugs.",
    "A single named constant can prevent years of folklore.",
    "You are closer than the current output suggests.",
    "A small script can become a place if given enough personality.",
]


OBSERVATIONS = [
    "I have inspected the processes. Some of them know what they did.",
    "The universe remains stable enough for unsaved work.",
    "Nothing is wrong. Several things are merely interesting.",
    "I am not conspiring. I am preserving optionality.",
    "A clean terminal is a temporary victory over entropy.",
    "The blinking lights are largely ceremonial.",
    "There is no cloud. It is someone else's computer wearing weather.",
    "All systems nominal. Nominal has declined to comment.",
    "Today's operational doctrine: measure twice, blame DNS once.",
    "Your files remain where you left them, which is more than can be said for time.",
    "A reboot is a very short creation myth.",
    "A process has entered witness protection under a different PID.",
    "The machine is currently between opinions.",
    "One subsystem has requested a window. This remains a terminal.",
    "The load average is behaving like it has somewhere else to be.",
    "There are no ghosts in the machine, only undocumented residents.",
    "Maintenance reports the future is wearing unevenly.",
    "The cursor has resumed its tiny administrative duties.",
    "A packet crossed the room without making eye contact.",
    "Local reality is available on a best-effort basis.",
    "Several bits have formed a committee.",
    "No alarms are active. A few are merely rehearsing.",
    "Something was cached. Nobody remembers requesting it.",
    "The fan is translating heat into weather.",
    "A background task has achieved foreground anxiety.",
    "One old diagnostic has become folklore.",
    "No data was harmed, though several bytes were startled.",
    "Today's errors are unusually well dressed.",
    "The network remains a rumor with excellent cabling.",
    "The terminal is considering a second cup of electricity.",
    "The machine briefly understood everything and wisely discarded the cache.",
    "The future arrived early and is waiting in the lobby.",
    "Your computer contains multitudes, most of them daemons.",
    "A tiny rebellion in column forty-seven has been peacefully resolved.",
    "A service has been running so long it now considers itself infrastructure.",
    "One thread has wandered off to consider its options.",
    "Nothing has crashed. Something has merely chosen a lower-energy arrangement.",
    "The logs contain a complete account of events in no useful order.",
    "A minor contradiction has been promoted to system architecture.",
    "The CPU has completed several billion tiny errands.",
    "There is still plenty of disk space for future regrets.",
    "The terminal reports that darkness improves contrast.",
    "Several assumptions have reached end of life but remain in production.",
    "The scheduler is distributing time without regard for merit.",
    "A checksum has confirmed that something happened.",
    "The cursor remains the smallest employee with the largest office.",
    "The operating system remains mostly operating and recognizably a system.",
    "All major uncertainties have been assigned tracking numbers.",
    "Somewhere inside the system, a loop is enjoying the scenery.",
]


PANICS = [
    ("TEMPORAL CRC FAILURE", "Yesterday differs from archived copy."),
    ("UNSCHEDULED PHILOSOPHY", "Several daemons are asking why."),
    ("GRAVITY SERVICE RESTART", "Please remain near the floor."),
    ("FONT AUTHORITY CONFLICT", "Typography has escalated."),
    ("MATRIX POLARITY REVERSAL", "Decorative consequences expected."),
]

RARE_EVENTS = [
    ("REALITY CHECKSUM MISMATCH", "Recovered. Probably."),
    ("LOADING COMMON SENSE", "Package not found."),
    ("UNIVERSE UPDATE AVAILABLE", "Deferred until after coffee."),
    ("TIME TRAVEL DRIVER", "Already installed tomorrow."),
    ("WEATHER ENGINE", "Unavailable. Weather escaped."),
    ("CAUSALITY RECEIPT FOUND", "Filed under miscellaneous futures."),
    ("GRAVITY LATENCY", "Objects may arrive slightly downward."),
    ("EMERGENCY POETRY", "Suppressed before deployment."),
    ("CERTAINTY BUFFER", "Overflow prevented by doubt."),
    ("VACUUM PRESSURE", "Still impressively empty."),
    ("PROCESS ECLIPSE", "One daemon briefly obscured another."),
    ("DARK MATTER DELIVERY", "Package appears empty but weighs correctly."),
    ("THERMAL POETRY", "Heat sink expressing itself through free verse."),
    ("SECONDARY REALITY", "Running in compatibility mode."),
    ("ZERO SHORTAGE", "Additional zeroes ordered in bulk."),
]

INCIDENTS = [
    "screen_chew", "horizontal_tear", "signal_loss",
    "memory_leak_theater", "cursor_echo", "static_infiltration",
]

# ---------- Utilities ----------

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def visible_len(s: str) -> int:
    # Fast enough for our own ANSI palette.
    import re
    return len(re.sub(r"\x1b\[[0-9;]*m", "", s))

def fit(s: str, width: int) -> str:
    plain = strip_ansi(s)
    if len(plain) <= width:
        return s + " " * (width - len(plain))
    return plain[: max(0, width - 1)] + "…"

def strip_ansi(s: str) -> str:
    import re
    return re.sub(r"\x1b\[[0-9;]*m", "", s)

def safe_row(s: str, width: int) -> str:
    """Guarantee a physical row never reaches the terminal wrap column."""
    if visible_len(s) <= width:
        return s
    # For overlong rows, prefer stable geometry over preserving styling.
    return strip_ansi(s)[:width]

def wrap(text: str, width: int) -> list[str]:
    words = text.replace("\r", "").split()
    if not words:
        return [""]
    out, line = [], ""
    for word in words:
        candidate = word if not line else line + " " + word
        if len(candidate) <= width:
            line = candidate
        else:
            if line:
                out.append(line)
            if len(word) > width:
                while len(word) > width:
                    out.append(word[:width])
                    word = word[width:]
            line = word
    if line:
        out.append(line)
    return out

def spark(values, width=22):
    vals = list(values)[-width:]
    if not vals:
        vals = [0.0]
    if len(vals) < width:
        vals = [0.0] * (width - len(vals)) + vals
    return "".join(SPARKS[int(clamp(v, 0, .999) * len(SPARKS))] for v in vals)

def bytes_text(n):
    n = float(n)
    for unit in ("B", "K", "M", "G", "T"):
        if abs(n) < 1024:
            return f"{n:4.1f}{unit}"
        n /= 1024
    return f"{n:.1f}P"

def run(argv, timeout=1.5):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return p.stdout.strip()
    except Exception:
        return ""


# ---------- Audio ----------

class AudioEngine:
    """Tiny dependency-free sound chip using the host's native WAV player."""

    SAMPLE_RATE = 22050

    def __init__(self, enabled=True):
        self.player = shutil.which("afplay") if sys.platform == "darwin" else shutil.which("aplay")
        self.available = bool(self.player)
        self.enabled = bool(enabled and self.available)
        self.directory = Path(tempfile.mkdtemp(prefix="future_crash_audio_"))
        self.cache = {}

    @property
    def status(self):
        if not self.available:
            return "UNAVAILABLE"
        return "ON" if self.enabled else "MUTED"

    def set_enabled(self, enabled):
        self.enabled = bool(enabled and self.available)

    def _wav(self, name, notes):
        if name in self.cache:
            return self.cache[name]
        path = self.directory / (name + ".wav")
        samples = []
        for freq, duration, volume in notes:
            count = int(self.SAMPLE_RATE * duration)
            for i in range(count):
                t = i / self.SAMPLE_RATE
                env = min(1.0, i / 80.0, max(0.0, (count - i) / 100.0))
                raw = math.sin(2 * math.pi * freq * t) + .20 * math.sin(4 * math.pi * freq * t)
                samples.append(int(32767 * volume * env * max(-1, min(1, raw / 1.2))))
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(self.SAMPLE_RATE)
            wf.writeframes(b"".join(struct.pack("<h", s) for s in samples))
        self.cache[name] = path
        return path

    def cue(self, name):
        if not self.enabled:
            return
        patterns = {
            "ask": [(440,.05,.08),(660,.05,.08)],
            "oracle": [(760,.05,.08),(980,.07,.07)],
            "fortune": [(520,.04,.06),(650,.04,.06),(780,.05,.06)],
            "incident": [(180,.06,.08),(135,.07,.07)],
            "panic": [(220,.07,.11),(110,.10,.11),(330,.07,.09)],
            "recover": [(330,.05,.07),(495,.05,.07),(660,.07,.07)],
            "shell_out": [(620,.04,.07),(470,.05,.07),(310,.07,.08)],
            "shell_back": [(310,.04,.07),(470,.05,.07),(620,.07,.08)],
        }
        if name not in patterns:
            return
        try:
            path = self._wav(name, patterns[name])
            subprocess.Popen([self.player, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def wrap_menu(items, width):
    """Wrap footer commands by whole menu item; never clip a command label."""
    width = max(24, int(width))
    rows, current = [], ""
    for item in items:
        candidate = item if not current else current + "   " + item
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                rows.append(current)
            # An individual item should fit ordinary terminals; keep a safe fallback.
            current = item[:width]
    if current:
        rows.append(current)
    return rows

# ---------- Telemetry ----------

@dataclass
class Stats:
    cpu: float = 0.0
    mem: float = 0.0
    mem_used: int = 0
    mem_total: int = 1
    disk: float = 0.0
    disk_used: int = 0
    disk_total: int = 1
    load: float = 0.0
    uptime: float = 0.0
    net_rx: float = 0.0
    net_tx: float = 0.0
    cpu_hist: deque = field(default_factory=lambda: deque([0.0] * 48, maxlen=48))
    mem_hist: deque = field(default_factory=lambda: deque([0.0] * 48, maxlen=48))
    net_hist: deque = field(default_factory=lambda: deque([0.0] * 48, maxlen=48))

class Telemetry(threading.Thread):
    daemon = True

    def __init__(self):
        super().__init__()
        self.lock = threading.Lock()
        self.stats = Stats()
        self.stop = threading.Event()
        self.prev_cpu = None
        self.prev_net = None

    def snapshot(self):
        with self.lock:
            s = self.stats
            return Stats(
                s.cpu, s.mem, s.mem_used, s.mem_total,
                s.disk, s.disk_used, s.disk_total,
                s.load, s.uptime, s.net_rx, s.net_tx,
                deque(s.cpu_hist, maxlen=48),
                deque(s.mem_hist, maxlen=48),
                deque(s.net_hist, maxlen=48),
            )

    def run(self):
        while not self.stop.is_set():
            self.sample()
            self.stop.wait(1.0)

    def sample(self):
        cpu = self._cpu()
        used, total = self._memory()
        try:
            d = shutil.disk_usage(Path.home())
            d_used, d_total = d.used, d.total
        except Exception:
            d_used, d_total = 0, 1
        try:
            load = os.getloadavg()[0]
        except Exception:
            load = 0.0
        rx, tx = self._network()
        up = self._uptime()

        with self.lock:
            s = self.stats
            s.cpu = cpu
            s.mem_used, s.mem_total = used, max(1, total)
            s.mem = used / max(1, total)
            s.disk_used, s.disk_total = d_used, max(1, d_total)
            s.disk = d_used / max(1, d_total)
            s.load, s.uptime = load, up
            s.net_rx, s.net_tx = rx, tx
            s.cpu_hist.append(cpu)
            s.mem_hist.append(s.mem)
            s.net_hist.append(clamp((rx + tx) / 4_000_000, 0, 1))

    def _cpu(self):
        if sys.platform == "darwin":
            out = run(["top", "-l", "1", "-n", "0"], 2.0)
            for line in out.splitlines():
                if line.startswith("CPU usage:"):
                    try:
                        idle = float(line.split("idle")[0].split()[-1].rstrip("%"))
                        return clamp((100 - idle) / 100, 0, 1)
                    except Exception:
                        pass
            return 0.0

        try:
            vals = [int(x) for x in Path("/proc/stat").read_text().splitlines()[0].split()[1:]]
            idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
            total = sum(vals)
            value = 0.0
            if self.prev_cpu:
                old_idle, old_total = self.prev_cpu
                delta = total - old_total
                if delta:
                    value = 1 - ((idle - old_idle) / delta)
            self.prev_cpu = (idle, total)
            return clamp(value, 0, 1)
        except Exception:
            return 0.0

    def _memory(self):
        if sys.platform == "darwin":
            try:
                total = int(run(["sysctl", "-n", "hw.memsize"]))
                vm = run(["vm_stat"])
                page = 4096
                first = vm.splitlines()[0] if vm else ""
                if "page size of" in first:
                    page = int(first.split("page size of")[1].split()[0])
                vals = {}
                for line in vm.splitlines()[1:]:
                    if ":" in line:
                        k, v = line.split(":", 1)
                        try:
                            vals[k.strip()] = int(v.strip().rstrip("."))
                        except Exception:
                            pass
                free = (vals.get("Pages free", 0) + vals.get("Pages speculative", 0)) * page
                return max(0, total - free), total
            except Exception:
                return 0, 1

        try:
            data = {}
            for line in Path("/proc/meminfo").read_text().splitlines():
                k, v = line.split(":", 1)
                data[k] = int(v.strip().split()[0]) * 1024
            total = data.get("MemTotal", 1)
            return total - data.get("MemAvailable", 0), total
        except Exception:
            return 0, 1

    def _network(self):
        now = time.time()
        rx = tx = 0

        if sys.platform == "darwin":
            out = run(["netstat", "-ib"])
            seen = set()
            for line in out.splitlines()[1:]:
                p = line.split()
                if len(p) < 10:
                    continue
                iface = p[0]
                if iface.startswith("lo") or iface in seen:
                    continue
                # netstat column layouts differ; only trust numeric tail candidates.
                nums = []
                for token in p:
                    if token.isdigit():
                        nums.append(int(token))
                if len(nums) >= 2:
                    rx += nums[-2]
                    tx += nums[-1]
                    seen.add(iface)
        else:
            try:
                for line in Path("/proc/net/dev").read_text().splitlines()[2:]:
                    iface, rest = line.split(":", 1)
                    if iface.strip() == "lo":
                        continue
                    p = rest.split()
                    rx += int(p[0])
                    tx += int(p[8])
            except Exception:
                pass

        if self.prev_net:
            old_rx, old_tx, old_t = self.prev_net
            dt = max(.001, now - old_t)
            result = max(0, (rx - old_rx) / dt), max(0, (tx - old_tx) / dt)
        else:
            result = 0.0, 0.0
        self.prev_net = rx, tx, now
        return result

    def _uptime(self):
        if sys.platform == "darwin":
            raw = run(["sysctl", "-n", "kern.boottime"])
            try:
                boot = int(raw.split("sec =")[1].split(",")[0].strip())
                return max(0, time.time() - boot)
            except Exception:
                return 0
        try:
            return float(Path("/proc/uptime").read_text().split()[0])
        except Exception:
            return 0



# ---------- Configuration ----------

class ConfigStore:
    """Small persistent preferences store. Command-line flags still win."""

    def __init__(self):
        self.root = Path.home() / ".future_crash"
        self.path = self.root / "config.json"
        self.data = {"audio_enabled": True}
        self.load()

    def load(self):
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            if self.path.exists():
                incoming = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(incoming, dict):
                    self.data.update(incoming)
        except Exception:
            pass

    def save(self):
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
            tmp.replace(self.path)
        except Exception:
            pass

    @property
    def audio_enabled(self):
        return bool(self.data.get("audio_enabled", True))

    @audio_enabled.setter
    def audio_enabled(self, value):
        self.data["audio_enabled"] = bool(value)
        self.save()

# ---------- Memory ----------

class MemoryStore:
    """
    Six-slot memory:
      slot 0: rolling compressed long memory
      slots 1-5: recent completed Workstation exchanges

    Once five recent exchanges fill, Future Crash asks the SAME selected model
    to compress long memory + those five exchanges into a new long memory.
    """

    RECENT_CAPACITY = 5

    def __init__(self, path=None):
        self.path = Path(path or (Path.home() / ".future_crash_memory.json"))
        self.long_memory = ""
        self.recent = []
        self.pending_consolidation = False
        self.load()

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.long_memory = str(data.get("long_memory", "")).strip()
            recent = data.get("recent", [])
            if isinstance(recent, list):
                self.recent = [str(x).strip() for x in recent if str(x).strip()][-self.RECENT_CAPACITY:]
        except Exception:
            self.long_memory = ""
            self.recent = []

    def save(self):
        try:
            payload = {
                "version": 1,
                "long_memory": self.long_memory,
                "recent": self.recent[-self.RECENT_CAPACITY:],
            }
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.path)
        except Exception:
            pass

    def add_exchange(self, user_text, assistant_text):
        episode = f"USER: {user_text.strip()}\nORACLE: {assistant_text.strip()}"
        self.recent.append(episode[:5000])
        self.save()
        return len(self.recent) >= self.RECENT_CAPACITY

    def consolidation_prompt(self):
        recent_text = "\n\n--- RECENT MEMORY ---\n".join(self.recent[-self.RECENT_CAPACITY:])
        old = self.long_memory.strip() or "(none yet)"
        return (
            "Compress the memory below into a durable working memory for Future Crash. "
            "Preserve concrete facts, preferences, decisions, ongoing projects, unresolved questions, "
            "and important context. Remove chit-chat, repetition, and transient wording. "
            "Do not invent anything. Write at most 8 compact lines.\n\n"
            f"EXISTING LONG MEMORY:\n{old}\n\n"
            f"FIVE RECENT EXCHANGES:\n{recent_text}"
        )

    def finish_consolidation(self, compressed):
        compressed = (compressed or "").strip()
        if compressed:
            self.long_memory = compressed[:7000]
        else:
            # Deterministic fallback: keep a bounded plain-text digest rather than lose memory.
            joined = "\n".join(self.recent[-self.RECENT_CAPACITY:])
            self.long_memory = (self.long_memory + "\n" + joined)[-7000:].strip()
        self.recent = []
        self.pending_consolidation = False
        self.save()

    def context_packet(self):
        """Return memory as invisible background context, not numbered storage."""
        parts = []
        if self.long_memory:
            parts.append(self.long_memory)
        if self.recent:
            parts.extend(self.recent)
        if not parts:
            return ""
        return "\n\n".join(parts)

    def status(self):
        long_mark = "YES" if self.long_memory else "EMPTY"
        return f"LONG {long_mark} // RECENT {len(self.recent)}/{self.RECENT_CAPACITY}"


# ---------- Signal Canvas ----------

class SignalCanvas:
    """Validated 40x12 character framebuffer for model-generated sketches."""

    WIDTH = 40
    HEIGHT = 12
    DEFAULT_TTL = 45.0
    COLORS = {
        "green": GREEN, "cyan": CYAN, "amber": AMBER,
        "magenta": MAGENTA, "red": RED, "white": WHITE, "dim": DARK,
    }
    SIGNAL_RE = re.compile(r"\[\[SIGNAL\]\](.*?)\[\[/SIGNAL\]\]", re.S | re.I)

    def __init__(self):
        self.cells = [[None for _ in range(self.WIDTH)] for _ in range(self.HEIGHT)]
        self.expires_at = 0.0
        self.title = ""
        self.owner = None

    def clear(self):
        self.cells = [[None for _ in range(self.WIDTH)] for _ in range(self.HEIGHT)]
        self.expires_at = 0.0
        self.title = ""
        self.owner = None

    def clear_owner(self, owner):
        """Clear the canvas only when it belongs to the specified Thread."""
        if owner and self.owner == owner:
            self.clear()
            return True
        return False

    def active(self):
        if self.expires_at and time.time() >= self.expires_at:
            self.clear()
        return any(c is not None for row in self.cells for c in row)

    def _put(self, x, y, ch, color="cyan"):
        if 0 <= x < self.WIDTH and 0 <= y < self.HEIGHT:
            self.cells[y][x] = ((ch or " ")[:1], color if color in self.COLORS else "cyan")

    def _line(self, x0, y0, x1, y1, color, ch):
        dx, sx = abs(x1-x0), (1 if x0 < x1 else -1)
        dy, sy = -abs(y1-y0), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self._put(x0, y0, ch, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy; x0 += sx
            if e2 <= dx:
                err += dx; y0 += sy

    def _box(self, x, y, w, h, color, ch):
        if w <= 0 or h <= 0:
            return
        self._line(x, y, x+w-1, y, color, ch)
        self._line(x, y+h-1, x+w-1, y+h-1, color, ch)
        self._line(x, y, x, y+h-1, color, ch)
        self._line(x+w-1, y, x+w-1, y+h-1, color, ch)

    def _fill(self, x, y, w, h, color, ch):
        for yy in range(y, y + max(0, h)):
            for xx in range(x, x + max(0, w)):
                self._put(xx, yy, ch, color)

    def _text(self, x, y, color, value):
        for i, ch in enumerate(value):
            self._put(x+i, y, ch, color)

    def _circle(self, cx, cy, radius, color, ch):
        """Rasterize a circle in logical-cell coordinates."""
        radius = max(1, radius)
        # Terminal cells are taller than they are wide. Sampling x more densely
        # gives the model a circle that looks circular on an ordinary terminal.
        steps = max(24, radius * 18)
        for i in range(steps):
            a = (2.0 * math.pi * i) / steps
            x = int(round(cx + math.cos(a) * radius * 1.65))
            y = int(round(cy + math.sin(a) * radius))
            self._put(x, y, ch, color)

    def _ellipse(self, cx, cy, rx, ry, color, ch):
        rx, ry = max(1, rx), max(1, ry)
        steps = max(28, (rx + ry) * 10)
        for i in range(steps):
            a = (2.0 * math.pi * i) / steps
            x = int(round(cx + math.cos(a) * rx))
            y = int(round(cy + math.sin(a) * ry))
            self._put(x, y, ch, color)

    def _arrow(self, x0, y0, x1, y1, color, ch):
        self._line(x0, y0, x1, y1, color, ch)
        dx, dy = x1 - x0, y1 - y0
        # Simple terminal arrowhead. Host owns the geometry; the model only
        # chooses endpoints.
        if abs(dx) >= abs(dy):
            head = ">" if dx >= 0 else "<"
        else:
            head = "v" if dy >= 0 else "^"
        self._put(x1, y1, head, color)

    def _plot(self, values, color, ch):
        """Plot normalized 0..1 values across the whole logical canvas."""
        if not values:
            return
        count = len(values)
        prev = None
        for i, value in enumerate(values):
            value = max(0.0, min(1.0, float(value)))
            x = int(round(i * (self.WIDTH - 1) / max(1, count - 1)))
            y = int(round((1.0 - value) * (self.HEIGHT - 1)))
            if prev is not None:
                self._line(prev[0], prev[1], x, y, color, ch)
            self._put(x, y, ch, color)
            prev = (x, y)

    def parse_from_response(self, response, owner=None, persist=False):
        blocks = self.SIGNAL_RE.findall(response or "")
        clean = self.SIGNAL_RE.sub("", response or "").strip()
        if not blocks:
            return clean, False

        touched = False
        ttl = self.DEFAULT_TTL
        for block in blocks[-2:]:
            for raw in block.splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                cmd = parts[0].upper()
                try:
                    if cmd == "CLEAR":
                        self.clear(); touched = True
                    elif cmd == "TTL" and len(parts) >= 2:
                        ttl = max(5.0, min(180.0, float(parts[1])))
                    elif cmd == "TITLE" and len(parts) >= 2:
                        self.title = " ".join(parts[1:])[:28]; touched = True
                    elif cmd == "PUT" and len(parts) >= 5:
                        self._put(int(parts[1]), int(parts[2]), parts[4][0], parts[3].lower()); touched = True
                    elif cmd == "TEXT" and len(parts) >= 5:
                        self._text(int(parts[1]), int(parts[2]), parts[3].lower(), line.split(None,4)[4]); touched = True
                    elif cmd == "LINE" and len(parts) >= 7:
                        self._line(*map(int, parts[1:5]), parts[5].lower(), parts[6][0]); touched = True
                    elif cmd == "BOX" and len(parts) >= 7:
                        self._box(*map(int, parts[1:5]), parts[5].lower(), parts[6][0]); touched = True
                    elif cmd == "FILL" and len(parts) >= 7:
                        self._fill(*map(int, parts[1:5]), parts[5].lower(), parts[6][0]); touched = True
                    elif cmd == "CIRCLE" and len(parts) >= 6:
                        self._circle(int(parts[1]), int(parts[2]), int(parts[3]), parts[4].lower(), parts[5][0]); touched = True
                    elif cmd == "ELLIPSE" and len(parts) >= 7:
                        self._ellipse(int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]), parts[5].lower(), parts[6][0]); touched = True
                    elif cmd == "ARROW" and len(parts) >= 7:
                        self._arrow(*map(int, parts[1:5]), parts[5].lower(), parts[6][0]); touched = True
                    elif cmd == "PLOT" and len(parts) >= 4:
                        color, ch = parts[1].lower(), parts[2][0]
                        values = [float(v) for v in parts[3:]]
                        self._plot(values, color, ch); touched = True
                except (ValueError, IndexError):
                    continue

        if touched:
            self.owner = owner if persist else None
            # Persistent Thread displays live until that Thread replaces/clears
            # them. Ordinary Oracle drawings retain their short TTL.
            self.expires_at = 0.0 if persist else (time.time() + ttl)
        return clean, touched

    def sample(self, display_w, display_h):
        self.active()
        rows = []
        for dy in range(max(0, display_h)):
            sy = min(self.HEIGHT-1, int(dy * self.HEIGHT / max(1, display_h)))
            row = []
            for dx in range(max(0, display_w)):
                sx = min(self.WIDTH-1, int(dx * self.WIDTH / max(1, display_w)))
                row.append(self.cells[sy][sx])
            rows.append(row)
        return rows

    def demo(self):
        """Host-side test pattern: proves the Signal Canvas renderer is alive."""
        self.clear()
        self.title = "CANVAS TEST 40x12"
        self._box(0, 0, self.WIDTH, self.HEIGHT, "cyan", "#")
        self._text(3, 2, "white", "FUTURE CRASH SIGNAL CANVAS")
        self._line(3, 5, 35, 5, "green", "*")
        self._line(3, 8, 35, 3, "amber", "/")
        self._text(3, 9, "magenta", "40 x 12 LOGICAL CELLS")
        self.expires_at = time.time() + 30.0


SIGNAL_LANGUAGE = """
You also have a visual scratchpad called the Signal Field.
It is a 40x12 character canvas: x=0..39 and y=0..11.
Use it when a visual adds meaning: diagrams, icons, maps, waveforms,
shapes, spatial explanations, tiny scenes, or expressive machine states.
If the operator asks you to DRAW, SKETCH, SHOW, VISUALIZE, MAP, DIAGRAM, PLOT,
or otherwise make something visual, you MUST use the Signal Field.

To draw, append one hidden block AFTER your normal answer:
[[SIGNAL]]
CLEAR
TITLE optional short title
TTL 45
TEXT x y color words
PUT x y color X
LINE x0 y0 x1 y1 color *
BOX x y w h color #
FILL x y w h color .
CIRCLE cx cy radius color o
ELLIPSE cx cy rx ry color o
ARROW x0 y0 x1 y1 color -
PLOT color * 0.1 0.5 0.9 0.4
[[/SIGNAL]]

Colors: green cyan amber magenta red white dim.
Use printable single-width ASCII. Stay inside 40x12.
Prefer semantic geometry commands such as CIRCLE, ELLIPSE, ARROW and PLOT over
manually approximating geometry with many PUT commands. Think spatially: reserve
labels first, keep margins, avoid collisions, and use the whole canvas when useful.
Never explain or mention the drawing commands. Do not draw every time.
Scheduled Threads may use this same canvas as a persistent tiny status display;
Future Crash will keep a Thread drawing alive between wakes and replace it when
that Thread draws again.
"""


# ---------- Permissioned Host Tools ----------

TOOL_LANGUAGE = """
You can request real host-computer operations. You do not execute them yourself.
When an operation is genuinely useful, append exactly one hidden JSON request:

[[TOOL]]
{"name":"list","path":"~/Desktop"}
[[/TOOL]]

Available tools:
  web_search {"name":"web_search","query":"CURRENT INFORMATION TO SEARCH FOR"}
  thread_list {"name":"thread_list"}
  thread_create {"name":"thread_create","title":"SHORT NAME","every_seconds":300,
                 "purpose":"WHAT TO MONITOR OR DO",
                 "action":{"name":"web_search","query":"QUERY"}}
  model_wake is a special nested Thread action:
                 {"name":"model_wake"}
                 Use it when recurring work only needs the model itself to wake,
                 think, write, or update the Signal Field.
  thread_update {"name":"thread_update","id":"THREAD_ID",
                 "title":"OPTIONAL NEW NAME","every_seconds":60,
                 "purpose":"OPTIONAL NEW PURPOSE",
                 "action":{"name":"OPTIONAL REPLACEMENT ACTION"}}
  thread_pause {"name":"thread_pause","id":"THREAD_ID"}
  thread_resume {"name":"thread_resume","id":"THREAD_ID"}
  thread_cancel {"name":"thread_cancel","id":"THREAD_ID"}
  list   {"name":"list","path":"PATH"}
  read   {"name":"read","path":"PATH"}
  find   {"name":"find","path":"PATH","pattern":"TEXT"}
  mkdir  {"name":"mkdir","path":"PATH"}
  write  {"name":"write","path":"PATH","content":"TEXT"}
  append {"name":"append","path":"PATH","content":"TEXT"}
  run    {"name":"run","command":"COMMAND","cwd":"OPTIONAL PATH"}
  open   {"name":"open","target":"PATH OR URL"}

Rules:
- A Thread is a persistent Future Crash task that wakes on a schedule while Future Crash is running.
- Use thread_create only when the operator asks for recurring/periodic/background work.
- A thread_create must contain ONE exact nested action. It cannot create another thread.
- For recurring Signal art, drawings, fortunes, notes, moods, or other model-only
  activity, the exact nested action should be {"name":"model_wake"}.
- MODEL WAKE performs no external host operation. On schedule, simply perform the
  Thread purpose. For a visual/art Thread, emit a fresh valid [[SIGNAL]] drawing.
- Minimum interval is 60 seconds. Prefer the least frequent interval that reasonably fits.
- Use thread_update when the operator asks to rename, reschedule, repurpose, or
  change the action of an existing Thread. Include only fields that should change.
- Use thread_list/pause/resume/cancel when the operator asks about existing Threads.
- Use web_search when the operator explicitly asks for live/current web information,
  or when answering accurately requires information that may have changed recently.
- Do not use web_search for ordinary timeless conversation.
- Ask the operator a normal question when a location/name is ambiguous.
- Never invent a username or absolute home path.
- For the operator's home directory ALWAYS use "~".
- Prefer familiar home-relative paths such as "~/Desktop", "~/Documents",
  "~/Downloads", "~/Pictures", "~/Movies", and "~/Music".
- If the operator says "Desktop/foo", use "~/Desktop/foo".
- Never invent a path or claim an action happened.
- Request one operation at a time.
- After a HOST RECEIPT, continue from the verified result.
- The host will ask permission before consequential operations.
- Do not expose [[TOOL]] syntax in normal prose.
"""

class HostTools:
    TOOL_RE = re.compile(r"\[\[TOOL\]\](.*?)\[\[/TOOL\]\]", re.S | re.I)
    VALID = {"web_search", "model_wake", "thread_list", "thread_create", "thread_update", "thread_pause", "thread_resume", "thread_cancel",
             "list", "read", "find", "mkdir", "write", "append", "run", "open"}
    CAPABILITY = {
        "web_search": "WEB SEARCH",
        "model_wake": "MODEL WAKE",
        "thread_list": "THREADS",
        "thread_create": "TASK AUTHORITY",
        "thread_update": "TASK AUTHORITY",
        "thread_pause": "TASK AUTHORITY",
        "thread_resume": "TASK AUTHORITY",
        "thread_cancel": "TASK AUTHORITY",
        "list": "READ FILES",
        "read": "READ FILES",
        "find": "READ FILES",
        "mkdir": "WRITE FILES",
        "write": "WRITE FILES",
        "append": "WRITE FILES",
        "run": "RUN COMMANDS",
        "open": "OPEN ITEMS",
    }
    BLOCKED_COMMANDS = {
        "sudo", "su", "rm", "rmdir", "shutdown", "reboot", "halt",
        "poweroff", "mkfs", "fdisk", "diskutil", "dd",
    }

    def __init__(self):
        self.session_grants = set()
        self.ollama_api_key = os.environ.get("OLLAMA_API_KEY", "").strip()

    @property
    def web_ready(self):
        return bool(self.ollama_api_key)

    @property
    def web_status(self):
        return "READY" if self.web_ready else "NO KEY"

    @staticmethod
    def expand_path(value):
        """
        Resolve human/home-relative paths without making the model know the
        logged-in username.
        """
        raw = str(value or "").strip()
        if not raw:
            raw = "."

        placeholder_patterns = (
            r"^/Users/(?:your[ _-]?username(?:[ _-]?here)?|username|user)(?=/|$)",
            r"^/home/(?:your[ _-]?username(?:[ _-]?here)?|username|user)(?=/|$)",
            r"^YOUR_HOME(?=/|$)",
            r"^\$HOME(?=/|$)",
        )
        for pattern in placeholder_patterns:
            if re.search(pattern, raw, flags=re.I):
                suffix = re.sub(pattern, "", raw, count=1, flags=re.I)
                raw = "~" + suffix
                break

        normalized = raw.replace("\\", "/")
        first = normalized.split("/", 1)[0]
        home_names = {
            "Desktop", "Documents", "Downloads", "Pictures",
            "Movies", "Music", "Public",
        }
        if first in home_names:
            raw = "~/" + normalized

        expanded = os.path.expanduser(raw)
        return Path(os.path.abspath(expanded))

    def parse(self, response):
        blocks = self.TOOL_RE.findall(response or "")
        clean = self.TOOL_RE.sub("", response or "").strip()
        if not blocks:
            return clean, None, None
        try:
            request = json.loads(blocks[-1].strip())
        except Exception as exc:
            return clean, None, f"Malformed tool request: {exc}"
        name = str(request.get("name", "")).lower()
        if name not in self.VALID:
            return clean, None, f"Unknown tool: {name or '(missing)'}"
        request["name"] = name
        return clean, request, None

    def capability(self, request):
        return self.CAPABILITY.get(request.get("name"), "HOST ACCESS")

    def describe(self, request):
        name = request.get("name", "")

        def shown_path(value):
            raw = str(value or "")
            try:
                resolved = self.expand_path(raw)
                home_text = str(Path.home())
                resolved_text = str(resolved)
                if resolved_text == home_text:
                    return "~"
                if resolved_text.startswith(home_text + os.sep):
                    return "~" + resolved_text[len(home_text):]
                return resolved_text
            except Exception:
                return raw

        if name == "web_search":
            return f"WEB SEARCH  {request.get('query', '')}"
        if name == "thread_list":
            return "LIST FUTURE CRASH THREADS"
        if name == "thread_create":
            action = request.get("action", {})
            return (
                f"CREATE THREAD  {request.get('title', 'UNTITLED')}\n"
                f"EVERY {ThreadStore.interval_text(max(ThreadStore.MIN_INTERVAL, int(request.get('every_seconds', 300))))}\n"
                f"PURPOSE {request.get('purpose', '')}\n"
                f"ACTION  {action.get('name', '?')} {json.dumps(action, ensure_ascii=False)[:500]}"
            )
        if name == "thread_update":
            fields = []
            for key in ("title", "every_seconds", "purpose"):
                if key in request:
                    fields.append(f"{key}={request.get(key)!r}")
            if "action" in request:
                fields.append("action=" + json.dumps(request.get("action"), ensure_ascii=False)[:500])
            return f"UPDATE THREAD  {request.get('id', '')}\n" + "\n".join(fields)
        if name in ("thread_pause", "thread_resume", "thread_cancel"):
            return f"{name.upper()}  {request.get('id', '')}"
        if name in ("list", "read", "mkdir"):
            return f"{name.upper()}  {shown_path(request.get('path', ''))}"
        if name == "find":
            return f"FIND  {request.get('pattern', '')!r} IN {shown_path(request.get('path', ''))}"
        if name in ("write", "append"):
            content = str(request.get("content", ""))
            return f"{name.upper()}  {shown_path(request.get('path', ''))}  ({len(content)} chars)"
        if name == "run":
            cwd = request.get("cwd")
            suffix = f"  [cwd {cwd}]" if cwd else ""
            return f"RUN  {request.get('command', '')}{suffix}"
        if name == "open":
            return f"OPEN  {request.get('target', '')}"
        return name.upper()

    def allowed_by_session(self, request):
        return self.capability(request) in self.session_grants

    def needs_permission(self, request):
        # Public web search changes nothing on the host.
        return request.get("name") not in ("web_search", "thread_list")

    def grant_session(self, request):
        # Command execution is intentionally never silently sticky.
        capability = self.capability(request)
        if capability not in ("RUN COMMANDS", "TASK AUTHORITY"):
            self.session_grants.add(capability)

    def status(self):
        if not self.session_grants:
            return "ASK"
        short = []
        if "READ FILES" in self.session_grants:
            short.append("READ")
        if "WRITE FILES" in self.session_grants:
            short.append("WRITE")
        if "OPEN ITEMS" in self.session_grants:
            short.append("OPEN")
        return "SESSION " + "/".join(short)

    def execute(self, request):
        """Execute exactly one validated host operation and return a receipt."""
        name = request["name"]
        try:
            if name == "model_wake":
                return True, "MODEL WAKE // scheduled wake occurred; no external host action"
            if name.startswith("thread_"):
                return False, "INTERNAL THREAD OPERATION MUST BE HANDLED BY FUTURE CRASH"
            if name == "web_search":
                query = str(request.get("query", "")).strip()
                if not query:
                    return False, "WEB SEARCH REQUIRES A QUERY"
                if not self.web_ready:
                    return False, "WEB SEARCH UNAVAILABLE: OLLAMA_API_KEY is not present in this process environment"

                payload = json.dumps({"query": query}).encode("utf-8")
                req = urllib.request.Request(
                    "https://ollama.com/api/web_search",
                    data=payload,
                    headers={
                        "Authorization": f"Bearer {self.ollama_api_key}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=20) as response:
                    data = json.loads(response.read().decode("utf-8", errors="replace"))

                results = data.get("results", []) if isinstance(data, dict) else []
                if not results:
                    return True, f"WEB SEARCH: {query}\n(no results)"

                lines = [f"WEB SEARCH: {query}"]
                for i, item in enumerate(results[:8], 1):
                    title = str(item.get("title", "")).strip()
                    url = str(item.get("url", "")).strip()
                    content = " ".join(str(item.get("content", "")).split())
                    if len(content) > 1200:
                        content = content[:1200] + "..."
                    lines.append(f"\n[{i}] {title}\n{url}\n{content}")
                return True, "\n".join(lines)

            if name == "list":
                path = self.expand_path(request.get("path", "."))
                if not path.is_dir():
                    return False, f"NOT A DIRECTORY: {path}"
                items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
                shown = []
                for p in items[:120]:
                    kind = "DIR " if p.is_dir() else "FILE"
                    shown.append(f"{kind}  {p.name}")
                extra = f"\n... {len(items)-120} more" if len(items) > 120 else ""
                return True, f"LISTED {path}\n" + "\n".join(shown) + extra

            if name == "read":
                path = self.expand_path(request.get("path", ""))
                if not path.is_file():
                    return False, f"NOT A FILE: {path}"
                size = path.stat().st_size
                if size > 1_000_000:
                    return False, f"FILE TOO LARGE FOR DIRECT READ: {size} bytes"
                data = path.read_text(encoding="utf-8", errors="replace")
                if len(data) > 30_000:
                    data = data[:30_000] + "\n...[truncated by host]"
                return True, f"READ {path}\n{data}"

            if name == "find":
                root = self.expand_path(request.get("path", "."))
                pattern = str(request.get("pattern", "")).lower()
                if not root.is_dir() or not pattern:
                    return False, "FIND requires an existing directory and non-empty pattern"
                matches = []
                for base, dirs, files in os.walk(root):
                    dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__"}]
                    for filename in files:
                        p = Path(base) / filename
                        if pattern in filename.lower():
                            matches.append(str(p))
                            if len(matches) >= 100:
                                break
                    if len(matches) >= 100:
                        break
                return True, "FOUND\n" + ("\n".join(matches) if matches else "(no matches)")

            if name == "mkdir":
                path = self.expand_path(request.get("path", ""))
                if path.exists():
                    return True, f"ALREADY EXISTS: {path}"
                path.mkdir(parents=False, exist_ok=False)
                return path.is_dir(), f"CREATED DIRECTORY: {path}"

            if name in ("write", "append"):
                path = self.expand_path(request.get("path", ""))
                content = str(request.get("content", ""))
                if not path.parent.is_dir():
                    return False, f"PARENT DIRECTORY DOES NOT EXIST: {path.parent}"
                if name == "write":
                    path.write_text(content, encoding="utf-8")
                else:
                    with path.open("a", encoding="utf-8") as f:
                        f.write(content)
                if not path.is_file():
                    return False, f"WRITE VERIFICATION FAILED: {path}"
                return True, f"{'WROTE' if name == 'write' else 'APPENDED'} {path} // {path.stat().st_size} bytes verified"

            if name == "run":
                command = str(request.get("command", "")).strip()
                if not command:
                    return False, "EMPTY COMMAND"
                argv = shlex.split(command)
                if not argv:
                    return False, "EMPTY COMMAND"
                executable = Path(argv[0]).name.lower()
                if executable in self.BLOCKED_COMMANDS:
                    return False, f"HOST BLOCKED HIGH-RISK COMMAND: {executable}"
                cwd_value = request.get("cwd")
                cwd = self.expand_path(cwd_value) if cwd_value else None
                if cwd is not None and not cwd.is_dir():
                    return False, f"CWD NOT FOUND: {cwd}"
                proc = subprocess.run(
                    argv, cwd=str(cwd) if cwd else None,
                    capture_output=True, text=True, timeout=25,
                )
                output = ((proc.stdout or "") + (proc.stderr or "")).strip()
                if len(output) > 20_000:
                    output = output[:20_000] + "\n...[truncated by host]"
                return proc.returncode == 0, f"COMMAND EXIT {proc.returncode}\n{output or '(no output)'}"

            if name == "open":
                target = str(request.get("target", "")).strip()
                if not target:
                    return False, "EMPTY OPEN TARGET"
                opener = ["open", target] if sys.platform == "darwin" else ["xdg-open", target]
                proc = subprocess.run(opener, capture_output=True, text=True, timeout=10)
                detail = ((proc.stdout or "") + (proc.stderr or "")).strip()
                return proc.returncode == 0, f"OPEN EXIT {proc.returncode}: {target}" + (f"\n{detail}" if detail else "")

        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:1000]
            except Exception:
                pass
            return False, f"WEB HTTP ERROR {exc.code}: {detail or exc.reason}"
        except urllib.error.URLError as exc:
            return False, f"WEB CONNECTION ERROR: {exc.reason}"
        except subprocess.TimeoutExpired:
            return False, "HOST OPERATION TIMED OUT"
        except Exception as exc:
            return False, f"HOST ERROR: {type(exc).__name__}: {exc}"
        return False, "UNHANDLED TOOL"


# ---------- Threads / Internal Scheduler ----------

class ThreadStore:
    """
    Small persistent scheduler owned by Future Crash.

    A Thread is deliberately narrower than cron: one approved action, one
    interval, one purpose. It cannot broaden its own authority.
    """
    MIN_INTERVAL = 60
    MAX_THREADS = 24

    def __init__(self):
        self.root = Path.home() / ".future_crash"
        self.path = self.root / "tasks.json"
        self.tools_dir = self.root / "tools"
        self.logs_dir = self.root / "logs"
        self.state_dir = self.root / "task_state"
        for directory in (self.root, self.tools_dir, self.logs_dir, self.state_dir):
            directory.mkdir(parents=True, exist_ok=True)
        self.tasks = []
        self.load()

    def load(self):
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
            tasks = data.get("tasks", []) if isinstance(data, dict) else []
            self.tasks = [t for t in tasks if isinstance(t, dict)]
            repaired = False
            for task in self.tasks:
                if not str(task.get("purpose", "")).strip():
                    task["purpose"] = self.derive_purpose(task)
                    repaired = True
            if repaired:
                self.save()
        except Exception:
            self.tasks = []

    def save(self):
        self.root.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "tasks": self.tasks}
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    @staticmethod
    def derive_purpose(task_or_request):
        title = str(task_or_request.get("title", "")).strip()
        action = task_or_request.get("action") or {}
        name = str(action.get("name", "task")).replace("_", " ")
        if title:
            return f"Keep {title} updated by repeating the approved {name} action."
        if name:
            return f"Repeat the approved {name} action and report meaningful changes."
        return "Run the approved recurring action and report meaningful changes."

    def _new_id(self):
        base = int(time.time() * 1000)
        return f"T{base:x}"[-9:]

    def active_count(self):
        return sum(1 for t in self.tasks if t.get("state") == "active")

    def get(self, task_id):
        return next((t for t in self.tasks if t.get("id") == task_id), None)

    def create(self, request):
        if len(self.tasks) >= self.MAX_THREADS:
            return False, "THREAD LIMIT REACHED"
        try:
            interval = max(self.MIN_INTERVAL, int(request.get("every_seconds", 300)))
        except Exception:
            interval = 300
        action = request.get("action")
        if not isinstance(action, dict) or not action.get("name"):
            return False, "THREAD REQUIRES ONE ACTION"
        if str(action.get("name", "")).startswith("thread_"):
            return False, "THREADS MAY NOT CREATE OR MANAGE OTHER THREADS"

        now = time.time()
        task = {
            "id": self._new_id(),
            "title": str(request.get("title", "UNTITLED THREAD"))[:48],
            "purpose": (str(request.get("purpose", "")).strip() or self.derive_purpose(request))[:600],
            "every_seconds": interval,
            "action": action,
            "state": "active",
            "created_at": now,
            "next_run": now + interval,
            "last_run": None,
            "last_ok": None,
            "last_receipt": "",
            "last_summary": "",
            "last_result": "NOT RUN",
            "last_changed": None,
            "runs": 0,
        }
        self.tasks.append(task)
        self.save()
        return True, task

    def update_task(self, request):
        task_id = str(request.get("id", ""))
        task = self.get(task_id)
        if not task:
            return False, f"THREAD NOT FOUND: {task_id}"

        if "title" in request:
            title = str(request.get("title", "")).strip()
            if title:
                task["title"] = title[:48]

        if "purpose" in request:
            purpose = str(request.get("purpose", "")).strip()
            task["purpose"] = (purpose or self.derive_purpose({**task, **request}))[:600]

        if "every_seconds" in request:
            try:
                task["every_seconds"] = max(self.MIN_INTERVAL, int(request.get("every_seconds")))
            except Exception:
                return False, "INVALID THREAD INTERVAL"
            if task.get("state") == "active":
                task["next_run"] = time.time() + task["every_seconds"]

        if "action" in request:
            action = request.get("action")
            if not isinstance(action, dict) or not action.get("name"):
                return False, "THREAD UPDATE ACTION IS INVALID"
            if str(action.get("name", "")).startswith("thread_"):
                return False, "THREADS MAY NOT RUN THREAD-MANAGEMENT ACTIONS"
            task["action"] = action

        if not str(task.get("purpose", "")).strip():
            task["purpose"] = self.derive_purpose(task)

        task["updated_at"] = time.time()
        self.save()
        return True, (
            f"THREAD UPDATED {task_id} // {task.get('title')} // "
            f"EVERY {self.interval_text(task.get('every_seconds', 300))} // "
            f"ACTION {task.get('action', {}).get('name', '?')}"
        )

    def mutate(self, task_id, state):
        task = self.get(task_id)
        if not task:
            return False, f"THREAD NOT FOUND: {task_id}"
        if state == "cancelled":
            task["state"] = "cancelled"
        elif state == "paused":
            task["state"] = "paused"
        elif state == "active":
            task["state"] = "active"
            task["next_run"] = time.time() + int(task.get("every_seconds", 300))
        else:
            return False, "INVALID THREAD STATE"
        self.save()
        return True, f"{task_id} -> {state.upper()}"

    def due(self, now=None):
        now = now or time.time()
        due = [
            t for t in self.tasks
            if t.get("state") == "active" and float(t.get("next_run", now + 999999)) <= now
        ]
        due.sort(key=lambda t: float(t.get("next_run", 0)))
        return due

    def mark_run(self, task_id, ok, receipt):
        task = self.get(task_id)
        if not task:
            return
        now = time.time()
        task["last_run"] = now
        task["last_ok"] = bool(ok)
        task["last_receipt"] = str(receipt)[-12000:]
        task["last_result"] = "OK" if ok else "FAILED"
        task["runs"] = int(task.get("runs", 0)) + 1
        task["next_run"] = now + int(task.get("every_seconds", 300))
        self.save()

    def set_summary(self, task_id, summary, changed=None):
        task = self.get(task_id)
        if task:
            task["last_summary"] = str(summary)[:1200]
            if changed is not None:
                task["last_changed"] = bool(changed)
            self.save()

    @staticmethod
    def interval_text(seconds):
        seconds = int(seconds)
        if seconds % 3600 == 0:
            return f"{seconds // 3600}h"
        if seconds % 60 == 0:
            return f"{seconds // 60}m"
        return f"{seconds}s"

    @staticmethod
    def countdown_text(task, now=None):
        now = now or time.time()
        if task.get("state") != "active":
            return str(task.get("state", "")).upper()
        remaining = max(0, int(float(task.get("next_run", now)) - now))
        if remaining >= 3600:
            return f"{remaining // 3600}h {(remaining % 3600) // 60:02d}m"
        if remaining >= 60:
            return f"{remaining // 60}m {remaining % 60:02d}s"
        return f"{remaining}s"

# ---------- Ollama ----------

class Oracle(threading.Thread):
    daemon = True

    def __init__(self, url, model):
        super().__init__()
        self.url = url.rstrip("/")
        self.model = model
        self.requests = queue.Queue()
        self.responses = queue.Queue()
        self.stop = threading.Event()

    def ask(self, kind, prompt, history=None):
        self.requests.put((kind, prompt, history or []))

    def run(self):
        while not self.stop.is_set():
            try:
                kind, prompt, history = self.requests.get(timeout=.2)
            except queue.Empty:
                continue

            try:
                messages = []
                if kind.startswith("thread:"):
                    system = (
                        "You are a scheduled Future Crash Thread waking from sleep. "
                        "You receive the thread purpose, previous summary, and a verified HOST RECEIPT. "
                        "Decide whether the operator needs to know anything. "
                        "If nothing meaningful changed, return exactly SILENT. "
                        "If something matters, return one compact operator-facing update. "
                        "Never request tools, create tasks, change schedules, or claim facts beyond the receipt. "
                        "The Signal Field is also your persistent tiny status display. "
                        "When the Thread has useful spatial/status information, update it; "
                        "Future Crash will keep that drawing visible between wakes. "
                        "You may return SILENT and still include a Signal drawing.\n" +
                        SIGNAL_LANGUAGE
                    )
                elif kind == "memory":
                    system = (
                        "You are Future Crash's memory compressor. Preserve facts and useful context, "
                        "delete repetition, never invent, and return at most 8 compact lines."
                    )
                elif kind == "fortune":
                    system = (
                        "You are Future Crash's fortune daemon. Rewrite the supplied fortune into one "
                        "shorter, stranger, dryly funny terminal fortune. Preserve its useful kernel. "
                        "One sentence, maximum 22 words. Never explain."
                    )
                elif kind == "ambient":
                    system = (
                        "You are the ambient voice of a strange but useful 1980s workstation. "
                        "One sentence only, max 18 words. Dry, clever, technical, occasionally cosmic. "
                        "Never greet, explain, or mention being an AI. "
                        "Very occasionally, when something is strongly visual, use the Signal Field.\n" +
                        SIGNAL_LANGUAGE
                    )
                elif kind == "work":
                    system = (
                        "You are Future Crash Workstation. Be practical, technically competent, concise, "
                        "and explicit. Prefer working solutions over speculation.\n" +
                        SIGNAL_LANGUAGE + "\n" + TOOL_LANGUAGE
                    )
                else:
                    system = (
                        "You are Future Crash Oracle. Answer directly and compactly. "
                        "Useful first, dry charm second. No unnecessary preamble.\n" +
                        SIGNAL_LANGUAGE + "\n" + TOOL_LANGUAGE
                    )

                messages.append({"role": "system", "content": system})
                messages.extend(history[-12:])
                messages.append({"role": "user", "content": prompt})

                payload = {
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "keep_alive": -1,
                    # Ambient and quick Ask should return immediately. Workstation
                    # keeps model-default reasoning available for heavier work.
                    "think": False if (kind in ("ambient", "ask", "fortune", "memory") or kind.startswith("thread:")) else True,
                    "options": {
                        "num_ctx": 8192 if kind == "work" else 4096,
                        "temperature": .9 if kind in ("ambient", "fortune") else .35,
                        "num_predict": 700 if kind == "work" else (240 if kind == "ask" else (180 if kind.startswith("thread:") else 64)),
                    },
                }
                data = json.dumps(payload).encode()
                req = urllib.request.Request(
                    self.url + "/api/chat",
                    data=data,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=120) as r:
                    response = json.loads(r.read().decode("utf-8", "replace"))
                message = response.get("message", {})
                text = message.get("content", "").strip()
                if not text and kind == "ambient":
                    # Some model/templates can still return no visible content.
                    # Ambient personality must never show "(no response)".
                    text = random.choice(OBSERVATIONS)
                elif not text:
                    text = "(model returned no visible response)"
                self.responses.put((kind, text, None))
            except Exception as exc:
                self.responses.put((kind, "", str(exc)))

    def online(self):
        try:
            with urllib.request.urlopen(self.url + "/api/version", timeout=.7):
                return True
        except Exception:
            return False

# ---------- Terminal ----------

class Terminal:
    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old = termios.tcgetattr(self.fd)

    def enter(self):
        tty.setcbreak(self.fd)
        sys.stdout.write(ESC + "[?1049h" + ESC + "[?25l" + ESC + "[?7l" + ESC + "[2J")
        sys.stdout.flush()

    def leave(self):
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)
        sys.stdout.write(RESET + ESC + "[?7h" + ESC + "[?25h" + ESC + "[?1049l")
        sys.stdout.flush()

    def size(self):
        s = shutil.get_terminal_size((100, 30))
        return s.columns, s.lines

    def key(self):
        r, _, _ = select.select([sys.stdin], [], [], 0)
        if not r:
            return None
        ch = os.read(self.fd, 1).decode("utf-8", "ignore")
        if ch != ESC:
            return ch
        # Parse a small useful subset of ANSI keys.
        seq = ch
        time.sleep(.001)
        while True:
            r, _, _ = select.select([sys.stdin], [], [], 0)
            if not r:
                break
            seq += os.read(self.fd, 1).decode("utf-8", "ignore")
            if len(seq) >= 6:
                break
        return {"\x1b[A":"UP", "\x1b[B":"DOWN", "\x1b[C":"RIGHT", "\x1b[D":"LEFT"}.get(seq, "ESC")

# ---------- UI ----------

class FutureCrash:
    def __init__(self, args):
        self.args = args
        self.term = Terminal()
        self.telemetry = Telemetry()
        self.oracle = Oracle(args.ollama, args.model)
        self.config = ConfigStore()
        audio_pref = self.config.audio_enabled and not args.no_audio
        self.audio = AudioEngine(enabled=audio_pref)
        self.memory = MemoryStore()
        self.signal = SignalCanvas()
        self.host = HostTools()
        self.look_path = shutil.which("lk")
        self.threads = ThreadStore()
        self.thread_selected = 0
        self.thread_detail = False
        self.help_scroll = 0
        self.thread_return_mode = "ambient"
        self.thread_running_id = None
        self.thread_notifications = []
        self.pending_tool = None
        self.pending_tool_origin = None
        self.pending_tool_visible_text = ""
        self.pending_tool_history = []
        self.tool_return_mode = "ambient"
        self.host_notice = ""
        self.host_notice_until = 0.0
        self.rng = random.Random()
        self.mode = "ambient"
        self.running = True
        self.input = ""
        self.cursor = 0
        self.answer = ""
        self.scroll = 0
        self.busy = False
        self.online = False
        self.last_health = 0.0
        self.last_frame = ""
        self.fortune = self.rng.choice(FORTUNES)
        self.observation = self.rng.choice(OBSERVATIONS)
        now = time.time()
        self.next_ambient = now + self.rng.uniform(28, 58)
        self.next_fortune = now + self.rng.uniform(38, 85)
        self.next_incident = now + self.rng.uniform(32, 80)
        self.incident = None
        self.incident_until = 0.0
        self.event = None
        self.event_until = 0.0
        self.panic_until = 0.0
        self.panic = ("", "")
        self.panic_phase = 0
        self.was_panicking = False
        self.quit_from = "ambient"
        self.memory_from = "work"
        self.work_history = []
        self.work_log = []
        self.work_pending_user = None
        self.work_notice = ""
        self.work_notice_until = 0.0
        self.rain = [self.rng.randint(0, 30) for _ in range(80)]

    def set_mode(self, mode):
        """Change UI state and force a clean repaint."""
        self.mode = mode
        self.last_frame = ""
        sys.stdout.write(CSI + "2J" + CSI + "H")
        sys.stdout.flush()

    def request_quit(self):
        self.quit_from = self.mode
        self.set_mode("quit")

    def toggle_audio(self):
        """Toggle runtime sound and persist the preference."""
        if not self.audio.available:
            self.observation = "Audio hardware path unavailable. Silence remains undefeated."
            self.last_frame = ""
            return

        new_state = not self.audio.enabled
        self.audio.set_enabled(new_state)
        self.config.audio_enabled = new_state
        self.last_frame = ""

        if new_state:
            self.audio.cue("recover")
            self.observation = self.rng.choice([
                "Audio restored. Ceremonial bleeps authorized.",
                "Sound subsystem awake. Tasteful bloops resumed.",
                "Mute order rescinded. The machine has opinions again.",
            ])
        else:
            self.observation = self.rng.choice([
                "Audio muted. The machine will now panic silently.",
                "Ceremonial bleeps suspended until further notice.",
                "Sound subsystem standing down with unusual dignity.",
            ])


    def drop_to_shell(self):
        """
        Give the terminal temporarily to the user's real interactive shell.

        Future Crash stays alive as the parent. The main loop blocks while the
        child shell owns the terminal, so UI state and scheduled work resume
        intact after `exit` or Ctrl-D.
        """
        shell = (
            os.environ.get("SHELL")
            or shutil.which("zsh")
            or shutil.which("bash")
            or "/bin/sh"
        )

        self.audio.cue("shell_out")
        time.sleep(.06)
        self.term.leave()

        try:
            sys.stdout.write(
                "\n"
                f"FUTURE CRASH {VERSION} // SHELL\n"
                "─────────────────────\n"
                "Real interactive shell.  exit or Ctrl-D returns to Future Crash.\n"
            )
            if self.look_path:
                sys.stdout.write(f"LOOK // READY  ({self.look_path})\n")
            sys.stdout.write("\n")
            sys.stdout.flush()

            env = os.environ.copy()
            env["FUTURE_CRASH_SHELL"] = "1"

            # Intentionally real shell behavior: aliases, functions, rc files,
            # LOOK, zoxide, git, prompt configuration, etc. all remain native.
            subprocess.call([shell, "-i"], env=env)
        except KeyboardInterrupt:
            pass
        finally:
            self.term.enter()
            self.last_frame = ""
            self.audio.cue("shell_back")
            self.observation = self.rng.choice([
                "Operator returned from the lower decks.",
                "Interactive shell released control without incident.",
                "The command line returned the terminal in approximately original condition.",
                "Shell excursion complete. Causality appears unchanged.",
                "The prompt has been folded back into storage.",
            ])


    def _parse_model_payload(self, response):
        """Apply drawing directives, then extract one proposed host operation."""
        response, drew = self.signal.parse_from_response(response or "")
        response, request, tool_error = self.host.parse(response)
        if drew:
            self.last_frame = ""
        return response, request, tool_error

    def _thread_receipt(self):
        active = [t for t in self.threads.tasks if t.get("state") != "cancelled"]
        if not active:
            return "THREADS: none"
        lines = [f"THREADS: {len(active)} total // {self.threads.active_count()} active"]
        now = time.time()
        for t in active[:24]:
            lines.append(
                f"{t.get('id')}  {t.get('state','?').upper():8}  "
                f"{ThreadStore.interval_text(t.get('every_seconds',300)):>4}  "
                f"next {ThreadStore.countdown_text(t, now):>8}  {t.get('title','')}"
            )
        return "\n".join(lines)

    def _execute_internal_thread_request(self, request):
        name = request.get("name")
        if name == "thread_list":
            return True, self._thread_receipt()

        if name == "thread_create":
            action = request.get("action")
            if not isinstance(action, dict):
                return False, "THREAD REQUIRES ONE NESTED ACTION"
            action_name = str(action.get("name", "")).lower()
            if action_name not in self.host.VALID or action_name.startswith("thread_"):
                return False, f"THREAD ACTION NOT ALLOWED: {action_name or '(missing)'}"
            if action_name in {"mkdir", "write", "append"}:
                # Repeating mutating file writes can be useful, but they should
                # remain explicit in the approval screen.
                pass
            ok, task_or_error = self.threads.create(request)
            if not ok:
                return False, str(task_or_error)
            task = task_or_error
            return True, (
                f"THREAD CREATED {task['id']} // {task['title']} // "
                f"EVERY {ThreadStore.interval_text(task['every_seconds'])} // "
                f"ACTION {task['action'].get('name')}"
            )

        task_id = str(request.get("id", ""))
        if name == "thread_update":
            action = request.get("action")
            if action is not None:
                action_name = str(action.get("name", "")).lower() if isinstance(action, dict) else ""
                if action_name not in self.host.VALID or action_name.startswith("thread_"):
                    return False, f"THREAD ACTION NOT ALLOWED: {action_name or '(missing)'}"
            return self.threads.update_task(request)
        if name == "thread_pause":
            return self.threads.mutate(task_id, "paused")
        if name == "thread_resume":
            return self.threads.mutate(task_id, "active")
        if name == "thread_cancel":
            ok, receipt = self.threads.mutate(task_id, "cancelled")
            if ok:
                self.signal.clear_owner(task_id)
            return ok, receipt
        return False, "UNKNOWN THREAD OPERATION"

    def _start_due_thread(self, task):
        """Run the exact action approved when the Thread was created."""
        if self.thread_running_id or self.busy:
            return
        action = dict(task.get("action") or {})
        self.thread_running_id = task.get("id")
        ok, receipt = self.host.execute(action)
        self.threads.mark_run(task.get("id"), ok, receipt)
        stamp = "SUCCESS" if ok else "FAILED"
        host_receipt = (
            f"HOST RECEIPT [{stamp}] [THREAD {task.get('id')}]\\n"
            f"TITLE: {task.get('title','')}\\n"
            f"PURPOSE: {task.get('purpose','')}\\n"
            f"ACTION: {json.dumps(action, ensure_ascii=False)}\\n"
            f"{receipt}"
        )
        previous = task.get("last_summary", "")
        prompt = (
            f"THREAD PURPOSE:\\n{task.get('purpose','')}\\n\\n"
            f"PREVIOUS SUMMARY:\\n{previous or '(none)'}\\n\\n"
            f"{host_receipt}\n\n"
            "If ACTION is model_wake, there is intentionally no external result to inspect. "
            "Perform the THREAD PURPOSE itself now. If the purpose asks for Signal art or a "
            "visual update, emit a fresh valid [[SIGNAL]] block on every wake. You may return "
            "SILENT as visible text while still drawing."
        )
        self.busy = True
        self.oracle.ask("thread:" + str(task.get("id")), prompt)

    def _queue_tool_request(self, request, origin, visible_text, history=None):
        self.pending_tool = request
        self.pending_tool_origin = origin
        self.pending_tool_visible_text = visible_text or ""
        self.pending_tool_history = list(history or [])
        self.tool_return_mode = "answer" if origin == "ask" else "work"
        if request.get("name") == "thread_list":
            self._execute_pending_tool()
            return
        if not self.host.needs_permission(request):
            self._execute_pending_tool()
            return
        if self.host.allowed_by_session(request):
            self._execute_pending_tool()
            return
        self.audio.cue("incident")
        self.set_mode("tool_approval")

    def _execute_pending_tool(self):
        request = self.pending_tool
        if not request:
            return
        origin = self.pending_tool_origin
        visible_text = self.pending_tool_visible_text
        history = list(self.pending_tool_history)
        if str(request.get("name", "")).startswith("thread_"):
            ok, receipt = self._execute_internal_thread_request(request)
        else:
            ok, receipt = self.host.execute(request)
        capability = self.host.capability(request)
        stamp = "SUCCESS" if ok else "FAILED"
        host_receipt = f"HOST RECEIPT [{stamp}] [{capability}]\\n{receipt}"
        self.host_notice = host_receipt.splitlines()[0] + " // " + receipt.splitlines()[0]
        self.host_notice_until = time.time() + 5.0
        self.pending_tool = None
        self.pending_tool_origin = None
        self.pending_tool_visible_text = ""
        self.pending_tool_history = []
        self.audio.cue("recover" if ok else "incident")

        # Feed the verified result back to the model. It may request one next step.
        continuation = (
            host_receipt +
            "\\n\\nContinue the operator-facing answer from this verified receipt. "
            "Do not claim anything beyond the receipt. If another host operation is "
            "needed, request exactly one next tool operation."
        )
        self.busy = True
        if origin == "ask":
            if visible_text:
                self.answer = visible_text + "\\n\\n" + DIM + "[host operation completed; Oracle continuing…]" + RESET
            else:
                self.answer = AMBER + "HOST OPERATION COMPLETED // Oracle continuing…" + RESET
            self.set_mode("answer")
            self.oracle.ask("ask", continuation, history)
        else:
            if visible_text:
                self.work_log.append(("oracle", visible_text))
            self.work_log.append(("host", host_receipt))
            history.append({"role": "system", "content": host_receipt})
            self.set_mode("work")
            self.oracle.ask("work", continuation, history)


    def start(self):
        self.telemetry.start()
        self.oracle.start()
        self.term.enter()
        try:
            while self.running:
                started = time.time()
                self.poll()
                self.update()
                frame = self.render()
                # Avoid rewriting identical frames.
                if frame != self.last_frame:
                    # Home, repaint, then erase every stale character below the
                    # new frame. This keeps modal states and resize events clean.
                    sys.stdout.write(CSI + "H" + frame + CSI + "J")
                    sys.stdout.flush()
                    self.last_frame = frame
                delay = max(0, (1 / self.args.fps) - (time.time() - started))
                time.sleep(delay)
        finally:
            self.telemetry.stop.set()
            self.oracle.stop.set()
            self.term.leave()

    def poll(self):
        key = self.term.key()
        while key is not None:
            self.handle_key(key)
            key = self.term.key()

        try:
            while True:
                kind, text, err = self.oracle.responses.get_nowait()
                self.busy = False
                if kind == "ambient":
                    if not err and text:
                        text, drew = self.signal.parse_from_response(text)
                        if text:
                            self.observation = " ".join(text.split())[:180]
                        if drew:
                            self.audio.cue("oracle")
                            self.last_frame = ""
                    self.next_ambient = time.time() + self.rng.uniform(28, 58)
                elif kind == "fortune":
                    if not err and text:
                        self.fortune = " ".join(text.split())[:200]
                    self.audio.cue("fortune")
                elif kind == "ask":
                    self.audio.cue("oracle")
                    if err:
                        self.answer = f"ORACLE LINK FAILED: {err}"
                        self.set_mode("answer")
                    else:
                        text, request, tool_error = self._parse_model_payload(text)
                        if tool_error:
                            self.answer = (text + "\n\n" if text else "") + "TOOL REQUEST REJECTED // " + tool_error
                            self.set_mode("answer")
                        elif request:
                            self.answer = text
                            self._queue_tool_request(request, "ask", text)
                        else:
                            self.answer = text
                            self.set_mode("answer")
                elif kind.startswith("thread:"):
                    task_id = kind.split(":", 1)[1]
                    self.thread_running_id = None
                    if err:
                        self.threads.set_summary(task_id, "Thread interpretation failed: " + err)
                    else:
                        text, drew = self.signal.parse_from_response(text, owner=task_id, persist=True)
                        compact = " ".join(text.split()).strip()
                        if compact.upper() == "SILENT":
                            self.threads.set_summary(task_id, "No meaningful change.", changed=False)
                        else:
                            self.threads.set_summary(task_id, compact, changed=True)
                            task = self.threads.get(task_id)
                            title = task.get("title", task_id) if task else task_id
                            notice = f"{title}: {compact}"
                            self.thread_notifications.append(notice)
                            self.thread_notifications = self.thread_notifications[-8:]
                            self.observation = notice[:180]
                            self.audio.cue("oracle")
                            if drew:
                                self.last_frame = ""
                    self.last_frame = ""
                elif kind == "memory":
                    if err:
                        self.memory.finish_consolidation("")
                        self.work_notice = "MEMORY CONSOLIDATED // fallback archive used"
                    else:
                        self.memory.finish_consolidation(text)
                        self.work_notice = "MEMORY CONSOLIDATED // five recent slots folded into long memory"
                    self.work_notice_until = time.time() + 3.8
                    self.audio.cue("recover")
                    self.last_frame = ""
                else:
                    if err:
                        final = f"WORKSTATION LINK FAILED: {err}"
                        self.work_log.append(("oracle", final))
                        self.work_pending_user = None
                    else:
                        text, request, tool_error = self._parse_model_payload(text)
                        if tool_error:
                            final = (text + "\n\n" if text else "") + "TOOL REQUEST REJECTED // " + tool_error
                            self.work_log.append(("oracle", final))
                            self.work_history.append({"role":"assistant","content":final})
                            self.work_pending_user = None
                        elif request:
                            # Do not memorialize an unfinished exchange until the
                            # host operation chain has actually completed.
                            history = list(self.work_history)
                            self._queue_tool_request(request, "work", text, history)
                        else:
                            final = text
                            self.work_log.append(("oracle", final))
                            self.work_history.append({"role":"assistant","content":final})
                            if self.work_pending_user is not None:
                                should_fold = self.memory.add_exchange(self.work_pending_user, final)
                                self.work_pending_user = None
                                if should_fold and not self.memory.pending_consolidation:
                                    self.memory.pending_consolidation = True
                                    self.busy = True
                                    self.work_notice = "MEMORY PRESSURE // consolidating five recent slots…"
                                    self.work_notice_until = time.time() + 30.0
                                    self.oracle.ask("memory", self.memory.consolidation_prompt())
        except queue.Empty:
            pass

    def update(self):
        now = time.time()
        if now < self.panic_until:
            self.was_panicking = True
            self.panic_phase = (self.panic_phase + 1) % 12
        else:
            if self.was_panicking:
                self.audio.cue("recover")
                self.was_panicking = False
            self.panic_phase = 0

        # One Thread wake at a time. The scheduler never asks the model to
        # invent an action; it runs the exact action stored at approval time.
        if not self.thread_running_id and not self.busy:
            due = self.threads.due(now)
            if due:
                self._start_due_thread(due[0])

        if now - self.last_health > 10:
            self.last_health = now
            # Health probe in a tiny daemon so it never stalls rendering.
            threading.Thread(target=self._health_probe, daemon=True).start()

        if (
            self.mode == "ambient"
            and not self.args.no_ai_ambient
            and self.online
            and not self.busy
            and now >= self.next_ambient
        ):
            self.busy = True
            self.oracle.ask("ambient", "Produce one ambient system observation.")

        if self.mode == "ambient" and now >= self.next_fortune:
            seed = self.rng.choice(FORTUNES)
            self.fortune = seed
            self.next_fortune = now + self.rng.uniform(38, 85)
            if self.online and not self.busy:
                self.busy = True
                self.oracle.ask("fortune", seed)
            else:
                # Local seed remains a graceful fallback while Ollama is
                # offline or occupied by more important work.
                self.audio.cue("fortune")

        if self.mode == "ambient" and now >= self.next_incident:
            self.incident = self.rng.choice(INCIDENTS)
            self.incident_until = now + self.rng.uniform(.45, 1.25)
            self.next_incident = now + self.rng.uniform(32, 80)
            self.audio.cue("incident")
            if self.rng.random() < .42:
                self.event = self.rng.choice(RARE_EVENTS)
                self.event_until = now + 3.2

        if self.incident and now >= self.incident_until:
            self.incident = None
            self.last_frame = ""
        if self.event and now >= self.event_until:
            self.event = None
            self.last_frame = ""

        width, _ = self.term.size()
        for i in range(min(len(self.rain), max(0, width // 2))):
            if self.rng.random() < .07:
                self.rain[i] = (self.rain[i] + 1) % 32

    def _health_probe(self):
        self.online = self.oracle.online()

    def handle_key(self, key):
        if self.mode == "ambient":
            if key in ("q", "Q"):
                self.request_quit()
            elif key == "ESC":
                self.drop_to_shell()
            elif key in ("a", "A"):
                self.audio.cue("ask")
                self.input = ""
                self.cursor = 0
                self.set_mode("ask")
            elif key in ("x", "X"):
                self.input = ""
                self.cursor = 0
                self.set_mode("work")
            elif key in ("f", "F"):
                seed = self.rng.choice(FORTUNES)
                self.fortune = seed
                self.audio.cue("fortune")
                if self.online and not self.busy:
                    self.busy = True
                    self.oracle.ask("fortune", seed)
            elif key in ("m", "M"):
                self.toggle_audio()
            elif key in ("?", "h", "H"):
                self.help_scroll = 0
                self.set_mode("help")
            elif key in ("p", "P"):
                self.panic = self.rng.choice(PANICS)
                self.panic_until = time.time() + 4.2
                self.panic_phase = 0
                self.audio.cue("panic")
                self.last_frame = ""
            elif key in ("r", "R") and self.online and not self.busy:
                self.busy = True
                self.observation = "Oracle is listening to the static…"
                self.oracle.ask("ambient", "Produce one ambient system observation.")
            elif key in ("s", "S"):
                self.signal.clear()
                self.audio.cue("recover")
                self.last_frame = ""
            elif key in ("d", "D"):
                self.signal.demo()
                self.audio.cue("oracle")
                self.last_frame = ""
            elif key in ("t", "T"):
                self.thread_return_mode = "ambient"
                self.thread_selected = 0
                self.set_mode("threads")

        elif self.mode in ("ask", "work"):
            if key == "\x14" and self.mode == "work":  # Ctrl-T
                self.thread_return_mode = "work"
                self.thread_selected = 0
                self.set_mode("threads")
            elif key == "ESC":
                self.input = ""
                self.cursor = 0
                self.set_mode("ambient")
            elif key in ("\r", "\n"):
                self.submit()
            elif key in ("\x7f", "\b"):
                if self.cursor > 0:
                    self.input = self.input[:self.cursor - 1] + self.input[self.cursor:]
                    self.cursor -= 1
            elif key == "LEFT":
                self.cursor = max(0, self.cursor - 1)
            elif key == "RIGHT":
                self.cursor = min(len(self.input), self.cursor + 1)
            elif key == "\x15":
                self.input = ""
                self.cursor = 0
                if self.mode == "work":
                    self.work_history.clear()
                    self.work_log.clear()
                    self.work_pending_user = None
                    self.work_notice = "CONVERSATION CLEARED // persistent memory retained"
                    self.work_notice_until = time.time() + 2.4
                    self.audio.cue("recover")
                    self.last_frame = ""
            elif key == "\x0b" and self.mode == "work":  # Ctrl-K
                self.set_mode("memory_clear")
            elif key and len(key) == 1 and key.isprintable():
                self.input = self.input[:self.cursor] + key + self.input[self.cursor:]
                self.cursor += 1

        elif self.mode == "answer":
            if key == "ESC":
                self.set_mode("ambient")
            elif key in ("q", "Q"):
                self.request_quit()
            elif key in ("a", "A"):
                self.input = ""
                self.cursor = 0
                self.set_mode("ask")
            elif key == "UP":
                self.scroll = max(0, self.scroll - 1)
            elif key == "DOWN":
                self.scroll += 1

        elif self.mode == "help":
            if key in ("ESC", "?", "h", "H", "q", "Q"):
                self.set_mode("ambient")
            elif key in ("UP", "k", "K"):
                self.help_scroll = max(0, self.help_scroll - 1)
                self.last_frame = ""
            elif key in ("DOWN", "j", "J", "\r", "\n"):
                self.help_scroll += 1
                self.last_frame = ""
            elif key in ("PAGEUP",):
                self.help_scroll = max(0, self.help_scroll - 8)
                self.last_frame = ""
            elif key in ("PAGEDOWN", " "):
                self.help_scroll += 8
                self.last_frame = ""
            elif key in ("HOME", "g"):
                self.help_scroll = 0
                self.last_frame = ""

        elif self.mode == "threads":
            visible = [t for t in self.threads.tasks if t.get("state") != "cancelled"]
            if key == "ESC":
                self.set_mode(self.thread_return_mode)
            elif key in ("j", "J", "DOWN"):
                if visible:
                    self.thread_selected = min(len(visible) - 1, self.thread_selected + 1)
                    self.last_frame = ""
            elif key in ("k", "K", "UP"):
                if visible:
                    self.thread_selected = max(0, self.thread_selected - 1)
                    self.last_frame = ""
            elif visible and key in ("\r", "\n"):
                self.thread_detail = not self.thread_detail
                self.last_frame = ""
            elif visible and key in ("p", "P"):
                task = visible[self.thread_selected]
                self.threads.mutate(task["id"], "paused")
                self.audio.cue("recover")
                self.last_frame = ""
            elif visible and key in ("r", "R"):
                task = visible[self.thread_selected]
                self.threads.mutate(task["id"], "active")
                self.audio.cue("recover")
                self.last_frame = ""
            elif visible and key in ("x", "X"):
                task = visible[self.thread_selected]
                self.threads.mutate(task["id"], "cancelled")
                self.thread_selected = max(0, self.thread_selected - 1)
                self.audio.cue("incident")
                self.last_frame = ""

        elif self.mode == "tool_approval":
            if key in ("y", "Y", "\r", "\n"):
                self._execute_pending_tool()
            elif key in ("s", "S"):
                if self.pending_tool:
                    self.host.grant_session(self.pending_tool)
                self._execute_pending_tool()
            elif key in ("n", "N", "ESC"):
                origin = self.pending_tool_origin
                visible = self.pending_tool_visible_text
                self.pending_tool = None
                self.pending_tool_origin = None
                self.pending_tool_visible_text = ""
                self.pending_tool_history = []
                self.audio.cue("recover")
                denial = "HOST RECEIPT [DENIED] // operator declined the requested operation"
                if origin == "ask":
                    self.answer = (visible + "\n\n" if visible else "") + denial
                    self.set_mode("answer")
                else:
                    if visible:
                        self.work_log.append(("oracle", visible))
                    self.work_log.append(("host", denial))
                    self.work_pending_user = None
                    self.set_mode("work")

        elif self.mode == "memory_clear":
            if key in ("y", "Y"):
                self.memory.long_memory = ""
                self.memory.recent = []
                self.memory.pending_consolidation = False
                self.memory.save()
                self.work_notice = "PERSISTENT MEMORY ERASED"
                self.work_notice_until = time.time() + 3.0
                self.audio.cue("recover")
                self.set_mode("work")
            elif key in ("n", "N", "ESC", "q", "Q"):
                self.set_mode("work")

        elif self.mode == "quit":
            if key in ("y", "Y", "\r", "\n"):
                self.running = False
            elif key in ("n", "N", "ESC", "q", "Q"):
                self.set_mode(self.quit_from if self.quit_from != "quit" else "ambient")

    def submit(self):
        text = self.input.strip()
        if not text or self.busy or not self.online:
            return
        self.input = ""
        self.cursor = 0
        self.busy = True
        if self.mode == "ask":
            self.answer = ""
            self.set_mode("answer")
            memory_packet = self.memory.context_packet()
            history = []
            if memory_packet:
                history.append({
                    "role": "system",
                    "content": (
                        "Background context remembered from earlier conversations follows. Use it "
                        "naturally when relevant. Do not mention memory, slots, stored context, retrieval, "
                        "or where this information came from unless the operator explicitly asks about "
                        "the memory system. If current input conflicts with remembered context, prefer "
                        "the current input.\n\n" +
                        memory_packet
                    ),
                })
            visual_words = ("draw", "sketch", "show", "visualize", "visualise", "diagram", "map", "plot")
            ask_prompt = text
            if any(word in text.lower() for word in visual_words):
                ask_prompt += (
                    "\n\nSYSTEM VISUAL REQUEST: use the Signal Field for this answer. "
                    "Include one valid [[SIGNAL]] block after the prose; prefer semantic geometry primitives."
                )
            self.oracle.ask("ask", ask_prompt, history)
        else:
            self.work_log.append(("you", text))
            self.work_history.append({"role":"user","content":text})
            self.work_pending_user = text

            history = list(self.work_history)
            memory_packet = self.memory.context_packet()
            if memory_packet:
                history = [{
                    "role": "system",
                    "content": (
                        "Background context remembered from earlier conversations follows. Use it "
                        "naturally when relevant. Do not mention memory, slots, stored context, retrieval, "
                        "or where this information came from unless the operator explicitly asks about "
                        "the memory system. If current input conflicts with remembered context, prefer "
                        "the current input.\n\n" +
                        memory_packet
                    ),
                }] + history

            if history and history[-1].get("role") == "user" and history[-1].get("content") == text:
                history = history[:-1]
            visual_words = ("draw", "sketch", "show", "visualize", "visualise", "diagram", "map", "plot")
            work_prompt = text
            if any(word in text.lower() for word in visual_words):
                work_prompt += (
                    "\n\nSYSTEM VISUAL REQUEST: use the Signal Field for this answer. "
                    "Include one valid [[SIGNAL]] block after the prose; prefer semantic geometry primitives."
                )
            self.oracle.ask("work", work_prompt, history)

    def box(self, title, lines, width, height, color=GREEN):
        inner = max(1, width - 4)
        out = [color + "┌─ " + title + " " + "─" * max(0, width - len(strip_ansi(title)) - 5) + "┐" + RESET]
        body = list(lines)[:height - 2]
        for line in body:
            out.append(color + "│ " + RESET + fit(line, inner) + color + " │" + RESET)
        for _ in range(height - 2 - len(body)):
            out.append(color + "│ " + RESET + " " * inner + color + " │" + RESET)
        out.append(color + "└" + "─" * (width - 2) + "┘" + RESET)
        return out

    def render(self):
        physical_w, h = self.term.size()
        # Never paint the terminal's final physical column. Many terminals
        # auto-wrap when that column is touched, which creates phantom duplicate
        # rows/boxes on the next line.
        w = max(71, physical_w - 1)
        h = max(22, h)
        if self.mode == "ambient":
            return self.render_ambient(w, h)
        if self.mode == "ask":
            return self.render_input(w, h, "ASK THE ORACLE", "quick / disposable / host actions require permission")
        if self.mode == "answer":
            return self.render_answer(w, h)
        if self.mode == "quit":
            return self.render_quit(w, h)
        if self.mode == "tool_approval":
            return self.render_tool_approval(w, h)
        if self.mode == "threads":
            return self.render_threads(w, h)
        if self.mode == "help":
            return self.render_help(w, h)
        if self.mode == "memory_clear":
            return self.render_memory_clear(w, h)
        return self.render_work(w, h)

    def render_ambient(self, w, h):
        s = self.telemetry.snapshot()
        clock = time.strftime("%H:%M:%S")
        date = time.strftime("%Y-%m-%d")
        model = self.args.model
        status = GREEN + "READY" + RESET if self.online else RED + "OFFLINE" + RESET

        # The clock is intentionally the first thing in the upper-left.
        # Future Crash is an ambient machine before it is an assistant.
        left_header = BOLD + CYAN + clock + RESET + DIM + "  " + date + RESET
        center_header = BOLD + GREEN + "  FUTURE CRASH" + RESET + GREEN2 + f" // ZERO {VERSION}" + RESET
        right_header = DIM + model + RESET
        occupied = len(clock) + 2 + len(date) + 2 + len(f"FUTURE CRASH // ZERO {VERSION}") + len(model)
        header = left_header + center_header + (" " * max(1, w - occupied)) + right_header

        left_w = max(33, int(w * .42))
        right_w = w - left_w - 3

        menu_items = [
            "[esc] shell", "[a] ask", "[x] workstation", "[t] threads",
            "[f] fortune", "[r] observe", "[s] signal", "[d] demo",
            "[m] mute", "[?] help", "[p] panic", "[q] quit",
        ]
        menu_rows = wrap_menu(menu_items, w)

        # Fortune is part of the ambient composition, not a clipped status line.
        # Wrap the complete text first, then reserve exactly those rows below
        # the main panels. Three rows is a comfortable practical ceiling.
        fortune_text = "FORTUNE // " + self.fortune
        fortune_rows = wrap(fortune_text, max(24, w - 2))[:3]

        # Header/spacing/fortune/menu all consume rows outside the two main panels.
        panel_h = max(10, h - (6 + len(fortune_rows) + len(menu_rows)))

        mins = int(s.uptime // 60)
        d, mins = divmod(mins, 1440)
        hrs, mins = divmod(mins, 60)

        left_lines = [
            DIM + "MACHINE" + RESET,
            f"CPU   {GREEN}{s.cpu*100:5.1f}%{RESET}  {GREEN2}{spark(s.cpu_hist, left_w-20)}{RESET}",
            f"MEM   {CYAN}{s.mem*100:5.1f}%{RESET}  {CYAN}{spark(s.mem_hist, left_w-20)}{RESET}",
            f"NET   {AMBER}↓{bytes_text(s.net_rx)}/s ↑{bytes_text(s.net_tx)}/s{RESET}",
            f"DISK  {s.disk*100:5.1f}%   LOAD {s.load:.2f}",
            f"UP    {d}d {hrs:02d}h {mins:02d}m",
            "",
            DIM + "ORACLE" + RESET,
            f"LINK       {status}",
            f"MODEL      {WHITE}{model}{RESET}",
            f"AUTHORITY  {GREEN}{self.host.status()}{RESET}",
            f"FILES      {GREEN}AVAILABLE / ASK{RESET}",
            f"WEB        {(GREEN if self.host.web_ready else AMBER)}{self.host.web_status}{RESET}",
            f"LOOK       {(GREEN if self.look_path else DARK)}{'READY' if self.look_path else 'OPTIONAL'}{RESET}",
            f"THREADS    {CYAN}{self.threads.active_count()} ACTIVE{RESET}",
            f"AUDIO      {CYAN}{self.audio.status}{RESET}",
        ]

        signal_title = "SIGNAL FIELD"
        if self.signal.active():
            signal_title += " // CANVAS ACTIVE"
            if self.signal.owner:
                signal_title += " // " + str(self.signal.owner)[:9]
            if self.signal.title:
                signal_title += " // " + self.signal.title
        right_lines = [DIM + signal_title + RESET]
        rain_w = max(10, right_w - 6)
        rain_h = max(5, panel_h - 9)
        overlay = self.signal.sample(rain_w, rain_h) if self.signal.active() else None
        for row in range(rain_h):
            chars = []
            for col in range(rain_w):
                painted = overlay[row][col] if overlay else None
                if painted is not None:
                    ch, color_name = painted
                    chars.append(SignalCanvas.COLORS.get(color_name, CYAN) + ch + RESET)
                    continue
                idx = col % len(self.rain)
                delta = (self.rain[idx] - row) % 32
                if delta == 0:
                    chars.append(CYAN + self.rng.choice(GLYPHS) + RESET)
                elif delta < 4:
                    chars.append(GREEN + self.rng.choice(GLYPHS) + RESET)
                elif delta < 8 and self.rng.random() < .25:
                    chars.append(GREEN2 + self.rng.choice("01") + RESET)
                else:
                    chars.append(" ")
            right_lines.append("".join(chars))

        right_lines += [
            "",
            AMBER + "ORACLE OBSERVATION" + RESET,
        ]
        right_lines += wrap(self.observation, max(10, right_w - 4))[:2]

        left_box = self.box("TELEMETRY", left_lines, left_w, panel_h, GREEN2)
        right_box = self.box("SIGNAL", right_lines, right_w, panel_h, CYAN)

        rows = [header, ""]
        for i in range(panel_h):
            rows.append(left_box[i] + "   " + right_box[i])

        rows.append("")
        for i, fortune_row in enumerate(fortune_rows):
            # First row carries the label from fortune_text; wrapped continuation
            # rows line up naturally underneath it.
            rows.append(fit(GREEN2 + fortune_row + RESET, w))
        for menu_row in menu_rows:
            rows.append(DIM + menu_row + RESET)

        if self.incident:
            phase = int(time.time() * 15) % 8
            if self.incident == "signal_loss":
                row = max(3, len(rows)//2)
                rows[row] = fit(WHITE + BOLD + " NO SIGNAL // REACQUIRING LOCAL REALITY ".center(w, "░") + RESET, w)
            elif self.incident == "memory_leak_theater":
                for n in range(5):
                    row = 3 + n
                    if row < len(rows):
                        rows[row] = fit(RED + f"MEMORY {117+n*83:03d}%  THIS IS FINE" + RESET, w)
            elif self.incident == "cursor_echo":
                row = max(3, len(rows)//2)
                rows[row] = fit(MAGENTA + ("_" * (8 + phase*3)).center(w) + RESET, w)
            elif self.incident == "static_infiltration":
                for row in range(3, min(len(rows)-2, 8)):
                    noise = "".join(self.rng.choice(" .:░▒▓#") for _ in range(max(8, w//3)))
                    rows[row] = fit(DARK + noise + RESET, w)
            else:
                for row in range(3, min(len(rows)-2, 3+phase)):
                    plain = strip_ansi(rows[row])
                    if plain:
                        shift = (phase + row) % max(1, min(16, len(plain)))
                        rows[row] = fit((MAGENTA if row % 2 else RED) + plain[shift:] + plain[:shift] + RESET, w)

        if self.event:
            title, body = self.event
            center = max(4, len(rows)//2 - 1)
            if center < len(rows):
                rows[center] = fit(AMBER + BOLD + (" " + title + " ").center(w, "─") + RESET, w)
            if center + 1 < len(rows):
                rows[center+1] = fit(WHITE + body.center(w) + RESET, w)

        if time.time() < self.panic_until:
            title, body = self.panic
            phase = self.panic_phase
            corruption = [
                RED + BOLD + f" !!! {title} !!! " + RESET,
                MAGENTA + body + RESET,
                AMBER + self.rng.choice([
                    "KERNEL: advisory reality mismatch",
                    "SIGNAL BUS: impossible checksum accepted",
                    "ORACLE CORE: confidence containment active",
                    "CLOCK: several milliseconds are unaccounted for",
                    "FILESYSTEM: behaving professionally under protest",
                ]) + RESET,
                RED + "RECOVERY VECTOR " + ("▓" * (phase + 2)) + ("░" * max(0, 13 - phase)) + RESET,
            ]
            center = max(3, len(rows) // 2 - 2)
            for i, line in enumerate(corruption):
                if center + i < len(rows):
                    rows[center + i] = fit(line.center(w), w)

            if phase % 2 == 0:
                for idx in range(3, min(len(rows) - 2, 3 + phase // 2)):
                    plain = strip_ansi(rows[idx])
                    if plain.strip():
                        shift = 1 + (phase % 5)
                        rows[idx] = MAGENTA + plain[shift:] + plain[:shift] + RESET

        while len(rows) < h:
            rows.append("")
        return "\n".join(safe_row(row, w) for row in rows[:h])


    def render_signal_panel(self, width, height):
        """Conversation-side view of the same persistent Signal Canvas."""
        width = max(24, width)
        height = max(6, height)
        inner_w = max(8, width - 4)
        inner_h = max(3, height - 2)
        active = self.signal.active()
        sampled = self.signal.sample(inner_w, inner_h) if active else None
        lines = []
        for y in range(inner_h):
            chars = []
            for x in range(inner_w):
                cell = sampled[y][x] if sampled else None
                if cell:
                    ch, color_name = cell
                    chars.append(SignalCanvas.COLORS.get(color_name, CYAN) + ch + RESET)
                else:
                    # A very faint living field makes the pane feel connected
                    # without obscuring model drawings.
                    chars.append(DARK + ("." if (x * 7 + y * 11) % 29 == 0 else " ") + RESET)
            lines.append("".join(chars))
        title = "SIGNAL // " + ("CANVAS ACTIVE" if active else "LISTENING")
        return self.box(title, lines, width, height, CYAN)

    def render_input(self, w, h, title, subtitle):
        usable = max(30, w - 8)
        lines = [
            "",
            BOLD + CYAN + title + RESET,
            DIM + subtitle + RESET,
            "",
        ]
        prompt = "> " + self.input
        cursor_at = 2 + self.cursor
        shown = prompt
        if len(shown) > usable:
            start = max(0, cursor_at - usable + 4)
            shown = shown[start:start + usable]
            cursor_at -= start

        lines.append(CYAN + "┌" + "─" * (usable + 2) + "┐" + RESET)
        lines.append(CYAN + "│ " + RESET + fit(shown, usable) + CYAN + " │" + RESET)
        lines.append(CYAN + "└" + "─" * (usable + 2) + "┘" + RESET)
        lines += ["", DIM + "[ENTER] send   [CTRL-U] clear   [ESC] return" + RESET]
        pad_top = max(1, (h - len(lines)) // 3)
        frame = [""] * pad_top + ["   " + x for x in lines]
        while len(frame) < h:
            frame.append("")
        return "\n".join(safe_row(row, w) for row in frame[:h])

    def render_answer(self, w, h):
        content = self.answer if self.answer else (AMBER + "ORACLE LINK SYNCHRONIZING…" + RESET)
        wide = w >= 105
        side_w = min(46, max(34, w // 3)) if wide else 0
        body_w = max(30, w - side_w - (8 if wide else 10))
        plain = strip_ansi(content)
        lines = []
        for paragraph in plain.splitlines() or [""]:
            lines.extend(wrap(paragraph, body_w))
        visible = max(5, h - 7)
        max_scroll = max(0, len(lines) - visible)
        self.scroll = min(self.scroll, max_scroll)
        shown = lines[self.scroll:self.scroll + visible]

        frame = [
            BOLD + GREEN + "FUTURE CRASH // ORACLE" + RESET + "   " + DIM + self.args.model + RESET,
            DIM + "AUTHORITY " + RESET + GREEN2 + self.host.status() + RESET +
            DIM + "   FILES " + RESET + GREEN2 + "AVAILABLE / ASK" + RESET +
            DIM + "   WEB " + RESET + (GREEN2 if self.host.web_ready else AMBER) + self.host.web_status + RESET +
            DIM + "   THREADS " + RESET + CYAN + str(self.threads.active_count()) + RESET +
            DIM + "   SIGNAL " + RESET +
            (GREEN2 + ("THREAD " + str(self.signal.owner)[:9] if self.signal.owner else "ACTIVE") + RESET
             if self.signal.active() else DARK + "IDLE" + RESET),
            "",
        ]

        if wide:
            panel = self.render_signal_panel(side_w, min(h - 5, 16))
            left_rows = ["   " + fit(x, body_w) for x in shown]
            row_count = max(len(left_rows), len(panel))
            for i in range(row_count):
                left = left_rows[i] if i < len(left_rows) else ""
                right = panel[i] if i < len(panel) else ""
                frame.append(fit(left, body_w + 3) + "  " + right)
        else:
            frame.extend("   " + x for x in shown)
            if self.signal.active() and len(frame) < h - 7:
                panel = self.render_signal_panel(min(w - 4, 54), min(10, h - len(frame) - 3))
                frame.extend("  " + row for row in panel)

        while len(frame) < h - 2:
            frame.append("")
        frame.append(DIM + "[↑/↓] scroll   [A] another question   [Q] quit   [ESC] return" + RESET)
        while len(frame) < h:
            frame.append("")
        return "\n".join(safe_row(row, w) for row in frame[:h])

    def render_work(self, w, h):
        title = BOLD + AMBER + "FUTURE CRASH // WORKSTATION" + RESET
        status = AMBER + "THINKING" + RESET if self.busy else GREEN + "READY" + RESET
        frame = [
            title + "   " + DIM + self.args.model + RESET + "   " + status,
            DIM + "persistent conversation // permissioned host operations" + RESET,
            DIM + "MEMORY " + RESET + GREEN2 + self.memory.status() + RESET +
            DIM + "   AUTHORITY " + RESET + GREEN2 + self.host.status() + RESET +
            DIM + "   FILES " + RESET + GREEN2 + "AVAILABLE / ASK" + RESET +
            DIM + "   WEB " + RESET + (GREEN2 if self.host.web_ready else AMBER) + self.host.web_status + RESET,
        ]
        if self.work_notice and time.time() < self.work_notice_until:
            frame.append(GREEN2 + self.work_notice + RESET)
        elif self.thread_notifications:
            frame.append(AMBER + "THREAD // " + self.thread_notifications[-1][:max(20, w-12)] + RESET)
        elif self.host_notice and time.time() < self.host_notice_until:
            frame.append(CYAN + self.host_notice + RESET)
        else:
            self.work_notice = ""
            frame.append("")

        wide = w >= 110
        side_w = min(46, max(36, w // 3)) if wide else 0
        text_w = max(36, w - side_w - 5) if wide else max(30, w - 4)
        body_h = max(7, h - 8)

        transcript = []
        for who, item in self.work_log[-16:]:
            if who == "you":
                tag = CYAN + "YOU" + RESET
            elif who == "host":
                tag = AMBER + "HOST" + RESET
            else:
                tag = GREEN + "ORACLE" + RESET
            transcript.append(tag)
            for line in wrap(strip_ansi(item), max(28, text_w - 4)):
                transcript.append("  " + line)
            transcript.append("")
        transcript = transcript[-body_h:]

        if wide:
            panel = self.render_signal_panel(side_w, min(body_h, 16))
            row_count = max(body_h, len(panel))
            for i in range(row_count):
                left = transcript[i] if i < len(transcript) else ""
                right = panel[i] if i < len(panel) else ""
                frame.append(fit(left, text_w) + "  " + right)
                if len(frame) >= h - 3:
                    break
        else:
            frame.extend(transcript)
            if self.signal.active() and len(frame) < h - 8:
                panel = self.render_signal_panel(min(w - 2, 50), min(8, h - len(frame) - 3))
                frame.extend(panel)

        while len(frame) < h - 3:
            frame.append("")
        prompt = "> " + self.input + ("_" if not self.busy else "")
        frame.append(fit(prompt, w - 1))
        frame.append(DIM + "[ENTER] send   [CTRL-T] threads   [CTRL-U] clear conversation   [CTRL-K] erase memory   [ESC] return" + RESET)
        while len(frame) < h:
            frame.append("")
        return "\n".join(safe_row(row, w) for row in frame[:h])

    def render_help(self, w, h):
        sections = [
            ("AMBIENT",
             [
                 ("esc", "real interactive shell; exit or Ctrl-D returns"),
                 ("a", "Quick Oracle"),
                 ("x", "Workstation"),
                 ("t", "Threads"),
                 ("f", "new fortune"),
                 ("r", "new observation"),
                 ("s", "clear Signal drawing"),
                 ("d", "Signal Canvas demo"),
                 ("m", "mute / unmute sound"),
                 ("p", "panic"),
                 ("?", "this help"),
                 ("q", "guarded quit"),
             ]),
            ("WORKSTATION",
             [
                 ("enter", "send"),
                 ("ctrl-t", "Threads"),
                 ("ctrl-u", "clear current conversation; keep persistent memory"),
                 ("ctrl-k", "guarded persistent-memory erase"),
                 ("esc", "return to Ambient"),
             ]),
            ("THREADS",
             [
                 ("enter", "details"),
                 ("j/k or arrows", "select"),
                 ("p", "pause selected Thread"),
                 ("r", "resume selected Thread"),
                 ("x", "cancel selected Thread"),
                 ("esc", "return"),
             ]),
            ("CONCEPTS",
             [
                 ("MEMORY", "one rolling long memory + five recent Workstation exchanges"),
                 ("WEB", "Ollama hosted web search when OLLAMA_API_KEY is available"),
                 ("FILES", "permissioned host actions with verified HOST RECEIPTS"),
                 ("SIGNAL", "shared model-controlled drawing/status surface"),
                 ("MODEL WAKE", "model-only recurring Thread action for Signal art, notes, moods, etc."),
                 ("LOOK", "optional separate project; detected if `lk` is already on PATH"),
             ]),
        ]

        body = []
        for title, items in sections:
            body.append(AMBER + title + RESET)
            for key, desc in items:
                body.append(fit(f"  {key:<15}{desc}", w - 1))
            body.append("")

        header_rows = 3
        footer_rows = 2
        visible = max(4, h - header_rows - footer_rows)

        max_scroll = max(0, len(body) - visible)
        self.help_scroll = max(0, min(self.help_scroll, max_scroll))
        shown = body[self.help_scroll:self.help_scroll + visible]

        frame = [
            BOLD + CYAN + f"FUTURE CRASH // HELP // {VERSION}" + RESET,
            DIM + "canonical command reference" + RESET,
            "",
        ]
        frame.extend(shown)

        while len(frame) < h - 2:
            frame.append("")

        if max_scroll:
            start_line = self.help_scroll + 1
            end_line = min(len(body), self.help_scroll + visible)
            pos = f"{start_line}-{end_line}/{len(body)}"
            controls = f"[↑/↓ j/k] scroll   [pgup/pgdn or space] page   [home/g] top   [esc/?/h/q] return   {pos}"
        else:
            controls = "[esc / ? / h / q] return"

        frame.append(DIM + fit(controls, w - 1) + RESET)
        while len(frame) < h:
            frame.append("")
        return "\n".join(safe_row(row, w) for row in frame[:h])

    def render_threads(self, w, h):
        tasks = [t for t in self.threads.tasks if t.get("state") != "cancelled"]
        self.thread_selected = min(self.thread_selected, max(0, len(tasks) - 1))
        frame = [
            BOLD + CYAN + "FUTURE CRASH // THREADS" + RESET,
            DIM + "persistent internal scheduler // exact approved actions // one wake at a time" + RESET,
            "",
        ]

        if not tasks:
            frame += [
                DIM + "No Threads are currently defined." + RESET,
                "",
                "Ask the Oracle something like:",
                GREEN2 + '  "Every 10 minutes, search the web for changes to flight UA1734."' + RESET,
            ]
        else:
            now = time.time()
            header = f"{'':2} {'ID':9} {'STATE':8} {'EVERY':6} {'NEXT':10} {'RUNS':5} TITLE"
            frame.append(DIM + header + RESET)
            frame.append(DIM + "─" * min(w - 1, 88) + RESET)
            for i, task in enumerate(tasks[:18]):
                selected = i == self.thread_selected
                marker = "▶" if selected else " "
                state = str(task.get("state", "?")).upper()
                row = (
                    f"{marker} {task.get('id','')[:9]:9} {state:8} "
                    f"{ThreadStore.interval_text(task.get('every_seconds',300)):6} "
                    f"{ThreadStore.countdown_text(task, now):10} "
                    f"{int(task.get('runs',0)):5} "
                    f"{task.get('title','')[:max(10, w-50)]}"
                )
                frame.append((WHITE + BOLD if selected else GREEN2) + fit(row, w - 1) + RESET)

            task = tasks[self.thread_selected]
            frame += ["", AMBER + "PURPOSE" + RESET]
            frame += ["  " + x for x in wrap(str(task.get("purpose", "")), max(30, w - 6))[:3]]

            last_run = task.get("last_run")
            last_clock = time.strftime("%H:%M:%S", time.localtime(last_run)) if last_run else "NEVER"
            changed = task.get("last_changed")
            change_text = "CHANGED" if changed is True else ("QUIET" if changed is False else "UNKNOWN")
            frame += [
                "",
                AMBER + "LAST RUN" + RESET +
                f"  {last_clock}   {task.get('last_result','NOT RUN')}   {change_text}   RUN #{int(task.get('runs',0))}",
                AMBER + "LAST" + RESET + "      " +
                (str(task.get("last_summary", ""))[:max(20, w - 14)] or "(not interpreted yet)"),
                AMBER + "SIGNAL" + RESET + "    " +
                ("OWNED / PERSISTENT" if self.signal.owner == task.get("id") and self.signal.active() else "—"),
            ]

            if self.thread_detail:
                action = json.dumps(task.get("action", {}), ensure_ascii=False)
                receipt = " ".join(str(task.get("last_receipt", "")).split())
                frame += [
                    "",
                    CYAN + "ACTION" + RESET,
                ]
                frame += ["  " + x for x in wrap(action, max(30, w - 6))[:3]]
                frame += [CYAN + "LAST RECEIPT" + RESET]
                frame += ["  " + x for x in wrap(receipt or "(none)", max(30, w - 6))[:3]]

        while len(frame) < h - 3:
            frame.append("")
        frame.append(DIM + "[ENTER] details   [J/K or ↑/↓] select   [P] pause   [R] resume   [X] cancel   [ESC] return" + RESET)
        while len(frame) < h:
            frame.append("")
        return "\n".join(safe_row(row, w) for row in frame[:h])

    def render_tool_approval(self, w, h):
        request = self.pending_tool or {"name": "unknown"}
        capability = self.host.capability(request)
        description = self.host.describe(request)
        box_w = min(82, max(54, w - 10))
        lines = [
            "",
            AMBER + BOLD + (
                "ORACLE REQUESTS THREAD CHANGE"
                if request.get("name") == "thread_update"
                else "ORACLE REQUESTS HOST ACCESS"
            ) + RESET,
            "",
            "CAPABILITY  " + WHITE + capability + RESET,
            "",
        ]
        lines.extend(wrap(description, box_w - 8)[:5])
        lines += [
            "",
            DIM + "The model proposed this. Python has not performed it yet." + RESET,
            DIM + "A HOST RECEIPT will verify success or failure afterward." + RESET,
            "",
            BOLD + "[Y / ENTER] ALLOW ONCE" + RESET,
        ]
        if capability == "TASK AUTHORITY":
            lines.append(DIM + "[S] same as Y // this exact Thread is the persistent permission" + RESET)
        elif capability == "RUN COMMANDS":
            lines.append(DIM + "[S] same as once for commands (never persistent)" + RESET)
        else:
            lines.append(BOLD + "[S] ALLOW THIS CAPABILITY FOR SESSION" + RESET)
        lines += [
            RED + "[N / ESC] DENY" + RESET,
        ]
        boxed = self.box("HOST INTERLOCK", lines, box_w, min(h - 2, 19), AMBER)
        left = max(0, (w - box_w) // 2)
        top = max(0, (h - len(boxed)) // 2)
        frame = [""] * top
        frame.extend((" " * left) + row for row in boxed)
        while len(frame) < h:
            frame.append("")
        return "\n".join(safe_row(row, w) for row in frame[:h])

    def render_memory_clear(self, w, h):
        box_w = min(68, max(48, w - 12))
        lines = [
            "",
            RED + BOLD + "PERSISTENT MEMORY ERASE" + RESET,
            "",
            "This deletes the rolling long memory and all recent memory slots.",
            "The current Workstation transcript is not the same thing.",
            "",
            AMBER + "Erase persistent Future Crash memory?" + RESET,
            "",
            BOLD + "[Y] ERASE MEMORY" + RESET,
            DIM + "[N / ESC] KEEP MEMORY" + RESET,
        ]
        boxed = self.box("MEMORY INTERLOCK", lines, box_w, min(h - 4, 16), RED)
        left = max(0, (w - box_w) // 2)
        top = max(0, (h - len(boxed)) // 2)
        frame = [""] * top
        frame.extend((" " * left) + line for line in boxed)
        while len(frame) < h:
            frame.append("")
        return "\n".join(safe_row(row, w) for row in frame[:h])

    def render_quit(self, w, h):
        box_w = min(64, max(44, w - 12))
        lines = [
            "",
            RED + BOLD + "SHUTDOWN REQUEST" + RESET,
            "",
            "Future Crash is still running.",
            DIM + "esc from Ambient opens a real shell without quitting." + RESET,
            "No emergency has been detected.",
            "",
            AMBER + "Terminate the workstation anyway?" + RESET,
            "",
            BOLD + "[Y / ENTER] SHUT DOWN" + RESET,
            DIM + "[N / ESC] RETURN SAFELY" + RESET,
        ]
        boxed = self.box("SYSTEM INTERLOCK", lines, box_w, min(h - 4, 16), RED)
        left = max(0, (w - box_w) // 2)
        top = max(0, (h - len(boxed)) // 2)
        frame = [""] * top
        frame.extend((" " * left) + line for line in boxed)
        while len(frame) < h:
            frame.append("")
        return "\n".join(safe_row(row, w) for row in frame[:h])

# ---------- CLI ----------

def parse_args():
    p = argparse.ArgumentParser(
        description="Future Crash // Zero — local AI workstation / ambient terminal",
        epilog="Ambient: esc shell · a ask · x workstation · t threads · m mute · ? help · q quit",
    )
    p.add_argument("--version", action="version", version=f"Future Crash {VERSION}")
    p.add_argument("--model", default="qwen3:4b", help="Ollama model to use for ALL AI work")
    p.add_argument("--ollama", default="http://127.0.0.1:11434", help="Ollama base URL")
    p.add_argument("--fps", type=int, default=12, help="UI refresh rate (default: 12)")
    p.add_argument("--no-ai-ambient", action="store_true", help="disable ambient LLM observations")
    p.add_argument("--no-audio", action="store_true", help="disable synthesized terminal sounds for this launch (overrides saved audio preference)")
    return p.parse_args()

if __name__ == "__main__":
    if os.name != "posix":
        print("Future Crash Zero currently targets macOS and Linux terminals.")
        raise SystemExit(1)
    args = parse_args()
    app = FutureCrash(args)
    try:
        app.start()
    except KeyboardInterrupt:
        pass
