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

**Status:** recovery verification and bounded isolated restores passed; package installation and reboot pending.
**Issue:** [#5](https://github.com/kaw393939/373_hosting/issues/5).
**Change record:** [October 26 maintenance](book/changes/2026-10-26-maintenance.md).
**Data recovery:** [chat #4](https://github.com/kaw393939/is373-ai-chat/issues/4)
and [restore checks in chat PR #43](https://github.com/kaw393939/is373-ai-chat/pull/43).
The separate application SQLite recovery record stays in its owning private repository.

The October 26 preflight observed Ubuntu 24.04.5, kernel `6.8.0-146` running
with `6.8.0-147` installed, a reboot marker, and 15 running containers. A fresh
encrypted pre-maintenance snapshot was verified off-host, and the selected chat
PostgreSQL and separate application SQLite restores passed. The owner
authorized backup verification and a bounded isolated
restoration before selected package updates and a controlled reboot. No package
upgrade or reboot was performed as part of HOST-001.

The maintenance shall:

- Identify separate recovery inputs for the historical encrypted chat backup,
  a separate application's SQLite data, and proxy configuration/certificate state.
  Record each recovery point and any missing coverage; do not infer that one
  archive contains the other systems' data.
- Verify a protected off-host copy with matching hashes, successful decryption
  where applicable, and a reviewed manifest. Then restore the agreed data into
  an isolated location and check its integrity and supported application reads.
  Artifact verification alone is not a restoration test.
- Refresh APT metadata and review upgrade candidates before applying selected
  packages within the existing Ubuntu release. Preserve application image and
  release identities, persistent data, certificate state, and HOST-001 policy.
- Record the maintenance/reboot interruption and verify the expected running
  kernel, required services, ports, public sites/releases, and private dashboard
  access afterward. Record recovery actions and remaining gaps honestly.

| Acceptance check | Evidence/status |
|---|---|
| Recovery inputs and recovery points identified separately | Final snapshot at 2026-10-27 01:00:37.692004 UTC; coverage corrected before maintenance |
| Off-host hashes, decryption, and manifest verified | Passed at 01:01:21 UTC: authenticated decryption and all 232 regular-file hashes/path checks |
| Bounded isolated restore and application/data checks | Earlier daily chat archive and three fresh PostgreSQL dumps passed data/ORM checks; separate SQLite integrity, foreign-key, and 14-table snapshot comparisons passed |
| Reviewed package candidates and actual installation result | Metadata refreshed; 22 upgrades, no additions/removals/held packages; installation pending |
| Reboot duration, running kernel, required services and ports | Pending |
| Public negative/private positive HOST-001 checks and site/release regressions | Pending |

This authorizes operational maintenance, not an Ubuntu release upgrade or a
new application release. The isolated restoration establishes only its recorded
scope; it does not establish a full host rebuild, public DNS/TLS recovery, or
recovery of writes newer than the verified backup. SQLite checks establish the
selected snapshot, not live-source parity; a full authenticated application
journey was not exercised. Protected configuration files were verified without
extraction on the Mac. Keep private archives,
databases, credentials, decryption material, and raw manifests outside Git.
This instructor operation adds no required student task. Dated findings are
AI/operator evidence, not learner responses.
