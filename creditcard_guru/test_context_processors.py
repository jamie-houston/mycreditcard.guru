"""
Tests for context processors.
"""
import json
import os
import tempfile
from datetime import datetime
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from creditcard_guru.context_processors import footer_context, _parse_iso_timestamp, _get_version_info


class ParseIsoTimestampTest(TestCase):
    """Test ISO timestamp parsing."""

    def test_parse_valid_iso_timestamp(self):
        """Test parsing a valid ISO 8601 timestamp."""
        timestamp_str = "2026-07-02T16:18:40-05:00"
        result = _parse_iso_timestamp(timestamp_str)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 7)
        self.assertEqual(result.day, 2)

    def test_parse_invalid_timestamp(self):
        """Test parsing an invalid timestamp returns None."""
        result = _parse_iso_timestamp("not a timestamp")
        self.assertIsNone(result)

    def test_parse_empty_timestamp(self):
        """Test parsing empty string returns None."""
        result = _parse_iso_timestamp("")
        self.assertIsNone(result)

    def test_parse_none_timestamp(self):
        """Test parsing None returns None."""
        result = _parse_iso_timestamp(None)
        self.assertIsNone(result)


class VersionInfoTest(TestCase):
    """Test version info retrieval."""

    def test_version_info_from_git(self):
        """Test that version info can be retrieved from git."""
        version_info = _get_version_info()

        # Should have both commit and timestamp when reading from git
        self.assertIn('commit', version_info)
        # Timestamp should be a datetime object or None
        if 'timestamp' in version_info:
            timestamp = version_info['timestamp']
            if timestamp is not None:
                self.assertIsInstance(timestamp, datetime)

    @override_settings(BASE_DIR=tempfile.gettempdir())
    def test_version_info_from_file(self):
        """Test that version info can be read from VERSION file."""
        # Create a temporary VERSION file
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='', prefix='VERSION', delete=False, dir=tempfile.gettempdir()
        ) as f:
            version_file = f.name
            json.dump({
                'timestamp': '2026-07-02T16:18:40-05:00',
                'commit': 'abc1234'
            }, f)

        try:
            # Temporarily override BASE_DIR to use our temp file
            original_base_dir = os.path.dirname(version_file)
            with override_settings(BASE_DIR=original_base_dir):
                # Copy our test file to VERSION in the temp dir
                version_path = os.path.join(original_base_dir, 'VERSION')
                with open(version_file, 'r') as src, open(version_path, 'w') as dst:
                    dst.write(src.read())

                version_info = _get_version_info()

                # Should have commit from file
                self.assertEqual(version_info.get('commit'), 'abc1234')
                # Should have parsed timestamp as datetime
                timestamp = version_info.get('timestamp')
                if timestamp is not None:
                    self.assertIsInstance(timestamp, datetime)

                # Clean up
                os.unlink(version_path)
        finally:
            os.unlink(version_file)


class FooterContextTest(TestCase):
    """Test the footer context processor."""

    def test_footer_context_has_required_keys(self):
        """Test that footer_context returns all required keys."""
        factory = RequestFactory()
        request = factory.get('/')

        context = footer_context(request)

        # Should have these keys
        self.assertIn('current_year', context)
        self.assertIn('last_import_date', context)
        self.assertIn('version_info', context)

    def test_footer_context_current_year(self):
        """Test that current_year is set correctly."""
        factory = RequestFactory()
        request = factory.get('/')

        context = footer_context(request)
        current_year = context['current_year']

        self.assertIsInstance(current_year, int)
        self.assertGreater(current_year, 2000)

    def test_footer_context_version_info(self):
        """Test that version_info is a dict."""
        factory = RequestFactory()
        request = factory.get('/')

        context = footer_context(request)
        version_info = context['version_info']

        self.assertIsInstance(version_info, dict)
