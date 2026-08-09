"""Guard: no native `alert()`, `confirm()` or `prompt()` anywhere in static/js.

Story 10 replaced all 14 of them with `showNotification()` and the
promise-returning `confirmDialog()` / `promptDialog()` helpers in `utils.js`.
The reason it stays a test rather than a one-off cleanup: a native dialog
hard-freezes browser automation until a human dismisses it, so a single new
`confirm()` silently makes a page untestable by Playwright again. That is the
failure this catches — the inconsistent styling is the lesser half.

Not a lint rule because the project has no JS linter in the gate; a Python test
runs in `manage.py test`, which is where the other guards already live.
"""

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

JS_ROOT = Path(settings.BASE_DIR) / 'static' / 'js'

# The same expression as the story's grep: a bare call, not a member access
# (`window.alert` is equally banned, but `foo.confirm(` on some unrelated object
# is not what this is about, and `.prompt(` shows up in third-party shapes).
NATIVE_DIALOG = re.compile(r'(?:^|[^.\w])(alert|confirm|prompt)\s*\(')

BLOCK_COMMENT = re.compile(r'/\*.*?\*/', re.DOTALL)
# `//` to end of line, but not the `//` in `https://` — a scheme is always
# preceded by `:`, and nothing else in these files legitimately is.
LINE_COMMENT = re.compile(r'(?<!:)//[^\n]*')


def strip_comments(source):
    """Drop comments so prose *about* these calls doesn't trip the guard."""
    return LINE_COMMENT.sub('', BLOCK_COMMENT.sub('', source))


class NoNativeDialogsTests(SimpleTestCase):
    def test_no_native_dialog_calls_in_static_js(self):
        offenders = []
        for path in sorted(JS_ROOT.rglob('*.js')):
            for lineno, line in enumerate(strip_comments(path.read_text()).splitlines(), 1):
                match = NATIVE_DIALOG.search(line)
                if match:
                    relative = path.relative_to(settings.BASE_DIR)
                    offenders.append(f'{relative}:{lineno}: {match.group(1)}( — {line.strip()}')

        self.assertEqual(
            offenders, [],
            'Native browser dialogs are banned in static/js — they freeze browser '
            'automation until a human dismisses them. Use showNotification() for '
            'messages, or confirmDialog() / promptDialog() from utils.js when you '
            'need an answer back. Offending call(s):\n  ' + '\n  '.join(offenders),
        )

    def test_the_replacement_helpers_exist(self):
        """Guards the guard: if utils.js loses the helpers, the ban is unmeetable."""
        utils = (JS_ROOT / 'utils.js').read_text()
        for helper in ('function confirmDialog(', 'function promptDialog('):
            self.assertIn(helper, utils, f'{helper}…) is missing from static/js/utils.js')
