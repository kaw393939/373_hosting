#!/usr/bin/env python3
"""Check the merged companion Compose model without starting containers."""
import argparse
import json


def check(model):
    services = model['services']
    if set(services) != {'dev', 'prod', 'wud'}:
        raise ValueError('Adapter must not add a second proxy or duplicate application services')
    prod = services['prod']
    labels = prod['labels']
    if 'traefik.http.routers.calculator.tls' in labels:
        raise ValueError('Inherit the entry-point TLS resolver; explicit tls=true suppresses that default')
    if labels.get('traefik.http.services.calculator.loadbalancer.server.port') != '8000':
        raise ValueError('Calculator must route to internal port 8000')
    if labels.get('traefik.http.routers.calculator.rule') != 'Host(`calculator.example.org`)':
        raise ValueError('Expected the configured calculator Host rule')
    if labels.get('traefik.docker.network') != model['networks']['hosting']['name']:
        raise ValueError('Traefik must select the actual external network')
    if not model['networks']['hosting']['external'] or 'hosting' not in prod['networks']:
        raise ValueError('Production must join the existing hosting network')
    for name, service in services.items():
        if any(port.get('host_ip') != '127.0.0.1' for port in service.get('ports', [])):
            raise ValueError(f'{name} unexpectedly publishes a public host port')
        if name != 'prod' and ('hosting' in service.get('networks', {})
                              or service.get('labels', {}).get('traefik.enable') == 'true'):
            raise ValueError(f'{name} must remain outside public routing')
    if prod['labels'].get('wud.watch') != 'true':
        raise ValueError('The adapter must preserve production update policy')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', help='Output from docker compose config --format json')
    args = parser.parse_args()
    with open(args.model) as stream:
        check(json.load(stream))
    print('PASS: hosting/application routing contract')


if __name__ == '__main__':
    main()
