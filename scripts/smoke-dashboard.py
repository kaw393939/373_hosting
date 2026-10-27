#!/usr/bin/env python3
"""Exercise real Traefik HTTP routing on disposable loopback ports, without its Docker provider."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

import configure

SPEC = importlib.util.spec_from_file_location('dashboard_checks', Path(__file__).with_name('check-dashboard.py'))
checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checks)


def run(docker, *args):
    return subprocess.run([docker, *args], check=True, capture_output=True, text=True, timeout=120).stdout.strip()


def exercise(docker, image, private):
    name = 'hosting-dashboard-check-' + uuid.uuid4().hex[:10]
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary).resolve()
        model = configure.generate({'email': 'teacher@example.com', 'dashboard': 'traefik.example.com',
                                    'sites': ['example.com']}, root / 'generated')
        labels = model['services']['traefik']['labels']
        dynamic = {'http': {'routers': {
            'dashboard': {'rule': labels['traefik.http.routers.dashboard.rule'],
                          'entryPoints': [labels['traefik.http.routers.dashboard.entrypoints'] if private else 'web'],
                          'service': 'api@internal'},
            'application': {'rule': 'Path(`/application-check`)', 'entryPoints': ['web'], 'service': 'ping@internal'},
        }}}
        (root / 'dynamic.yaml').write_text(json.dumps(dynamic))
        try:
            run(docker, 'run', '--detach', '--name', name,
                '--publish', '127.0.0.1::8000', '--publish', '127.0.0.1::8080',
                '--mount', f'type=bind,source={root / "dynamic.yaml"},target=/etc/traefik/dynamic.yaml,readonly',
                image, '--api.dashboard=true', '--api.insecure=false', '--ping=true',
                '--entrypoints.web.address=:8000', '--entrypoints.traefik.address=:8080',
                '--providers.file.filename=/etc/traefik/dynamic.yaml', '--log.level=ERROR')
            web = 'http://' + run(docker, 'port', name, '8000/tcp')
            admin = 'http://' + run(docker, 'port', name, '8080/tcp')
            if not web.startswith('http://127.0.0.1:') or not admin.startswith('http://127.0.0.1:'):
                raise RuntimeError('The isolated check unexpectedly published beyond loopback')
            deadline = time.monotonic() + 30
            while True:
                try:
                    if checks.request(web + '/application-check')['status'] == 200:
                        break
                except OSError:
                    pass
                if time.monotonic() >= deadline:
                    raise RuntimeError('The isolated proxy did not become ready')
                time.sleep(0.25)
            if not private:
                if checks.request(web + '/api/version', True)['status'] != 200:
                    raise RuntimeError('The public-route baseline was not reproduced')
                print('PASS: baseline reproduces public API despite api.insecure=false')
            else:
                result = checks.check(web, admin)
                if not result['passed']:
                    raise RuntimeError('Private routing did not meet the HTTP contract')
                print(f"PASS: {len(result['results'])} private-routing comparisons and ordinary route response")
        finally:
            subprocess.run([docker, 'rm', '--force', name], check=False, capture_output=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--docker', default='docker')
    args = parser.parse_args()
    image = 'traefik:v3.7.13'
    if subprocess.run([args.docker, 'image', 'inspect', image], capture_output=True, check=False).returncode:
        run(args.docker, 'pull', image)
    exercise(args.docker, image, private=False)
    exercise(args.docker, image, private=True)
    print('Scope: real Traefik/file-provider HTTP integration; no Docker socket, public DNS/TLS or live server change.')


if __name__ == '__main__':
    main()
