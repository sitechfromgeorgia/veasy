"""Kaeasy inside the engine: SiTech's Georgian writing plugin (github.com/sitechfromgeorgia/kaeasy), used as a gate.

The videos go out without a human review, so the Georgian check can't depend on an agent remembering to load a
skill. The engine loads kaeasy's deterministic linter and its shared mistakes memory straight from the plugin folder
every agent on the server already uses (KAEASY_DIR), so a rule added to kaeasy reaches the videos with no copy here.

  narration          -> lint mode "article"
  on-screen text     -> lint mode "social"
  the spoken text    -> lint mode "speech" (after normalize_ka: numbers in words, brands in Georgian letters)

Blocking: kaeasy's STRICT rules (near-zero false positives) plus the rules ka_check maps to its K numbers.
Everything else is a warning. Before writing, the writer model gets kaeasy's ten most-broken rules and the fleet's
most frequent mistakes; after an editor pass, the phrases it changed go back into the shared memory.

When kaeasy isn't installed, nothing breaks: the checks run without it and `engine doctor` says so. On the server set
SHORTS_REQUIRE_KAEASY=1, so a render refuses to run without it.
"""
import difflib
import importlib.util
import os
import pathlib
import re
import sys

DEFAULT_DIR = "/root/.hermes/shared-plugins/kaeasy"
AGENT = "tt-shorts"
_mods = {}


def directory():
    return pathlib.Path(os.environ.get("KAEASY_DIR", DEFAULT_DIR))


def _load(name):
    """kaeasy's lint.py or memory.py as a module, or None. Cached; a broken file must not stop the videos."""
    if name in _mods:
        return _mods[name]
    path = directory() / f"{name}.py"
    mod = None
    if path.exists():
        try:
            spec = importlib.util.spec_from_file_location(f"kaeasy_{name}", path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[f"kaeasy_{name}"] = mod
            spec.loader.exec_module(mod)
        except Exception as e:  # noqa: BLE001
            print(f"kaeasy: {path} failed to load: {e}", file=sys.stderr)
            mod = None
    _mods[name] = mod
    return mod


def reset():
    """Forget the loaded modules (tests, or after KAEASY_DIR changes)."""
    _mods.clear()


def available():
    return _load("lint") is not None


def version():
    """'0.1.0+b7cca49' (plugin.yaml version + git commit when the folder is a clone), or None when missing."""
    if not available():
        return None
    d = directory()
    v = "unknown"
    try:
        m = re.search(r"^version:\s*(\S+)", (d / "plugin.yaml").read_text(encoding="utf-8"), re.M)
        v = m.group(1) if m else v
    except OSError:
        pass
    try:
        head = (d / ".git" / "HEAD").read_text(encoding="utf-8").strip()
        sha = (d / ".git" / head[5:]).read_text(encoding="utf-8").strip() if head.startswith("ref: ") else head
        v += f"+{sha[:7]}"
    except OSError:
        pass
    return v


def strict_rules():
    lint = _load("lint")
    return set(getattr(lint, "STRICT", ())) if lint else set()


def check(text, mode):
    """kaeasy findings for one text as dicts {check, severity, message, snippet}; [] when kaeasy is missing."""
    lint = _load("lint")
    if not lint or not (text or "").strip():
        return []
    try:
        return [f.as_dict() if hasattr(f, "as_dict") else dict(f) for f in lint.check_text(text, mode=mode)]
    except Exception as e:  # noqa: BLE001
        print(f"kaeasy: check_text failed ({mode}): {e}", file=sys.stderr)
        return []


def ten_rules():
    """The 'ten rules broken most often' section of kaeasy's georgian-writing skill, or ''."""
    path = directory() / "skills" / "georgian-writing" / "SKILL.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    m = re.search(r"^## The ten rules broken most often\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else ""


def mistakes(limit=15):
    """The fleet's most frequent Georgian mistakes as '- ❌ … → ✅ …' lines, or ''."""
    mem = _load("memory")
    if not mem:
        return ""
    try:
        rows = mem.top(limit)
        return mem.as_markdown(rows) if rows else ""
    except Exception as e:  # noqa: BLE001
        print(f"kaeasy: memory read failed: {e}", file=sys.stderr)
        return ""


def prompt_block(limit=15):
    """What the writer model reads before writing (free: no model call, no network)."""
    parts = []
    rules = ten_rules()
    if rules:
        parts.append("Georgian: the ten rules broken most often (kaeasy):\n" + rules)
    seen = mistakes(limit)
    if seen and not seen.startswith("ჯერ"):
        parts.append("Georgian mistakes other SiTech agents made before (avoid them):\n" + seen)
    return "\n\n".join(parts)


def changed_phrases(before, after, max_words=5, limit=5):
    """Short (wrong, right) phrase pairs an edit made, word by word; long rewrites are skipped (not a lesson)."""
    a, b = before.split(), after.split()
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op != "replace":
            continue
        if not (0 < i2 - i1 <= max_words and 0 < j2 - j1 <= max_words):
            continue
        strip = lambda ws: " ".join(ws).strip(".,:;!?„“\"")  # noqa: E731
        wrong, right = strip(a[i1:i2]), strip(b[j1:j2])
        if wrong and right and wrong != right and re.search(r"[ა-ჰ]", wrong + right):
            out.append((wrong, right))
        if len(out) >= limit:
            break
    return out


def learn_edit(before, after, reason="ვიდეოს სცენარის რედაქტორის ჩასწორება"):
    """Record an editor pass's phrase fixes in kaeasy's shared memory. Off with SHORTS_KAEASY_LEARN=0."""
    mem = _load("memory")
    if not mem or os.environ.get("SHORTS_KAEASY_LEARN", "1") == "0":
        return []
    saved = []
    for wrong, right in changed_phrases(before, after):
        try:
            saved.append(mem.learn(wrong, right, reason=reason, category="style", agent=AGENT))
        except Exception as e:  # noqa: BLE001
            print(f"kaeasy: learn failed: {e}", file=sys.stderr)
    return saved
