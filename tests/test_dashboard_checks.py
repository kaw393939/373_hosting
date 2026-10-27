import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('dashboard_checks', Path(__file__).parents[1] / 'scripts/check-dashboard.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


class DashboardChecks(unittest.TestCase):
    def test_rejects_credentials_and_nonloopback_plaintext_before_connecting(self):
        for value in ('http://example.com', 'https://user:password@example.com',
                      'https://example.com/api', 'https://example.com?token=example'):
            with self.subTest(origin=value), patch.object(checks, 'request') as request:
                with self.assertRaises(ValueError):
                    checks.check(value)
                request.assert_not_called()
        with self.assertRaises(ValueError):
            checks.origin('https://example.com', admin=True)

    def test_exposure_or_redirect_cannot_pass_as_public_denial(self):
        for status in (200, 301, 401, 500):
            with self.subTest(status=status), patch.object(checks, 'request', return_value={'status': status}):
                self.assertFalse(checks.check('https://example.com')['passed'])
        with patch.object(checks, 'request', return_value={'status': 404}):
            result = checks.check('https://example.com')
        self.assertTrue(result['passed'])
        self.assertFalse(result['administrator_access_checked'])

    def test_checks_private_access_separately_and_records_failures_without_bodies(self):
        def responses(url, version=False):
            if url.startswith('http://127.0.0.1:18082'):
                return {'status': 200, **({'version': '3.7.13'} if version else {})}
            return {'status': 404}
        with patch.object(checks, 'request', side_effect=responses):
            result = checks.check('https://example.com', 'http://127.0.0.1:18082')
        self.assertTrue(result['passed'])
        self.assertTrue(result['administrator_access_checked'])
        with patch.object(checks, 'request', side_effect=OSError('private response must not be copied')):
            failed = checks.check('https://example.com')
        self.assertFalse(failed['passed'])
        self.assertNotIn('private response', repr(failed))


if __name__ == '__main__':
    unittest.main()
