import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('configure', Path(__file__).parents[1] / 'scripts/configure.py')
configure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configure)


class ConfigurationTests(unittest.TestCase):
    def config(self):
        return {'email': 'teacher@example.com', 'dashboard': 'traefik.example.com',
                'sites': ['example.com', 'www.example.com']}

    def test_preserves_content_and_certificate_secrets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            configure.generate(self.config(), root)
            page = root / 'sites/example.com/index.html'
            acme = root / 'letsencrypt/acme.json'
            page.write_text('My custom page')
            acme.write_text('{"existing":"certificate state"}')
            configure.generate(self.config(), root)
            self.assertEqual(page.read_text(), 'My custom page')
            self.assertEqual(json.loads(acme.read_text())['existing'], 'certificate state')
            self.assertEqual(acme.stat().st_mode & 0o777, 0o600)

    def test_rejects_duplicate_and_unsafe_hosts_before_writing(self):
        for host in ['../escape', 'https://example.com', '*.example.com', 'Example.com', 'traefik.example.com']:
            with self.subTest(host=host), tempfile.TemporaryDirectory() as temporary:
                config = self.config()
                config['sites'] = [host]
                root = Path(temporary) / 'uncreated'
                with self.assertRaises(ValueError):
                    configure.generate(config, root)
                self.assertFalse(root.exists())

    def test_only_proxy_publishes_ports_and_dashboard_is_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            stack = configure.generate(self.config(), temporary)
            services = stack['services']
            self.assertEqual(services['traefik']['ports'], ['80:80', '443:443'])
            self.assertNotIn('ports', services['site-1'])
            self.assertNotIn('ports', services['site-2'])
            self.assertEqual(services['traefik']['labels']['traefik.http.routers.dashboard.service'], 'api@internal')
            self.assertIn('--api.insecure=false', services['traefik']['command'])


if __name__ == '__main__':
    unittest.main()
