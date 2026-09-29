#!/usr/bin/env python3
"""Generate a hosting lab without third-party Python packages or shell interpolation."""
import argparse
import html
import json
import re
from pathlib import Path

HOST = re.compile(r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


def validate(config):
    if not isinstance(config, dict):
        raise ValueError('Configuration must be a JSON object')
    sites = config.get('sites')
    if not isinstance(sites, list) or not sites:
        raise ValueError('sites must be a nonempty list')
    hosts = [config.get('dashboard')] + sites
    if any(not isinstance(h, str) or not HOST.fullmatch(h) for h in hosts):
        raise ValueError('Use lowercase DNS hostnames, without URLs, wildcards, or paths')
    if len(hosts) != len(set(hosts)):
        raise ValueError('Every hostname, including the dashboard, must be unique')
    if not isinstance(config.get('email'), str) or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', config['email']):
        raise ValueError('A valid contact email is required')
    return config


def generate(config, output):
    validate(config)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    certs = output / 'letsencrypt'
    certs.mkdir(mode=0o700, exist_ok=True)
    certs.chmod(0o700)
    acme = certs / 'acme.json'
    acme.touch(mode=0o600, exist_ok=True)
    acme.chmod(0o600)
    logging = {'driver': 'json-file', 'options': {'max-size': '10m', 'max-file': '3'}}
    services = {'traefik': {
        'image': 'traefik:v3.7.13', 'restart': 'unless-stopped',
        'security_opt': ['no-new-privileges:true'],
        'command': [
            '--api.dashboard=true', '--api.insecure=false',
            '--providers.docker=true', '--providers.docker.exposedbydefault=false',
            '--providers.docker.network=hosting-web',
            '--entrypoints.web.address=:80', '--entrypoints.websecure.address=:443',
            '--entrypoints.web.http.redirections.entrypoint.to=websecure',
            '--entrypoints.web.http.redirections.entrypoint.scheme=https',
            '--entrypoints.websecure.http.tls.certresolver=letsencrypt',
            '--certificatesresolvers.letsencrypt.acme.email=' + config['email'],
            '--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json',
            '--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web',
            '--ping=true', '--log.level=INFO', '--accesslog=true'],
        'ports': ['80:80', '443:443'],
        'volumes': ['/var/run/docker.sock:/var/run/docker.sock:ro', './letsencrypt:/letsencrypt'],
        'networks': ['web'], 'logging': logging,
        'healthcheck': {'test': ['CMD', 'traefik', 'healthcheck', '--ping'],
                        'interval': '10s', 'timeout': '5s', 'retries': 3},
        'labels': {'traefik.enable': 'true',
                   'traefik.http.routers.dashboard.rule': f"Host(`{config['dashboard']}`)",
                   'traefik.http.routers.dashboard.entrypoints': 'websecure',
                   'traefik.http.routers.dashboard.service': 'api@internal'}}}
    for index, domain in enumerate(config['sites'], 1):
        name = f'site-{index}'
        folder = output / 'sites' / domain
        folder.mkdir(parents=True, exist_ok=True)
        page = folder / 'index.html'
        if not page.exists():
            title = html.escape(domain)
            page.write_text(f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Welcome | {title}</title>
<style>body{{background:#101827;color:#f4f7fc;font:18px system-ui;margin:0;min-height:100vh;display:grid;place-items:center}}main{{max-width:850px;padding:40px}}h1{{font-size:clamp(32px,6vw,64px);overflow-wrap:anywhere}}p{{line-height:1.7;color:#bac7da}}small{{color:#64dfb4}}</style></head>
<body><main><small>IS 373 · Hosting Lab</small><h1>Welcome to {title}</h1>
<p>This hostname has its own Apache HTTP Server container, routed through Traefik.</p>
<p>Edit this page to test your deployment. HTTPS certificates are managed by Let's Encrypt.</p>
</main></body></html>\n''')
        services[name] = {
            'image': 'httpd:2.4-alpine', 'restart': 'unless-stopped',
            'security_opt': ['no-new-privileges:true'],
            'volumes': [f'./sites/{domain}:/usr/local/apache2/htdocs:ro'],
            'networks': ['web'], 'logging': logging,
            'labels': {'traefik.enable': 'true',
                       f'traefik.http.routers.{name}.rule': f'Host(`{domain}`)',
                       f'traefik.http.routers.{name}.entrypoints': 'websecure',
                       f'traefik.http.services.{name}.loadbalancer.server.port': '80'}}
    stack = {'name': 'hosting373', 'services': services,
             'networks': {'web': {'name': 'hosting-web'}}}
    (output / 'compose.yaml').write_text(json.dumps(stack, indent=2) + '\n')
    return stack


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('runtime'))
    args = parser.parse_args()
    try:
        generate(json.loads(args.config.read_text()), args.output)
    except (ValueError, OSError) as error:
        parser.exit(1, f'Configuration error: {error}\n')
    print(f'Created {args.output}/compose.yaml. Existing pages and certificates were preserved.')
    print('Dashboard authentication is disabled for this lab.')


if __name__ == '__main__':
    main()
