import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('configure', Path(__file__).parents[1] / 'scripts/configure.py')
configure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configure)


class ConfigurationTests(unittest.TestCase):
    def test_checked_in_stack_matches_generator(self):
        repo = Path(__file__).parents[1]
        config = json.loads((repo / 'examples/hosting.example.json').read_text())
        example = repo / 'examples/full-stack'
        with tempfile.TemporaryDirectory() as temporary:
            actual = configure.generate(config, temporary)
            self.assertEqual(actual, json.loads((example / 'compose.yaml').read_text()))
            for host in config['sites']:
                relative = Path('sites') / host / 'index.html'
                self.assertEqual((Path(temporary) / relative).read_text(), (example / relative).read_text())

    def config(self):
        return {'email': 'teacher@example.com', 'dashboard': 'traefik.example.com',
                'sites': ['example.com', 'www.example.com']}

    def test_regeneration_removes_public_dashboard_and_preserves_content_and_secrets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stack = configure.generate(self.config(), root)
            page = root / 'sites/example.com/index.html'
            acme = root / 'letsencrypt/acme.json'
            page.write_text('My custom page')
            acme.write_text('{"existing":"certificate state"}')
            legacy = stack['services']['traefik']
            legacy['ports'] = ['80:80', '443:443', '8082:8080']
            legacy['labels']['traefik.http.routers.dashboard.rule'] = 'Host(`traefik.example.com`)'
            legacy['labels']['traefik.http.routers.dashboard.entrypoints'] = 'websecure'
            legacy['labels']['traefik.http.routers.dashboard.tls.certresolver'] = 'letsencrypt'
            (root / 'compose.yaml').write_text(json.dumps(stack))
            configure.generate(self.config(), root)
            regenerated = json.loads((root / 'compose.yaml').read_text())['services']['traefik']
            self.assertEqual(regenerated['ports'], ['80:80', '443:443', '127.0.0.1:8082:8080'])
            self.assertEqual(regenerated['labels']['traefik.http.routers.dashboard.entrypoints'], 'traefik')
            self.assertNotIn('Host(', regenerated['labels']['traefik.http.routers.dashboard.rule'])
            self.assertFalse(any('.tls' in key for key in regenerated['labels']))
            self.assertEqual(page.read_text(), 'My custom page')
            self.assertEqual(json.loads(acme.read_text())['existing'], 'certificate state')
            self.assertEqual(acme.stat().st_mode & 0o777, 0o600)
            self.assertEqual(acme.parent.stat().st_mode & 0o777, 0o700)

    def test_rejects_duplicate_and_unsafe_hosts_before_writing(self):
        for host in ['../escape', 'https://example.com', '*.example.com', 'Example.com', 'traefik.example.com']:
            with self.subTest(host=host), tempfile.TemporaryDirectory() as temporary:
                config = self.config()
                config['sites'] = [host]
                root = Path(temporary) / 'uncreated'
                with self.assertRaises(ValueError):
                    configure.generate(config, root)
                self.assertFalse(root.exists())

    def test_dashboard_uses_loopback_port_and_no_public_entrypoint(self):
        with tempfile.TemporaryDirectory() as temporary:
            stack = configure.generate(self.config(), temporary)
            proxy = stack['services']['traefik']
            self.assertEqual(proxy['ports'], ['80:80', '443:443', '127.0.0.1:8082:8080'])
            self.assertIn('--api.dashboard=true', proxy['command'])
            self.assertIn('--api.insecure=false', proxy['command'])
            self.assertNotIn('--api.insecure=true', proxy['command'])
            self.assertIn('--entrypoints.traefik.address=:8080', proxy['command'])
            self.assertIn('--ping=true', proxy['command'])
            self.assertEqual(proxy['healthcheck']['test'], ['CMD', 'traefik', 'healthcheck', '--ping'])
            labels = proxy['labels']
            self.assertEqual(labels['traefik.http.routers.dashboard.rule'],
                             'PathPrefix(`/api`) || PathPrefix(`/dashboard`)')
            self.assertFalse(any('.tls' in key for key in labels))
            api_routers = []
            for service in stack['services'].values():
                for key, value in service['labels'].items():
                    if key.endswith('.service') and value == 'api@internal':
                        router = key.removesuffix('.service')
                        api_routers.append(router)
                        self.assertEqual(service['labels'][router + '.entrypoints'], 'traefik')
            self.assertEqual(api_routers, ['traefik.http.routers.dashboard'])

    def test_website_routes_and_proxy_mounts_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            stack = configure.generate(self.config(), temporary)
            for index, domain in enumerate(self.config()['sites'], 1):
                name = f'site-{index}'
                service = stack['services'][name]
                self.assertNotIn('ports', service)
                self.assertEqual(service['labels'][f'traefik.http.routers.{name}.rule'], f'Host(`{domain}`)')
                self.assertEqual(service['labels'][f'traefik.http.routers.{name}.entrypoints'], 'websecure')
                self.assertEqual(service['networks'], ['web'])
                self.assertEqual(service['volumes'], [f'./sites/{domain}:/usr/local/apache2/htdocs:ro'])
            proxy = stack['services']['traefik']
            self.assertEqual(proxy['volumes'],
                             ['/var/run/docker.sock:/var/run/docker.sock:ro', './letsencrypt:/letsencrypt'])
            self.assertEqual(stack['networks'], {'web': {'name': 'hosting-web'}})

    def test_static_example_keeps_private_entrypoint_and_api_mode(self):
        source = (Path(__file__).parents[1] / 'examples/full-stack/traefik.yml').read_text()
        self.assertRegex(source, r'(?m)^  insecure: false(?:\s+#.*)?$')
        self.assertRegex(source, r"(?m)^  traefik:\n    address: ':8080'(?:\s+#.*)?$")
        self.assertRegex(source, r'(?m)^ping: \{\}(?:\s+#.*)?$')


if __name__ == '__main__':
    unittest.main()
