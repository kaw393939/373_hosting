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

**Status:** applied and verified, including AI browser review, October 26, 2026 EDT.
**Issue:** [#5](https://github.com/kaw393939/373_hosting/issues/5).
**PR:** [#6](https://github.com/kaw393939/373_hosting/pull/6).
**CI:** [passing hosting run](https://github.com/kaw393939/373_hosting/actions/runs/40431472341).
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
| Reviewed package candidates and actual installation result | 22 version-pinned upgrades applied at 01:04:12.687–01:08:05.223 UTC; APT exit 0, clean dpkg audit; no additions/removals/held packages |
| Reboot, running kernel, required services and ports | Issued 01:09:34 UTC; 01:11:55.705 UTC checks found expected kernel `6.8.0-147`, changed boot ID, no reboot marker/failed units, and required services/timers active |
| Public negative/private positive HOST-001 checks and site/release regressions | After packages and reboot: 13 public management paths returned 404, two tunneled checks returned 200, eight site baselines and five health/release results matched; AI browser review passed |
| Preservation | All 15 container identities/images and recorded health, port, and restart fields matched preflight; selected configuration files across six deployment directories and ACME hashes unchanged |

Docker 29.9.2, containerd 2.4.2, Compose 5.6.1, and Buildx 0.38.1 were verified.
An observer recorded sampled failure windows of approximately 55–103 seconds
during package updates and 80–122 seconds around reboot across three selected
health endpoints. These measurements do not describe every request or an SLA.
No health checks were relaxed. Live application containers/images were
preserved, and no production database was restored.

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

At maintenance completion, the separate chat restore PR's verification gate had
found an application dependency issue tracked in
[chat #44](https://github.com/kaw393939/is373-ai-chat/issues/44). That PR was
unmerged with its gate unchanged. [HOST-003](#host-003--companion-image-security-maintenance)
tracks the follow-up; host package updates do not patch preserved application images.

## HOST-003 · Companion image security maintenance

**Status:** application patch merged; main-candidate validation and deployment in progress.
**Owning issue:** [chat #44](https://github.com/kaw393939/is373-ai-chat/issues/44).
**Application PR:** [#46](https://github.com/kaw393939/is373-ai-chat/pull/46).
**Change record:** [certifi maintenance](book/changes/2026-10-26-certifi.md).

The chat application owns its locked dependencies, image tests, release and
deployment evidence. Its [dependency requirement](https://github.com/kaw393939/is373-ai-chat/blob/main/docs/requirements.md#dependency-security-maintenance)
and [canonical change record](https://github.com/kaw393939/is373-ai-chat/blob/main/docs/audit/2026-10-26-certifi.md)
define the scoped certifi correction and actual results; acceptance criteria stay
in the owning issue. Hosting infrastructure shall preserve unrelated routes,
certificates and services during the application release.

Distinguish the dependency scan, synthetic TLS checks, and the selected running
digest in development, QA and production. Retain the existing promotion gate
and record approval accurately; passing source checks alone does not establish
a patched deployment. Broader Python/build-tool trust scope stays in
[chat #45](https://github.com/kaw393939/is373-ai-chat/issues/45).
This cross-repository worked example adds no required student task or copied
application implementation here.
