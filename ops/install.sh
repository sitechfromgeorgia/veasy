#!/usr/bin/env bash
# Veasy: set up the render environment on the agent server (84.46.250.149).
# Run by the owner from the Veasy checkout:  bash ops/install.sh [--align]
# Idempotent. It installs no secrets and enables no timers: data/.env and the systemd timer (phase 1) are
# separate, owner-approved steps.
#
#   bash ops/install.sh --skills (--target DIR | --profile NAME) [--dry-run]
# installs only the two engines' own agent skills, pinned, into an agent's skills folder (docs/plan-v2.md § 3):
#   Remotion's (remotion-dev/skills at REMOTION_SKILLS_SHA, through `npx skills@SKILLS_CLI add`; the repo has no
#   licence file, so Veasy never copies them into its own tree) and HyperFrames' core skills (hyperframes,
#   hyperframes-cli) from the pinned npm package in compose/ (Apache-2.0). media-use is left out: it can call
#   HeyGen's paid APIs, and Veasy's media layer does that job. --profile NAME targets a Hermes profile's folder,
#   ${HERMES_HOME:-$HOME/.hermes}/profiles/NAME/skills; --target any folder (a test, Claude Code's .claude/skills).
#   A manifest, veasy-engine-skills.json, records what was installed at which pin. Nothing is installed globally.
set -euo pipefail
umask 022
cd "$(dirname -- "${BASH_SOURCE[0]}")/.."
VIDEO="$(pwd -P)"

REMOTION_SKILLS_SHA="c7cb2fdcacd134fb2ccb9b7a44f9ffa44e467271"  # remotion-dev/skills, 2026-11-03 ("Update template")
SKILLS_CLI="1.7.6"                                               # vercel-labs/skills, the `npx skills` installer
HF_SKILLS=(hyperframes hyperframes-cli)                          # from compose/node_modules/hyperframes/dist/skills
HF_LEFT_OUT=(media-use)

if [[ "${1:-}" == "--skills" ]]; then
  shift
  TARGET="" DRY=0
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --target) TARGET="$2"; shift 2 ;;
      --profile) TARGET="${HERMES_HOME:-$HOME/.hermes}/profiles/$2/skills"; shift 2 ;;
      --dry-run) DRY=1; shift ;;
      *) echo "unknown option $1 (--target DIR | --profile NAME, --dry-run)" >&2; exit 2 ;;
    esac
  done
  [[ -n "$TARGET" ]] || { echo "say where: --target DIR or --profile NAME (a Hermes profile)" >&2; exit 2; }
  run() { echo "+ $*"; [[ $DRY == 1 ]] || "$@"; }
  export DISABLE_TELEMETRY=1 DO_NOT_TRACK=1 HYPERFRAMES_NO_TELEMETRY=1 HYPERFRAMES_NO_UPDATE_CHECK=1 \
         HYPERFRAMES_SKIP_SKILLS=1 HYPERFRAMES_NO_AUTO_INSTALL=1
  run mkdir -p "$TARGET"
  # Remotion's skills: the skills CLI installs into <cwd>/.hermes/skills (agent hermes-agent, project scope);
  # done in a scratch folder and moved, so no agent's global folder is touched
  WORK="$(mktemp -d)"
  trap 'rm -rf "$WORK"' EXIT
  (cd "$WORK" && run npx --yes "skills@$SKILLS_CLI" add \
     "https://github.com/remotion-dev/skills/tree/$REMOTION_SKILLS_SHA/skills" -a hermes-agent --skill '*' --copy -y)
  if [[ $DRY == 0 ]]; then
    found=0
    for d in "$WORK"/.hermes/skills/remotion-*; do
      [[ -f "$d/SKILL.md" ]] || continue
      rm -rf "$TARGET/$(basename "$d")"; cp -R "$d" "$TARGET/"; found=$((found + 1))
    done
    [[ $found -gt 0 ]] || { echo "no Remotion skill was installed (see the output above)" >&2; exit 1; }
  fi
  # HyperFrames' core skills from the pinned package (compose/package.json), media-use left out
  [[ -d compose/node_modules/hyperframes ]] || run bash -c "cd compose && npm ci --no-audit --no-fund"
  for s in "${HF_SKILLS[@]}"; do
    run rm -rf "$TARGET/$s"
    run cp -R "compose/node_modules/hyperframes/dist/skills/$s" "$TARGET/$s"
  done
  for s in "${HF_LEFT_OUT[@]}"; do run rm -rf "$TARGET/$s"; done
  HF_VERSION="$(node -p "require('./compose/package.json').dependencies.hyperframes")"
  if [[ $DRY == 0 ]]; then
    cat > "$TARGET/veasy-engine-skills.json" <<JSON
{"about": "Installed by Veasy's ops/install.sh --skills: the two film engines' own skills, pinned. Veasy's skills (veasy:make-video, veasy:compose) say which wins where they overlap: captions are Veasy's captions.py, media is Veasy's media layer (never media-use), HyperFrames runs only through engine compose (no publish, cloud, lambda, tts, feedback, add).",
 "remotion": {"repo": "remotion-dev/skills", "commit": "$REMOTION_SKILLS_SHA", "installer": "skills@$SKILLS_CLI", "copied_into_veasy": false},
 "hyperframes": {"package": "hyperframes@$HF_VERSION", "skills": ["${HF_SKILLS[0]}", "${HF_SKILLS[1]}"], "left_out": ["${HF_LEFT_OUT[0]}"]}}
JSON
  fi
  echo "ok: the engines' skills in $TARGET"
  exit 0
fi

command -v ffmpeg >/dev/null || { echo "ffmpeg is missing: apt-get install -y ffmpeg" >&2; exit 1; }
command -v npm >/dev/null || { echo "Node.js 20+ is missing (Remotion)" >&2; exit 1; }
python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' || { echo "python 3.11+ required" >&2; exit 1; }

python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

(cd remotion && npm ci --no-audit --no-fund && npx remotion browser ensure)  # frames: Remotion + chrome-headless-shell
# the second engine, HyperFrames (pinned in compose/package.json), with telemetry and update checks off
(cd compose && npm ci --no-audit --no-fund && HYPERFRAMES_NO_TELEMETRY=1 DO_NOT_TRACK=1 HYPERFRAMES_NO_UPDATE_CHECK=1 \
  HYPERFRAMES_SKIP_SKILLS=1 HYPERFRAMES_NO_AUTO_INSTALL=1 node node_modules/hyperframes/bin/hyperframes.mjs browser ensure)

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
(cd remotion && npx tsc --noEmit)
echo "ok: $VIDEO  (preview: .venv/bin/python -m tt_shorts.props stories/24835.json --variant editorial)"
