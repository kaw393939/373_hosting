#!/usr/bin/env python3
"""Verify public DNS and HTTP/HTTPS from the machine running this script."""
import argparse
import json
import socket
import sys
import urllib.request
from configure import validate


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    with open(args.config) as stream:
        config = validate(json.load(stream))
    failed = False
    for host in config['sites'] + [config['dashboard']]:
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
            route = '/dashboard/' if host == config['dashboard'] else '/'
            with urllib.request.urlopen('https://' + host + route, timeout=15) as response:
                body = response.read().decode()
                if response.status != 200 or (host != config['dashboard'] and host not in body):
                    raise ValueError('Unexpected status or welcome-page hostname')
            print('  PASS: HTTP redirect, trusted TLS, and HTTPS response')
        except Exception as error:
            failed = True
            print(f'  FAIL: {error}', file=sys.stderr)
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
