#!/usr/bin/env python3
"""Verify public DNS and HTTP/HTTPS from the machine running this script."""
import argparse
import json
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path
from configure import validate


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--admin-origin', help='Loopback origin of an open SSH tunnel')
    parser.add_argument('--dashboard-origin', help='Former public dashboard with an existing valid TLS certificate')
    args = parser.parse_args()
    with open(args.config) as stream:
        config = validate(json.load(stream))
    failed = False
    for host in config['sites']:
        try:
            addresses = sorted({a[4][0] for a in socket.getaddrinfo(host, 443)})
            print(f'{host}: DNS {", ".join(addresses)}')
            opener = urllib.request.build_opener(NoRedirect)
            try:
                response = opener.open('http://' + host + '/', timeout=15)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                if response.code not in (301, 302, 307, 308) or response.headers.get('Location') != 'https://' + host + '/':
                    raise ValueError('Expected an HTTP redirect to the same HTTPS hostname')
            with urllib.request.urlopen('https://' + host + '/', timeout=15) as response:
                body = response.read().decode()
                if response.status != 200 or host not in body:
                    raise ValueError('Unexpected status or welcome-page hostname')
            print('  PASS: HTTP redirect, trusted TLS, and HTTPS response')
        except Exception as error:
            failed = True
            print(f'  FAIL: {error}', file=sys.stderr)
    command = [sys.executable, str(Path(__file__).with_name('check-dashboard.py')),
               '--public-origin', args.dashboard_origin or 'https://' + config['sites'][0]]
    if args.admin_origin:
        command += ['--admin-origin', args.admin_origin]
    dashboard_failed = subprocess.run(command, check=False).returncode != 0
    return int(failed or dashboard_failed)


if __name__ == '__main__':
    sys.exit(main())
