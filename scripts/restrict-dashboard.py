#!/usr/bin/env python3
"""Plan or apply HOST-001 to an existing JSON Compose file without regenerating sites."""
import argparse
import contextlib
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

ROUTER = 'traefik.http.routers.dashboard.'
PRIVATE_PORT = '127.0.0.1:8082:8080'
RULE = 'PathPrefix(`/api`) || PathPrefix(`/dashboard`)'
BACKUPS = Path('/var/backups/hosting373')
INTERRUPTS = (signal.SIGINT, signal.SIGHUP, signal.SIGTERM)


class ApplyInterrupted(RuntimeError):
    pass


@contextlib.contextmanager
def apply_signals():
    def interrupt(*arguments):
        raise ApplyInterrupted('Apply interrupted; attempting disabled fallback')
    previous = {item: signal.getsignal(item) for item in INTERRUPTS}
    try:
        for item in INTERRUPTS:
            signal.signal(item, interrupt)
        yield
    finally:
        for item, handler in previous.items():
            signal.signal(item, handler)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *arguments):
        return None


def restrict_dashboard(model):
    """Return a private-dashboard copy; reject layouts this migration cannot safely infer."""
    result = copy.deepcopy(model)
    try:
        if result.get('include'):
            raise ValueError
        services = result['services']
        proxy = services['traefik']
        command, labels, ports = proxy['command'], proxy['labels'], proxy['ports']
        if not isinstance(command, list) or not isinstance(labels, dict) or not isinstance(ports, list):
            raise ValueError
        flags = {}
        for argument in command:
            key, separator, value = argument.partition('=')
            key = key.lower()
            if '$' in argument or not separator or not key.startswith('--') or key in flags or key == '--configfile':
                raise ValueError
            flags[key] = value
        if flags.get('--api.insecure') != 'false' or flags.get('--api.dashboard') != 'true':
            raise ValueError
        if flags.get('--api.basepath', '/') != '/' or proxy.get('network_mode') or proxy.get('entrypoint'):
            raise ValueError
        if flags.get('--providers.docker.endpoint', 'unix:///var/run/docker.sock') != 'unix:///var/run/docker.sock':
            raise ValueError
        if proxy.get('env_file'):
            raise ValueError
        environment = proxy.get('environment', {})
        if any(key.upper().startswith('TRAEFIK_') for key in environment):
            raise ValueError
        address = '--entrypoints.traefik.address'
        if address in flags and flags[address] != ':8080':
            raise ValueError
        for key, value in flags.items():
            if key.startswith('--providers.') and key != '--providers.docker' and not key.startswith('--providers.docker.'):
                raise ValueError
            if key.startswith('--entrypoints.') and key.endswith('.address') and key != address:
                if re.search(r':8080(?:/tcp)?$', value):
                    raise ValueError
            if key.startswith('--entrypoints.traefik.http.tls'):
                raise ValueError
        if sorted(ports) not in [sorted(['80:80', '443:443']),
                                 sorted(['80:80', '443:443', PRIVATE_PORT])]:
            raise ValueError
        for name, service in services.items():
            if service.get('extends') or service.get('label_file'):
                raise ValueError
            service_labels = service.get('labels', {})
            if isinstance(service_labels, list):
                service_labels = dict(item.split('=', 1) for item in service_labels)
            normalized = {key.lower(): value for key, value in service_labels.items()}
            if len(normalized) != len(service_labels):
                raise ValueError
            for key, value in normalized.items():
                if '$' in key or ('.routers.' in key and '$' in str(value)):
                    raise ValueError
                if str(value).lower() == 'api@internal' and (name != 'traefik' or key != ROUTER + 'service'):
                    raise ValueError
            if name != 'traefik':
                for port in service.get('ports', []):
                    parts = str(port).split(':')
                    published = str(port.get('published', '')) if isinstance(port, dict) else (parts[-2] if len(parts) > 1 else '')
                    if '$' in published:
                        raise ValueError
                    bounds = published.split('-')
                    if published == '8082' or (len(bounds) == 2 and int(bounds[0]) <= 8082 <= int(bounds[1])):
                        raise ValueError
        for key in list(labels):
            lowered = key.lower()
            if lowered in [ROUTER + field for field in ('rule', 'entrypoints', 'service')]:
                del labels[key]
            elif lowered == ROUTER + 'tls' or lowered.startswith(ROUTER + 'tls.'):
                del labels[key]
        labels.update({ROUTER + 'rule': RULE, ROUTER + 'entrypoints': 'traefik',
                       ROUTER + 'service': 'api@internal'})
        if address not in flags:
            command.append(address + '=:8080')
        if PRIVATE_PORT not in ports:
            ports.append(PRIVATE_PORT)
        return result
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        raise ValueError('Unsupported Compose layout; HOST-001 requires the known CLI-based Traefik stack') from None


def disable_dashboard(model):
    """Fail closed: retain sites and ping, but remove the dashboard/API route and host port."""
    result = restrict_dashboard(model)
    proxy = result['services']['traefik']
    proxy['labels'] = {key: value for key, value in proxy['labels'].items()
                       if not key.lower().startswith(ROUTER)}
    proxy['ports'].remove(PRIVATE_PORT)
    return result


def run(arguments, timeout=60):
    process = None
    try:
        process = subprocess.Popen(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, start_new_session=True)
        output, _ = process.communicate(timeout=timeout)
        if process.returncode:
            raise RuntimeError('Docker command failed; private command output was suppressed')
        return output.strip()
    except (OSError, subprocess.SubprocessError, KeyboardInterrupt, ApplyInterrupted) as error:
        if process is not None:
            # Ignore repeat interruptions only during this bounded (at most four-second) cleanup.
            previous = {item: signal.signal(item, signal.SIG_IGN) for item in INTERRUPTS}
            try:
                for stop in (signal.SIGTERM, signal.SIGKILL):
                    try:
                        os.killpg(process.pid, stop)
                    except ProcessLookupError:
                        pass
                    try:
                        process.communicate(timeout=2)
                    except subprocess.TimeoutExpired:
                        pass
            finally:
                for item, handler in previous.items():
                    signal.signal(item, handler)
        if isinstance(error, (KeyboardInterrupt, ApplyInterrupted)):
            raise ApplyInterrupted('Docker command interrupted; attempting disabled fallback') from None
        raise RuntimeError('Docker command failed; private command output was suppressed') from None


def compose(path, project):
    return ['docker', 'compose', '--project-name', project, '--project-directory', str(path.parent), '-f', str(path)]


def container_image(path, project, deadline=None):
    def remaining():
        return 60 if deadline is None else max(0.01, deadline - time.monotonic())
    containers = run(compose(path, project) + ['ps', '-q', 'traefik'], timeout=remaining()).split()
    if len(containers) != 1 or not re.fullmatch(r'[a-f0-9]{12,64}', containers[0]):
        raise RuntimeError('Expected exactly one running Traefik container')
    return containers[0], run(['docker', 'inspect', '--format', '{{.Image}}', containers[0]], timeout=remaining())


def read_file(path):
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as source:
        metadata = os.fstat(source.fileno())
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError('Compose target must be a regular file')
        return source.read(), metadata


def stage(path, model):
    descriptor, name = tempfile.mkstemp(prefix='.HOST-001-', suffix='.json', dir=path.parent)
    with os.fdopen(descriptor, 'w') as output:
        json.dump(model, output, indent=2)
        output.write('\n')
        output.flush()
        os.fsync(output.fileno())
    return Path(name)


def replace(path, model, metadata, project):
    candidate = stage(path, model)
    try:
        run(compose(candidate, project) + ['config', '--quiet'])
        os.chown(candidate, metadata.st_uid, metadata.st_gid)
        candidate.chmod(stat.S_IMODE(metadata.st_mode))
        os.replace(candidate, path)
    finally:
        candidate.unlink(missing_ok=True)


def backup(original):
    BACKUPS.mkdir(mode=0o700, parents=True, exist_ok=True)
    if BACKUPS.is_symlink() or BACKUPS.stat().st_uid != 0 or stat.S_IMODE(BACKUPS.stat().st_mode) != 0o700:
        raise RuntimeError('Backup directory must be root-owned with mode 0700')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination = BACKUPS / ('HOST-001-' + stamp)
    destination.mkdir(mode=0o700)
    destination.chmod(0o700)
    descriptor = os.open(destination / 'compose.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, 'wb') as output:
        output.write(original)
        output.flush()
        os.fsync(output.fileno())


def wait_for_private_dashboard(path, project, image):
    deadline = time.monotonic() + 45
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    while time.monotonic() < deadline:
        try:
            container, actual_image = container_image(path, project, deadline)
            if actual_image != image:
                raise RuntimeError('Traefik image changed unexpectedly')
            if run(['docker', 'port', container, '8080/tcp'], timeout=max(0.01, deadline - time.monotonic())) != '127.0.0.1:8082':
                raise RuntimeError('Unexpected administrator port binding')
            with opener.open('http://127.0.0.1:8082/api/version', timeout=max(0.01, min(2, deadline - time.monotonic()))) as response:
                if response.status == 200:
                    return
        except (OSError, RuntimeError) as error:
            if isinstance(error, ApplyInterrupted):
                raise
            if isinstance(error, urllib.error.HTTPError):
                error.close()
            time.sleep(max(0, min(1, deadline - time.monotonic())))
    raise RuntimeError('Private dashboard check did not pass within 45 seconds')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compose', required=True, type=Path)
    parser.add_argument('--apply', action='store_true', help='Require root and the previously reviewed SHA-256')
    parser.add_argument('--expected-sha256')
    args = parser.parse_args(argv)
    try:
        if args.apply and (os.geteuid() != 0 or not args.expected_sha256):
            raise ValueError('Apply requires root and --expected-sha256')
        path = args.compose
        if not path.is_absolute() or path.is_symlink() or not path.is_file():
            raise ValueError('--compose must be an absolute existing nonsymlink JSON file')
        original, metadata = read_file(path)
        digest = hashlib.sha256(original).hexdigest()
        if args.expected_sha256 and args.expected_sha256 != digest:
            raise ValueError('Compose SHA-256 changed; review a fresh plan')
        model = json.loads(original)
        candidate = restrict_dashboard(model)
        print('Compose SHA-256: ' + digest)
        print('HOST-001: dashboard/API -> traefik:8080; publish only 127.0.0.1:8082; preserve sites and ping')
        if not args.apply:
            return 0
        project = model.get('name', path.parent.name.lower())
        if not isinstance(project, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', project):
            raise ValueError('Unsupported Compose project name')
        _, image = container_image(path, project)
        image_name = model['services']['traefik'].get('image', '')
        if not isinstance(image_name, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.:@/-]*', image_name):
            raise ValueError('Unsupported Traefik image reference')
        if run(['docker', 'image', 'inspect', '--format', '{{.Id}}', image_name]) != image:
            raise RuntimeError('Local image reference differs from the running Traefik image')
        staged = stage(path, candidate)
        try:
            run(compose(staged, project) + ['config', '--quiet'])
        finally:
            staged.unlink(missing_ok=True)
        current, _ = read_file(path)
        if hashlib.sha256(current).hexdigest() != digest:
            raise RuntimeError('Compose changed before apply; no replacement made')
        backup(original)
        with apply_signals():
            try:
                replace(path, candidate, metadata, project)
                run(compose(path, project) + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', 'traefik'])
                wait_for_private_dashboard(path, project, image)
            except (OSError, RuntimeError, KeyboardInterrupt):
                try:
                    replace(path, disable_dashboard(candidate), metadata, project)
                    run(compose(path, project) + ['up', '-d', '--no-deps', '--no-build', '--pull', 'never', 'traefik'])
                    container, fallback_image = container_image(path, project)
                    publications = run(['docker', 'port', container]).splitlines()
                    if fallback_image != image or {line.split(' -> ')[0] for line in publications} != {'80/tcp', '443/tcp'}:
                        raise RuntimeError('Disabled fallback runtime check failed')
                    print('HOST-001 FAILED: disabled dashboard/API fallback applied; public sites require verification')
                except (OSError, RuntimeError, KeyboardInterrupt):
                    print('HOST-001 FAILED: disabled fallback could not be completed; operator action required')
                return 1
        print('HOST-001 applied; local API and exact loopback binding verified. Public checks remain required.')
        return 0
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        print('HOST-001 stopped before completion; configuration, credentials, and command output were suppressed')
        return 1
    except (ValueError, RuntimeError) as error:
        print('HOST-001 stopped: ' + str(error))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
