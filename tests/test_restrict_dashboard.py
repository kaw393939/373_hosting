import contextlib
import copy
import hashlib
import http.server
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('restrict_dashboard', Path(__file__).parents[1] / 'scripts/restrict-dashboard.py')
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class MigrationTests(unittest.TestCase):
    def model(self):
        model = json.loads((Path(__file__).parents[1] / 'examples/full-stack/compose.yaml').read_text())
        proxy = model['services']['traefik']
        proxy['command'].remove('--entrypoints.traefik.address=:8080')
        proxy['ports'].remove(migration.PRIVATE_PORT)
        proxy['labels'].update({migration.ROUTER + 'rule': 'Host(`traefik.example.com`)',
                                migration.ROUTER + 'entrypoints': 'websecure',
                                migration.ROUTER + 'tls.certresolver': 'letsencrypt',
                                migration.ROUTER + 'middlewares': 'dashboard-auth'})
        proxy['labels']['traefik.http.middlewares.dashboard-auth.basicauth.usersfile'] = '/run/secrets/auth'
        model['services']['application'] = {'image': 'example/app@sha256:abc', 'environment': {'PRIVATE': 'preserve-me'},
                                             'volumes': ['./data:/data'], 'ports': ['127.0.0.1:8090:8000', '9000']}
        return model

    def test_private_migration_is_idempotent_and_preserves_other_configuration(self):
        original = self.model()
        untouched = copy.deepcopy(original)
        result = migration.restrict_dashboard(original)
        self.assertEqual(original, untouched)
        self.assertEqual(migration.restrict_dashboard(result), result)
        expected = copy.deepcopy(untouched)
        proxy = expected['services']['traefik']
        proxy['command'].append('--entrypoints.traefik.address=:8080')
        proxy['ports'].append(migration.PRIVATE_PORT)
        del proxy['labels'][migration.ROUTER + 'tls.certresolver']
        proxy['labels'].update({migration.ROUTER + 'rule': migration.RULE,
                                migration.ROUTER + 'entrypoints': 'traefik',
                                migration.ROUTER + 'service': 'api@internal'})
        self.assertEqual(result, expected)

    def test_disabled_fallback_removes_only_admin_route_and_publication(self):
        private = migration.restrict_dashboard(self.model())
        disabled = migration.disable_dashboard(private)
        proxy = disabled['services']['traefik']
        self.assertEqual(proxy['ports'], ['80:80', '443:443'])
        self.assertFalse(any(key.startswith(migration.ROUTER) for key in proxy['labels']))
        self.assertIn('--ping=true', proxy['command'])
        self.assertIn('--api.insecure=false', proxy['command'])
        for name, service in private['services'].items():
            if name != 'traefik':
                self.assertEqual(disabled['services'][name], service)
        self.assertEqual(migration.disable_dashboard(disabled), disabled)

    def test_rejects_unsupported_or_conflicting_proxy_configuration(self):
        modifications = [
            lambda proxy: proxy['command'].append('--configFile=/private/config.yml'),
            lambda proxy: proxy['command'].append('--API.INSECURE=true'),
            lambda proxy: proxy['command'].append('--entrypoints.traefik.address=:9090'),
            lambda proxy: proxy['command'].append('--entrypoints.other.address=:8080'),
            lambda proxy: proxy['command'].append('--entrypoints.traefik.http.tls=true'),
            lambda proxy: proxy['command'].append('--providers.file.filename=/private/routes.yml'),
            lambda proxy: proxy['command'].append('--providers.docker.endpoint=tcp://other-host:2375'),
            lambda proxy: proxy.update(network_mode='host'),
            lambda proxy: proxy.update(entrypoint=['custom-wrapper']),
            lambda proxy: proxy.update(env_file=['.env']),
            lambda proxy: proxy.update(environment={'TRAEFIK_API_INSECURE': 'true'}),
            lambda proxy: proxy.update(labels=['traefik.enable=true']),
            lambda proxy: proxy['labels'].update({'TRAEFIK.HTTP.ROUTERS.DASHBOARD.SERVICE': 'api@internal'}),
        ]
        for change in modifications:
            with self.subTest(change=change):
                model = self.model()
                change(model['services']['traefik'])
                with self.assertRaises(ValueError):
                    migration.restrict_dashboard(model)
        for port in ['8082:8080', '[::1]:8082:8080', '127.0.0.1:8082:8080/udp',
                     '127.0.0.1:8080:8080', {'published': 8082, 'target': 8080}, migration.PRIVATE_PORT + '/tcp']:
            with self.subTest(port=port):
                model = self.model()
                model['services']['traefik']['ports'].append(port)
                with self.assertRaises(ValueError):
                    migration.restrict_dashboard(model)

    def test_rejects_other_api_routers_and_port_collisions(self):
        for extension in ['extends', 'label_file']:
            model = self.model()
            model['services']['application'][extension] = 'external.yml'
            with self.subTest(extension=extension), self.assertRaises(ValueError):
                migration.restrict_dashboard(model)
        model = self.model()
        model['include'] = ['external.yml']
        with self.assertRaises(ValueError):
            migration.restrict_dashboard(model)
        for labels in [{migration.ROUTER + 'service': 'api@internal'},
                       {'traefik.http.routers.other.service': '${ADMIN_SERVICE:-api@internal}'},
                       ['Traefik.http.routers.other.service=API@INTERNAL']]:
            with self.subTest(labels=labels):
                model = self.model()
                model['services']['application']['labels'] = labels
                with self.assertRaises(ValueError):
                    migration.restrict_dashboard(model)
        for port in ['8082:80', '[::]:8082:80', '8080-8085:80-85', {'published': '8082', 'target': 80}]:
            with self.subTest(port=port):
                model = self.model()
                model['services']['application']['ports'] = [port]
                with self.assertRaises(ValueError):
                    migration.restrict_dashboard(model)

    def invoke(self, path, *arguments):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = migration.main(['--compose', str(path), *arguments])
        return status, output.getvalue()

    def test_plan_reads_only_and_does_not_print_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'compose.yaml'
            original = json.dumps(self.model()).encode()
            path.write_bytes(original)
            with mock.patch.object(migration, 'run') as run, mock.patch.object(migration, 'stage') as stage:
                status, output = self.invoke(path)
            self.assertEqual(status, 0)
            self.assertIn(hashlib.sha256(original).hexdigest(), output)
            self.assertNotIn('preserve-me', output)
            self.assertNotIn('admin@example.com', output)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(path.parent.iterdir()), [path])
            run.assert_not_called()
            stage.assert_not_called()

    def test_rejects_stale_hash_nonroot_symlink_and_bad_json_before_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'compose.yaml'
            original = json.dumps(self.model()).encode()
            path.write_bytes(original)
            alias = Path(temporary) / 'alias.yaml'
            alias.symlink_to(path)
            cases = [(path, ['--apply', '--expected-sha256', '0' * 64], 0),
                     (path, ['--apply', '--expected-sha256', hashlib.sha256(original).hexdigest()], 501),
                     (alias, [], 0), (Path('compose.yaml'), [], 0)]
            for target, arguments, uid in cases:
                with self.subTest(target=target, uid=uid), mock.patch.object(migration.os, 'geteuid', return_value=uid), \
                     mock.patch.object(migration, 'run') as run, mock.patch.object(migration, 'stage') as stage:
                    self.assertEqual(self.invoke(target, *arguments)[0], 1)
                    run.assert_not_called()
                    stage.assert_not_called()
                    self.assertEqual(path.read_bytes(), original)
            path.write_text('{"private-secret": invalid}')
            status, output = self.invoke(path)
            self.assertEqual(status, 1)
            self.assertNotIn('private-secret', output)

    def exercise_failed_apply(self, failure, during_up=False):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'compose.yaml'
            original = json.dumps(self.model()).encode()
            path.write_bytes(original)
            path.chmod(0o640)
            calls = []
            def fake_run(arguments, timeout=60):
                calls.append(arguments)
                if during_up and 'up' in arguments and sum('up' in call for call in calls) == 1:
                    raise failure
                if arguments[:3] == ['docker', 'image', 'inspect']:
                    return 'sha256:same-image'
                if arguments[:2] == ['docker', 'port']:
                    return '80/tcp -> 0.0.0.0:80\n443/tcp -> 0.0.0.0:443'
                return ''
            with mock.patch.object(migration.os, 'geteuid', return_value=0), \
                 mock.patch.object(migration.os, 'chown'), mock.patch.object(migration, 'backup') as backup, \
                 mock.patch.object(migration, 'container_image', return_value=('a' * 64, 'sha256:same-image')), \
                 mock.patch.object(migration, 'run', side_effect=fake_run), \
                 mock.patch.object(migration, 'wait_for_private_dashboard', side_effect=None if during_up else failure):
                status, output = self.invoke(path, '--apply', '--expected-sha256', hashlib.sha256(original).hexdigest())
            self.assertEqual(status, 1)
            self.assertIn('disabled dashboard/API fallback applied', output)
            self.assertNotIn('private-secret', output)
            self.assertEqual(json.loads(path.read_text()), migration.disable_dashboard(self.model()))
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)
            backup.assert_called_once_with(original)
            recreations = [call for call in calls if 'up' in call]
            self.assertEqual(len(recreations), 2)
            for call in recreations:
                self.assertEqual(call[-7:], ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', 'traefik'])
            for call in calls:
                if call[:2] == ['docker', 'compose']:
                    self.assertEqual(call[call.index('--project-name') + 1], 'hosting373')
                    self.assertEqual(call[call.index('--project-directory') + 1], str(path.parent))
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_apply_failure_installs_disabled_fallback_without_restoring_public_route(self):
        self.exercise_failed_apply(RuntimeError('private-secret'))

    def test_interruption_during_recreation_attempts_disabled_fallback(self):
        for failure in [KeyboardInterrupt(), migration.ApplyInterrupted('private-secret')]:
            with self.subTest(interruption=type(failure).__name__):
                self.exercise_failed_apply(failure, during_up=True)

    def test_docker_error_output_is_suppressed(self):
        process = mock.Mock(returncode=1)
        process.communicate.return_value = ('private-secret', 'private-secret')
        with mock.patch.object(migration.subprocess, 'Popen', return_value=process):
            with self.assertRaisesRegex(RuntimeError, '^Docker command failed; private command output was suppressed$'):
                migration.run(['docker', 'compose', 'config', '--quiet'])

    def test_signal_interruption_terminates_subprocess_group_and_restores_handlers(self):
        popen = subprocess.Popen
        processes, timers = [], []
        previous = {item: migration.signal.getsignal(item) for item in migration.INTERRUPTS}
        def start_process(*arguments, **keywords):
            process = popen(*arguments, **keywords)
            processes.append(process)
            timer = threading.Timer(0.05, os.kill, args=(os.getpid(), migration.signal.SIGTERM))
            timers.append(timer)
            timer.start()
            return process
        with mock.patch.object(migration.subprocess, 'Popen', side_effect=start_process):
            with migration.apply_signals(), self.assertRaises(migration.ApplyInterrupted):
                migration.run([sys.executable, '-c', 'import time; time.sleep(30)'])
        for timer in timers:
            timer.join(timeout=2)
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())
        with self.assertRaises(ProcessLookupError):
            os.killpg(processes[0].pid, 0)
        self.assertEqual({item: migration.signal.getsignal(item) for item in migration.INTERRUPTS}, previous)

    def test_unknown_container_count_is_rejected_before_inspection(self):
        for output in ['', 'a' * 64 + '\n' + 'b' * 64]:
            with self.subTest(output=output), mock.patch.object(migration, 'run', return_value=output) as run:
                with self.assertRaisesRegex(RuntimeError, 'exactly one running Traefik'):
                    migration.container_image(Path('/opt/hosting/compose.yaml'), 'hosting')
                self.assertEqual(run.call_count, 1)

    def test_image_drift_stops_before_staging_backup_or_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'compose.yaml'
            original = json.dumps(self.model()).encode()
            path.write_bytes(original)
            with mock.patch.object(migration.os, 'geteuid', return_value=0), \
                 mock.patch.object(migration, 'container_image', return_value=('a' * 64, 'sha256:running')), \
                 mock.patch.object(migration, 'run', return_value='sha256:different'), \
                 mock.patch.object(migration, 'stage') as stage, mock.patch.object(migration, 'backup') as backup:
                status, output = self.invoke(path, '--apply', '--expected-sha256', hashlib.sha256(original).hexdigest())
            self.assertEqual(status, 1)
            self.assertIn('Local image reference differs', output)
            self.assertEqual(path.read_bytes(), original)
            stage.assert_not_called()
            backup.assert_not_called()

    def test_private_check_rejects_additional_ipv6_publication(self):
        with mock.patch.object(migration.time, 'monotonic', side_effect=[0, 0, 0, 45, 45]), \
             mock.patch.object(migration.time, 'sleep'), \
             mock.patch.object(migration, 'container_image', return_value=('a' * 64, 'sha256:same')), \
             mock.patch.object(migration, 'run', return_value='127.0.0.1:8082\n[::]:8082'), \
             mock.patch.object(migration.urllib.request, 'build_opener') as opener:
            with self.assertRaisesRegex(RuntimeError, 'within 45 seconds'):
                migration.wait_for_private_dashboard(Path('/opt/hosting/compose.yaml'), 'hosting', 'sha256:same')
            opener.return_value.open.assert_not_called()

    def test_local_api_redirect_is_not_followed_to_an_unrelated_success(self):
        requests = []
        class RedirectingAPI(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                self.send_response(302 if self.path == '/api/version' else 200)
                self.send_header('Location', '/unrelated')
                self.end_headers()
            def log_message(self, *arguments):
                pass
        server = http.server.HTTPServer(('127.0.0.1', 0), RedirectingAPI)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            opener = migration.urllib.request.build_opener(migration.urllib.request.ProxyHandler({}), migration.NoRedirect())
            with self.assertRaises(migration.urllib.error.HTTPError) as raised:
                opener.open(f'http://127.0.0.1:{server.server_port}/api/version', timeout=2)
            raised.exception.close()
            self.assertEqual(requests, ['/api/version'])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
