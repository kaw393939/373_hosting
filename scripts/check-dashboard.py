#!/usr/bin/env python3
"""Check public management denial and optional SSH-tunnel access; never print bodies."""
import argparse
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit

PUBLIC_PATHS = (
    '/dashboard/', '/api/version', '/api/overview', '/api/entrypoints',
    '/api/http/routers', '/api/http/services', '/api/http/middlewares',
    '/api/tcp/routers', '/api/tcp/services', '/api/udp/routers',
    '/api/udp/services', '/debug/vars', '/debug/pprof/',
)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def origin(value, admin=False):
    parsed = urlsplit(value)
    loopback = parsed.hostname in ('127.0.0.1', 'localhost', '::1')
    if (not parsed.hostname or parsed.username or parsed.password or parsed.query
            or parsed.fragment or parsed.path not in ('', '/')
            or parsed.scheme not in ('http', 'https')
            or (parsed.scheme != 'https' and not loopback)
            or (admin and not loopback)):
        raise ValueError('Use a bare HTTPS origin; HTTP/admin origins must be loopback')
    return value.rstrip('/')


def request(url, version=False):
    try:
        response = urllib.request.build_opener(NoRedirect).open(url, timeout=10)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        result = {'status': response.status}
        if version and response.status == 200:
            data = json.loads(response.read(4096))
            if not isinstance(data.get('Version'), str):
                raise ValueError('Administrator API did not identify Traefik')
            result['version'] = data['Version']
        return result


def check(public_origin, admin_origin=None):
    public_origin = origin(public_origin)
    if admin_origin:
        admin_origin = origin(admin_origin, admin=True)
    results = []
    targets = [(public_origin + path, 404, False) for path in PUBLIC_PATHS]
    if admin_origin:
        targets += [(admin_origin + '/dashboard/', 200, False),
                    (admin_origin + '/api/version', 200, True)]
    for url, expected, version in targets:
        row = {'url': url, 'expected': expected}
        try:
            row.update(request(url, version))
            row['passed'] = row['status'] == expected
        except (OSError, ValueError, urllib.error.URLError):
            row.update(passed=False, error='Connection, TLS or response validation failed')
        results.append(row)
    return {'passed': all(row['passed'] for row in results),
            'administrator_access_checked': bool(admin_origin), 'results': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public-origin', required=True)
    parser.add_argument('--admin-origin', help='Loopback origin of the SSH tunnel')
    parser.add_argument('--output', type=Path, help='Optional private JSON evidence file')
    args = parser.parse_args()
    try:
        result = check(args.public_origin, args.admin_origin)
    except ValueError as error:
        parser.error(str(error))
    for row in result['results']:
        print(f"{'PASS' if row['passed'] else 'FAIL'} {row['url']}: "
              f"expected {row['expected']}, observed {row.get('status', 'unavailable')}")
    if not args.admin_origin:
        print('Administrator access not checked; open the SSH tunnel and add --admin-origin.')
    print('Scope: selected HTTP routes only; not host isolation, all hostnames or container identity.')
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    return int(not result['passed'])


if __name__ == '__main__':
    sys.exit(main())
