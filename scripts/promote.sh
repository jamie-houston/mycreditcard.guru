#!/usr/bin/env bash
#
# Deploy main to PythonAnywhere — run this on your laptop, not the server.
#
# Pushes main, then SSHes in to pull and run scripts/deploy.sh (which does the
# migrate/import/collectstatic/reload). Refuses to run on a dirty tree or off
# main, and confirms afterwards that the commit the server reports matches the
# one you just pushed.
#
#   ./scripts/promote.sh
#
# Optional overrides:
#   PA_USER=foresterh PA_DIR=/home/foresterh/mycreditcard.guru ./scripts/promote.sh
#   PA_VENV=$HOME/.virtualenvs/creditcard_guru ./scripts/promote.sh   # if auto-detect fails
#   PA_SITE_URL=https://example.com ./scripts/promote.sh              # public check
set -euo pipefail

PA_USER="${PA_USER:-foresterh}"
PA_HOST="${PA_HOST:-ssh.pythonanywhere.com}"
PA_DIR="${PA_DIR:-/home/foresterh/mycreditcard.guru}"
PA_SITE_URL="${PA_SITE_URL:-https://www.mycreditcard.guru}"
BRANCH="main"

die() { echo "promote: $*" >&2; exit 1; }

# --- preconditions ---
[ -z "$(git status --porcelain)" ] \
    || die "working tree is dirty — commit or stash first"

current_branch="$(git rev-parse --abbrev-ref HEAD)"
[ "$current_branch" = "$BRANCH" ] \
    || die "on '$current_branch', not '$BRANCH' — this project deploys straight from $BRANCH"

local_sha="$(git rev-parse --short HEAD)"
echo "==> deploying $local_sha to $PA_USER@$PA_HOST:$PA_DIR"

# --- push ---
echo "==> git push origin $BRANCH"
git push origin "$BRANCH"

# --- remote pull + deploy ---
# data/input/cards/*.json is tracked but rewritten in place by the monthly
# import_external_cards task, which leaves the server tree dirty and blocks
# --ff-only. Git's copy is canonical (the DB is what actually serves), so
# discarding the server's edits is safe.
remote_script="$(cat <<REMOTE
set -euo pipefail
cd '$PA_DIR'
if [ -n "\$(git status --porcelain -- data/input/cards/)" ]; then
    echo '==> discarding server-side edits under data/input/cards/'
    git checkout -- data/input/cards/
fi
git pull --ff-only
${PA_VENV:+DEPLOY_VENV='$PA_VENV' }./scripts/deploy.sh
echo "REMOTE_SHA=\$(git rev-parse --short HEAD)"
REMOTE
)"

# tee to a temp file rather than a variable so the deploy's output streams as
# it runs, while still leaving the trailing REMOTE_SHA line readable.
log="$(mktemp)"
trap 'rm -f "$log"' EXIT
ssh "$PA_USER@$PA_HOST" "bash -lc $(printf '%q' "$remote_script")" 2>&1 | tee "$log"

# --- verify the server is on the commit we just pushed ---
remote_sha="$(tr -d '\r' <"$log" | sed -n 's/^REMOTE_SHA=//p' | tail -n1)"
[ -n "$remote_sha" ] || die "deploy ran but the server never reported a commit — check the output above"
[ "$remote_sha" = "$local_sha" ] \
    || die "server is on $remote_sha, expected $local_sha — the pull or reload did not take"
echo "==> server is on $local_sha"

# --- public check (visibility only, never a gate) ---
# base.html renders the VERSION commit into the footer of every page.
if served_sha="$(curl -fsS --max-time 15 "$PA_SITE_URL" 2>/dev/null \
    | sed -n 's/.*Version: \([0-9a-f]\{7,\}\).*/\1/p' | head -n1)" \
    && [ -n "$served_sha" ]; then
    if [ "$served_sha" = "$local_sha" ]; then
        echo "==> $PA_SITE_URL is serving $local_sha"
    else
        echo "!! $PA_SITE_URL is serving $served_sha, not $local_sha"
        echo "   The web app may still be reloading — re-check in a few seconds."
    fi
else
    echo "==> could not read the version footer from $PA_SITE_URL (skipping public check)"
fi

echo "==> Done."
