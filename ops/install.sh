#!/usr/bin/env bash
# tbilisi.today Shorts: set up the render environment on the agent server (84.46.250.149).
# Run by the owner from the monorepo checkout:  bash video/ops/install.sh [--align]
# Idempotent. It installs no secrets and enables no timers: data/.env and the systemd timer (phase 1) are
# separate, owner-approved steps.
set -euo pipefail
umask 022
cd "$(dirname -- "${BASH_SOURCE[0]}")/.."
VIDEO="$(pwd -P)"
command -v ffmpeg >/dev/null || { echo "ffmpeg is missing: apt-get install -y ffmpeg" >&2; exit 1; }
python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' || { echo "python 3.11+ required" >&2; exit 1; }

python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
.venv/bin/python -m playwright install chromium-headless-shell  # frames; system libs: playwright install-deps

if [[ "${1:-}" == "--align" ]]; then  # Georgian word timings for the Gemini voice (~2 GB with CPU torch)
  python3 -m venv .venv-align
  .venv-align/bin/pip install -q --upgrade pip
  .venv-align/bin/pip install -q -r requirements-align.txt
fi

if ! ls assets/music/*.m4a >/dev/null 2>&1; then  # deterministic loops, ours outright: ~6 min on 4 cores
  .venv/bin/python tools/compose_music.py
fi

install -d -m 700 data
[[ -f data/.env ]] || install -m 600 ops/env.example data/.env

.venv/bin/python -m unittest discover -s tests
echo "ok: $VIDEO  (render a preview: .venv/bin/python -m tt_shorts.render stories/24835.json --theme A --silent)"
