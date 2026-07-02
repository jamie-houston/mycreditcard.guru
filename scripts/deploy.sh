#!/usr/bin/env bash
#
# Post-pull deploy steps for Credit Card Guru.
#
# Safe to run manually anywhere. Every step is idempotent: it no-ops when
# nothing changed, so running the whole thing after every pull never leaves
# you half-deployed.
#
#   ./scripts/deploy.sh
#
# Optional overrides (only needed if auto-detection can't find them):
#   DEPLOY_VENV=/home/you/.virtualenvs/myenv ./scripts/deploy.sh
#   DEPLOY_WSGI=/var/www/you_pythonanywhere_com_wsgi.py ./scripts/deploy.sh
#
set -euo pipefail

# --- locate project root (this script lives in scripts/) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"
echo "==> Deploying from $PROJECT_ROOT"

# --- activate virtualenv ---
# Priority: explicit override -> already-active venv -> local ./venv ->
# the only env under ~/.virtualenvs (PythonAnywhere's default location).
if [ -n "${DEPLOY_VENV:-}" ]; then
    # shellcheck disable=SC1091
    source "$DEPLOY_VENV/bin/activate"
elif [ -n "${VIRTUAL_ENV:-}" ]; then
    echo "==> using already-active venv"
elif [ -f "venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "venv/bin/activate"
elif [ -d "$HOME/.virtualenvs" ] && [ "$(find "$HOME/.virtualenvs" -maxdepth 1 -mindepth 1 -type d | wc -l)" -eq 1 ]; then
    # shellcheck disable=SC1091
    source "$HOME/.virtualenvs/$(ls -1 "$HOME/.virtualenvs")/bin/activate"
elif python -c "import django" >/dev/null 2>&1; then
    # No virtualenv, but the ambient python already has Django (e.g. this
    # PythonAnywhere account installs packages to ~/.local, not a venv).
    echo "==> no virtualenv found; using ambient python"
else
    echo "!! No virtualenv found, and the ambient python can't import Django."
    echo "   Set DEPLOY_VENV to the path shown on the PythonAnywhere Web tab, e.g.:"
    echo "     DEPLOY_VENV=\$HOME/.virtualenvs/<name> ./scripts/deploy.sh"
    exit 1
fi
echo "==> python: $(command -v python)"

# --- dependencies (no-op if requirements unchanged) ---
echo "==> pip install -r requirements.txt"
pip install -q -r requirements.txt

# --- database (no-op if no pending migrations) ---
echo "==> manage.py migrate"
python manage.py migrate --noinput

# --- version file ---
echo "==> Generating VERSION file"
cd "$PROJECT_ROOT"
{
    echo "{"
    echo "  \"timestamp\": \"$(git log -1 --format=%cI main 2>/dev/null || echo '')\","
    echo "  \"commit\": \"$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')\""
    echo "}"
} > VERSION
chmod 644 VERSION

# --- static files ---
echo "==> manage.py collectstatic"
python manage.py collectstatic --noinput

# --- reload web app: PythonAnywhere reloads when its WSGI file is touched ---
WSGI="${DEPLOY_WSGI:-}"
if [ -z "$WSGI" ]; then
    # PythonAnywhere puts exactly one *_wsgi.py per web app under /var/www
    WSGI="$(ls /var/www/*_wsgi.py 2>/dev/null | head -n1 || true)"
fi
if [ -n "$WSGI" ] && [ -f "$WSGI" ]; then
    touch "$WSGI"
    echo "==> reloaded web app (touched $WSGI)"
else
    echo "==> no /var/www/*_wsgi.py found — not on PythonAnywhere, skipping reload"
fi

echo "==> Done."
