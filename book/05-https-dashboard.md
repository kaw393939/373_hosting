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

On your own computer, use the SSH account that you use to administer the VPS:

```bash
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:18082:127.0.0.1:8082 USER@SERVER
```

Leave that terminal running, then open `http://127.0.0.1:18082/dashboard/`. Keep
the trailing slash. Look for each website's router, its matching Host rule,
the `websecure` entry point, and its service. The router points to a service;
the service selects a backend port. Stop the tunnel with Ctrl+C when finished.

The server publishes management port 8082 only on `127.0.0.1`. SSH authenticates
you and encrypts traffic between your computer and the server; the local browser
URL uses HTTP inside that tunnel. No new dashboard password is required by the
base model. Dashboard and API paths on a public website's HTTPS origin must
return 404; ordinary public HTTP traffic still redirects to HTTPS. The private
route issues no public certificate for a dashboard hostname.

`api.insecure=false` disables Traefik's automatic insecure API exposure; it does
not add authentication. The explicit dashboard router selects `api@internal`
only on the named `traefik` entry point at container port 8080, matching
``PathPrefix(`/api`) || PathPrefix(`/dashboard`)``. It is absent from the public
`websecure` entry point. See the [Traefik API/dashboard reference](https://doc.traefik.io/traefik/reference/install-configuration/api-dashboard/).

This boundary restricts remote access through the host's published port. Trusted
processes on the VPS and containers sharing Traefik's network remain within the
administrative trust boundary; loopback publishing is not a complete sandbox.
The [HOST-001 worked change](changes/2026-10-26-dashboard.md) records the earlier
public exposure, the applied correction and the actual checks.

With the base-model tunnel running, check both sides from your own computer:

```bash
python3 scripts/check-dashboard.py --public-origin https://YOUR_WEBSITE_HOST --admin-origin http://127.0.0.1:18082
```

Use a website with a valid trusted certificate. For an existing server, repeat
the public check against its former dashboard hostname while that certificate
remains valid. These are selected HTTP requests; they complement configuration
checks and do not establish the behavior of every possible hostname.

## Optional: add authentication inside the tunnel

The [authentication overlay](../examples/full-stack/compose.auth.yaml) adds an
extra credential check without making the dashboard public. Copy it beside the
generated Compose file and create a bcrypt hash interactively:

```bash
cp examples/full-stack/compose.auth.yaml runtime/compose.auth.yaml
sudo apt-get install -y apache2-utils
sudo install -d -m 700 runtime/credentials
sudo htpasswd -cB runtime/credentials/dashboard.htpasswd admin
sudo chmod 600 runtime/credentials/dashboard.htpasswd
sudo docker compose -f runtime/compose.yaml -f runtime/compose.auth.yaml config --quiet
sudo docker compose -f runtime/compose.yaml -f runtime/compose.auth.yaml up -d
```

The `-c` flag creates/replaces the password file; omit it when changing a user in
an existing file. Through the tunnel, the dashboard and API should return 401
without credentials and load with valid credentials. Public paths still return
404 over HTTPS. Use the same two `-f` arguments for subsequent Compose commands, including
after regenerating the base file, so the overlay remains active.

**Checkpoint:** through the tunnel, identify one router and its service. From a
public connection, confirm the dashboard and API are unavailable. Explain which
connection SSH protects.
