# 5 · Automatic HTTPS and the Traefik dashboard

[Contents](../README.md) · [Next: troubleshooting](06-troubleshooting.md)

## Learning goals

Describe domain validation, distinguish wildcard DNS from wildcard TLS, and inspect routing through the dashboard.

The `letsencrypt` resolver uses ACME HTTP-01. The certificate authority asks Traefik to prove control of a hostname by answering a challenge over port 80. Once validated, the certificate is saved in `runtime/letsencrypt/acme.json`. Traefik uses it for HTTPS and schedules renewal automatically while running.

HTTP-to-HTTPS redirection does not prevent Traefik from answering its own HTTP-01 challenge. Keep port 80 reachable after initial setup because renewals still need validation. See the [ACME resolver reference](https://doc.traefik.io/traefik/reference/install-configuration/tls/certificate-resolvers/acme/).

The ACME file contains private keys and account information. Its permissions must be 600. Keep it out of Git, preserve it across container recreation, and include it only in protected backups. Deleting it to “refresh SSL” can cause unnecessary reissuance and rate limits.

## Wildcards are separate decisions

`*.example.org` in DNS can make future subdomains resolve. Traefik still needs a router for each application. In this lab, a new named router gets its own certificate automatically. A wildcard certificate such as `*.example.org` requires DNS-01 validation and DNS-provider integration; HTTP-01 cannot issue it. A wildcard certificate also does not automatically cover `example.org`.

For repeated experiments, use Let's Encrypt's staging endpoint in a separate runtime and ACME store. Staging certificates intentionally fail browser trust checks. Do not repeatedly erase the production certificate store while debugging. Review [challenge types](https://letsencrypt.org/docs/challenge-types/) and [rate limits](https://letsencrypt.org/docs/rate-limits/).

## Inspect the dashboard

Open `https://YOUR_DASHBOARD_HOST/dashboard/`. Keep the trailing slash. Look for each website's router, its matching Host rule, the `websecure` entry point, and its service. The router points to a service; the service selects a backend port.

The default lab is public without a password, but it still uses trusted HTTPS. `api.insecure=false` means the dashboard is routed through Traefik's regular HTTPS entry point; it does not imply authentication. The dashboard/API are for inspection and expose infrastructure metadata.

## Optional exercise: add a password

Install the password-file utility, then create a bcrypt hash interactively. The plaintext password is not placed in your shell command:

```bash
sudo apt-get install -y apache2-utils
sudo install -d -m 700 runtime/secrets
sudo htpasswd -cB runtime/secrets/dashboard.htpasswd admin
sudo chmod 600 runtime/secrets/dashboard.htpasswd
```

Edit `runtime/compose.yaml`. Append this string to Traefik's `volumes` list:

```json
"./secrets/dashboard.htpasswd:/run/secrets/dashboard.htpasswd:ro"
```

Add these entries to Traefik's `labels` object, preserving valid JSON commas:

```json
"traefik.http.routers.dashboard.middlewares": "dashboard-auth",
"traefik.http.middlewares.dashboard-auth.basicauth.usersfile": "/run/secrets/dashboard.htpasswd",
"traefik.http.middlewares.dashboard-auth.basicauth.removeheader": "true"
```

Validate and apply with `sudo docker compose -f runtime/compose.yaml config --quiet` followed by `sudo docker compose -f runtime/compose.yaml up -d`. Without credentials the dashboard should return 401; with credentials it should load. Regenerating Compose removes these manual additions, so reapply them before deploying a regenerated stack.

**Checkpoint:** explain why HTTPS alone does not make a dashboard private.
