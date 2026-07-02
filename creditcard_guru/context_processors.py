"""
Context processors for creditcard_guru project.
Provides global template variables across all templates.
"""
import os
import json
import subprocess
from datetime import datetime
from django.db.models import Max
from django.conf import settings
from cards.models import CreditCard


def _parse_iso_timestamp(timestamp_str):
    """
    Parse ISO 8601 timestamp string to datetime object.

    Args:
        timestamp_str: ISO 8601 timestamp string (e.g., "2026-07-02T16:18:40-05:00")

    Returns:
        datetime: Parsed datetime object, or None if parsing fails
    """
    try:
        return datetime.fromisoformat(timestamp_str)
    except (ValueError, TypeError):
        return None


def _get_version_info():
    """
    Get version info from VERSION file (generated during deploy) or from git.

    Returns:
        dict: Version info with 'timestamp' (datetime object) and 'commit' keys, or empty dict if unavailable
    """
    version_file = os.path.join(settings.BASE_DIR, 'VERSION')

    # Try to read from VERSION file (generated during deploy)
    if os.path.exists(version_file):
        try:
            with open(version_file, 'r') as f:
                data = json.load(f)
                # Parse the timestamp string to datetime object
                if 'timestamp' in data and data['timestamp']:
                    data['timestamp'] = _parse_iso_timestamp(data['timestamp'])
                return data
        except Exception:
            pass

    # Fallback: generate from git (for local dev)
    try:
        # Get the timestamp of the last commit to main
        timestamp_str = subprocess.check_output(
            ['git', 'log', '-1', '--format=%cI', 'main'],
            cwd=settings.BASE_DIR,
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()

        # Get the short commit hash
        commit = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=settings.BASE_DIR,
            stderr=subprocess.DEVNULL
        ).decode('utf-8').strip()

        if timestamp_str:
            timestamp = _parse_iso_timestamp(timestamp_str)
            return {'timestamp': timestamp, 'commit': commit}
    except Exception:
        pass

    return {}


def footer_context(request):
    """
    Provides footer-related context variables to all templates.

    Returns:
        dict: Context variables including:
            - current_year: Current year for copyright
            - last_import_date: Last time cards were imported/updated
            - version_info: Version info with timestamp and commit hash
    """
    # Get current year for copyright
    current_year = datetime.now().year

    # Get the last time any credit card was updated (indicates last import)
    last_import_date = None
    try:
        # Find the most recently updated credit card
        latest_card_update = CreditCard.objects.aggregate(
            latest_update=Max('updated_at')
        )['latest_update']

        if latest_card_update:
            last_import_date = latest_card_update
    except Exception:
        # If there's any database error, just set to None
        # This ensures the site doesn't break if there are no cards yet
        pass

    # Get version info
    version_info = _get_version_info()

    return {
        'current_year': current_year,
        'last_import_date': last_import_date,
        'version_info': version_info,
    }
