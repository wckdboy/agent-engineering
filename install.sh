#!/bin/sh
# Install or upgrade the portable eng kit into a repository.
set -eu

SELF=$(cd -- "$(dirname -- "$0")" && pwd)
TARGET=""
HOOKS=0
CI=0
FORCE=0

usage() {
  cat <<'EOF'
usage: install.sh --target <repo> [--hooks] [--ci] [--force]

  --target <repo>  repository to install into (required)
  --hooks          set core.hooksPath to .agents/hooks
  --ci             install the standalone GitHub Actions workflow
  --force          overwrite an existing config and kit-owned config files

The installer never overwrites AGENTS.md content; it appends one marked section.
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --target) [ $# -ge 2 ] || { usage; exit 2; }; TARGET=$2; shift 2 ;;
    --hooks) HOOKS=1; shift ;;
    --ci) CI=1; shift ;;
    --force) FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

[ -n "$TARGET" ] || { usage; exit 2; }
[ -d "$TARGET" ] || { echo "eng install: no such directory: $TARGET" >&2; exit 2; }
TARGET=$(cd -- "$TARGET" && pwd)

command -v python3 >/dev/null 2>&1 || {
  echo "eng install: python3 is required" >&2
  exit 2
}

mkdir -p "$TARGET/.agents/bin" "$TARGET/.agents/lib" "$TARGET/.agents/skills" \
  "$TARGET/.agents/references" "$TARGET/.agents/config" "$TARGET/.agents/hooks" \
  "$TARGET/.agents/ci" "$TARGET/.agents/templates"

cp "$SELF/bin/eng" "$TARGET/.agents/bin/eng"
cp "$SELF/lib/eng.py" "$TARGET/.agents/lib/eng.py"
chmod 755 "$TARGET/.agents/bin/eng" "$TARGET/.agents/lib/eng.py"

# Kit-owned code and skills are replaced on upgrade; local rules live in
# guard-allow.txt and in repository policy, not in these files.
cp -R "$SELF/skills/." "$TARGET/.agents/skills/"
cp -R "$SELF/references/." "$TARGET/.agents/references/"
cp -R "$SELF/hooks/." "$TARGET/.agents/hooks/"
cp -R "$SELF/ci/." "$TARGET/.agents/ci/"
cp -R "$SELF/templates/." "$TARGET/.agents/templates/"
chmod 755 "$TARGET/.agents/hooks/"* 2>/dev/null || true

for f in semgrep.yml gitleaks.toml guard-allow.txt actions-allow.txt; do
  if [ ! -f "$TARGET/.agents/config/$f" ]; then
    cp "$SELF/configs/$f" "$TARGET/.agents/config/$f"
  elif [ "$FORCE" = 1 ] && [ "$f" != "guard-allow.txt" ]; then
    cp "$SELF/configs/$f" "$TARGET/.agents/config/$f"
  fi
done

printf '%s\n' "1.0.0" > "$TARGET/.agents/VERSION"
cp "$SELF/README.agents.md" "$TARGET/.agents/README.md"

INIT_ARGS=""
[ "$HOOKS" = 1 ] && INIT_ARGS="$INIT_ARGS --hooks"
[ "$CI" = 1 ] && INIT_ARGS="$INIT_ARGS --ci"
[ "$FORCE" = 1 ] && INIT_ARGS="$INIT_ARGS --force"

# shellcheck disable=SC2086
python3 "$TARGET/.agents/lib/eng.py" --root "$TARGET" init $INIT_ARGS

echo
echo "eng installed in $TARGET"
echo "  fast:  ./.agents/bin/eng verify --profile fast"
echo "  full:  ./.agents/bin/eng verify --profile full"
echo "  map:   ./.agents/bin/eng detect"
echo "  help:  ./.agents/bin/eng --help"
