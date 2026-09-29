#!/usr/bin/env python3
"""Verify an application's release identity over its public HTTPS route."""
import argparse
import json
import re
import urllib.parse
import urllib.request


def health_url(origin):
    parsed = urllib.parse.urlsplit(origin)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        raise ValueError('Use an HTTPS origin, such as https://calculator.example.org')
    return origin.rstrip('/') + '/health'


def verify(origin, expected_commit):
    if not re.fullmatch(r'[0-9a-f]{40}', expected_commit):
        raise ValueError('Expected commit must be a full lowercase 40-character Git SHA')
    url = health_url(origin)
    with urllib.request.urlopen(url, timeout=15) as response:
        if response.geturl() != url or response.status != 200:
            raise ValueError('Health must return 200 directly from the requested HTTPS URL')
        health = json.load(response)
    if (health.get('status') != 'ok' or health.get('environment') != 'production'
            or health.get('commit') != expected_commit):
        raise ValueError('Public health does not identify the expected production release')
    return health


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--expected-commit', required=True)
    args = parser.parse_args()
    try:
        health = verify(args.url, args.expected_commit)
    except (ValueError, OSError) as error:
        parser.exit(1, f'Public release verification failed: {error}\n')
    print(json.dumps(health, indent=2))
    print('PASS: trusted HTTPS and expected public production commit')


if __name__ == '__main__':
    main()
