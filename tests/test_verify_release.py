import importlib.util
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('verify_release', Path(__file__).parents[1] / 'scripts/verify-release.py')
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class Response(io.BytesIO):
    status = 200

    def geturl(self):
        return 'https://calculator.example.org/health'


class PublicReleaseTests(unittest.TestCase):
    def test_rejects_non_https_origins_credentials_and_paths(self):
        for url in ['http://example.org', 'https://user:pass@example.org',
                    'https://example.org/api', 'https://example.org/?key=value']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                verifier.health_url(url)

    def test_stale_production_commit_fails(self):
        response = Response(json.dumps({'status': 'ok', 'environment': 'production', 'commit': 'b' * 40}).encode())
        with patch.object(verifier.urllib.request, 'urlopen', return_value=response):
            with self.assertRaisesRegex(ValueError, 'expected production release'):
                verifier.verify('https://calculator.example.org', 'a' * 40)

    def test_expected_public_release_passes(self):
        health = {'status': 'ok', 'environment': 'production', 'commit': 'a' * 40}
        with patch.object(verifier.urllib.request, 'urlopen', return_value=Response(json.dumps(health).encode())):
            self.assertEqual(verifier.verify('https://calculator.example.org/', 'a' * 40), health)
