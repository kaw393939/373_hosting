# Hosting requirements

## HOST-001 · Keep the Traefik dashboard private

**Status:** applied and verified October 26, 2026 (EDT; checks completed October 27 at 00:04 UTC).
**PR:** [#4](https://github.com/kaw393939/373_hosting/pull/4).
**Issue:** [#3](https://github.com/kaw393939/373_hosting/issues/3).
**Change record:** [October 26, 2026](book/changes/2026-10-26-dashboard.md).

The classroom dashboard and API were publicly readable without authentication.
Administrators need routing visibility without publishing management metadata
to ordinary website visitors.

The base configuration shall:

- Keep `api.insecure=false` and route `api@internal` only through a named
  `traefik` entry point at container port 8080, with rule
  ``PathPrefix(`/api`) || PathPrefix(`/dashboard`)``.
- Publish that port only as `127.0.0.1:8082:8080`. Administrators use an SSH
  tunnel and `http://127.0.0.1:18082/dashboard/`; no new password is required.
- Remove the dashboard route from public HTTP/HTTPS. Public `/dashboard/` and
  `/api` requests must not expose dashboard content or configuration metadata.
- Preserve ordinary website redirects, trusted HTTPS, content, images, mounts,
  certificate state, networks, and application containers.

The SSH account controls remote access to the host port. Host processes and
containers sharing Traefik's network remain trusted; this is not a complete
sandbox. An optional BasicAuth overlay adds a check inside the tunnel.

| Acceptance check | Expected result | Evidence |
|---|---|---|
| Positive: SSH tunnel, dashboard and API | Dashboard loads; API returns usable routing data | Live HTTP and browser checks passed; see dated record |
| Negative: dashboard/API paths on selected public HTTPS origins, without credentials | 404; no management data | All 13 selected paths returned 404 |
| Regression: ordinary public websites | Redirects, trusted HTTPS, and expected content still work | Eight site baselines and five health/release results unchanged |
| Configuration preservation | Only the required proxy access settings change | Exact planned model installed; other 14 container IDs/images and ACME bytes unchanged |

Positive/negative describe the case being checked. Unit tests check generated
configuration and verifier behavior; a container integration check exercises
Traefik routing; live HTTP/browser checks establish the deployed behavior.
Passing one level does not establish the others.

Public checks require a trusted certificate: use a website origin by default,
and the former dashboard origin when its existing certificate is still valid.
The private route does not issue or renew a certificate for the dashboard name.
Selected requests complement structural checks; they do not prove all hostnames.

Implementation links: [generator](scripts/configure.py),
[generated-model tests](tests/test_configure.py),
[public verifier](scripts/verify.py), [complete Compose example](examples/full-stack/compose.yaml),
[file-based equivalent](examples/full-stack/traefik.yml), and
[existing-deployment migration](scripts/restrict-dashboard.py).
Actual check results belong in [VALIDATION.md](VALIDATION.md) and the dated record.

Applying the change requires Docker administrator access and briefly interrupts
all traffic through Traefik. Preserve a private backup before replacing the live
Compose file. Recovery must keep public management access closed. Retain the
change only after repository and live HTTP/browser checks; do not close the
issue on repository checks alone. Attribute AI operator observations separately
from any later human review.

## HOST-002 · Controlled host maintenance

**Status:** planned; no package upgrades or reboot performed in HOST-001.
**Issue:** [#5](https://github.com/kaw393939/373_hosting/issues/5).

The October 26 audit observed a pending kernel reboot and cached package
updates. Refresh and review candidates, verify recovery prerequisites, then
apply selected updates in a controlled interruption window. Acceptance requires
the expected running kernel, no failed required services or unintended public
ports, preserved public release/content baselines, and HOST-001 still passing.
The issue records the staged checks; live results remain pending.
