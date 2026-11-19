"""One reader for the daily corpus review, with the model named in one place.

The owner installed antigravity (`agy`) on 2026-11-18 with Gemini 3.8 Flash on his subscription, and
asked for it to be used for the daily language review: "gemini 3.8 flash მოდელი მაქვს ჩართული რაც
ყელამდე გეყოფა ყველაფერში და ჭკვიანურად გამოვიყენოთ".

Measured on this host: `agy -p ... --model gemini-3.8-flash-high` answers a Georgian JSON question in
about 35 s for about 28k tokens, and caught "მოქცევარი" and "პატროლმა" the same way the writer model
did. It runs headless, so it can be a function.

Two backends, one contract: a prompt in, a string out. The corpus review and the per-story reader both
call `ask()` and never care which one answered. `TT_READER=agy|writer` selects, defaulting to agy when
the binary is present, because it is the owner's own subscription and the writer's free tier is the
scarcer resource.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess

AGY = os.environ.get("TT_AGY_BIN") or "/root/.local/bin/agy"
DEFAULT_MODEL = os.environ.get("TT_READER_MODEL") or "gemini-3.8-flash-high"
TIMEOUT = int(os.environ.get("TT_READER_TIMEOUT", "240"))


def available() -> bool:
    """Is the antigravity CLI installed and runnable?"""
    return bool(AGY and pathlib.Path(AGY).exists() and os.access(AGY, os.X_OK))


def backend() -> str:
    """agy when the owner's CLI is there, writer otherwise. Explicit override wins."""
    chosen = (os.environ.get("TT_READER") or "").strip().lower()
    if chosen in ("agy", "writer"):
        return chosen
    return "agy" if available() else "writer"


def ask(prompt: str, *, model: str | None = None, max_tokens: int = 1500, json_out: bool = False) -> str:
    """One question, one answer, whichever backend is configured.

    json_out asks agy for its own JSON envelope so the answer can be read out of `response` rather than
    out of a terminal transcript; the text returned is always the model's answer and never the envelope.

    A `model` names an agy model (gemini-4-neon-high, claude-opus-5-5-high). It must NOT be forwarded to
    the writer fallback: the writer serves its own ids and answers 404 for an agy name (measured
    2026-11-19: a review that asked for gemini-4-neon-high lost all five chunks this way, while the
    caller reported a clean '0 pairs found'). The fallback runs on the writer's own model.
    """
    if backend() == "agy":
        answer = _agy(prompt, model=model, json_out=json_out)
        if answer:
            return answer
        # An agy that answered nothing (a permission denial, a killed run) must not silently become an
        # empty answer: fall through to the writer model, which is slower but always present.
    from tt_shorts import writer
    return writer._call(prompt, writer.MODEL, max_tokens=max_tokens)


def _agy(prompt: str, *, model: str | None = None, json_out: bool = False) -> str:
    """Run `agy -p`. Empty string on any failure: the caller decides what a failure means."""
    if not available():
        return ""
    cmd = [AGY, "-p", prompt, "--model", model or DEFAULT_MODEL,
           # Headless mode cannot answer a permission prompt, so any tool request is auto-denied and the
           # run returns nothing. This flag is required for a batch reader; the process runs as root on
           # the owner's own host inside a call we construct, with no repository or network target we did
           # not choose. Measured 2026-11-18: without it, every call returned an empty response.
           "--dangerously-skip-permissions"]
    if json_out:
        cmd += ["--output-format", "json"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, encoding="utf-8")
    except (subprocess.TimeoutExpired, OSError):
        return ""
    if json_out:
        for line in (p.stdout or "").splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                env = json.loads(line)
            except ValueError:
                continue
            if isinstance(env, dict) and "response" in env:
                return str(env.get("response") or "").strip()
        return ""
    return (p.stdout or "").strip()


def status() -> dict:
    """What the reader is and whether it works, for a health line."""
    return {"backend": backend(), "agy_present": available(), "model": DEFAULT_MODEL,
            "timeout_s": TIMEOUT}
