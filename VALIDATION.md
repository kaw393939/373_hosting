# Validation record

The original classroom deployment behind this book used Ubuntu 24.04, Docker Engine 29.8.1, Traefik 3.7.13, and the official Apache `httpd:2.4-alpine` image. Five website hostnames returned their distinct welcome pages over trusted HTTPS; HTTP redirected to HTTPS. Its dashboard and API returned 200 without authentication after the instructor disabled the password. Six public certificates were issued. These are historical observations, not the desired dashboard policy.

The repository generalizes that deployment with replaceable hostnames. It does not export the live server's passwords, ACME state, or private keys.

Repository checks cover generator behavior, preservation of edited content and certificate state, invalid hostname rejection, shell syntax, and the generated Docker Compose model. CI repeats those checks without deploying public infrastructure. It does not test DNS-provider changes or request production certificates.

The installer follows the Docker repository commands used on the classroom server. A second clean VPS was not provisioned for this publication. Students should perform the complete public verification in Chapter 4 on their own host.

The checked-in complete example is compared against the generator in tests,
including every HTML page. CI validates the base Compose file, each optional
overlay, and both overlays combined. Overlay validation checks the merged model;
it does not request certificates or provision a password file. The optional
file-based Traefik configuration is an instructional equivalent of the base CLI
settings, not a change applied to the classroom server.

## HOST-001: private dashboard

The [specification](SPEC.md) and [worked change record](book/changes/2026-10-26-dashboard.md)
track [issue #3](https://github.com/kaw393939/373_hosting/issues/3). The revised
base model routes the dashboard/API only through a dedicated entry point,
published as `127.0.0.1:8082:8080`; administrators reach it through SSH. Dashboard
and API paths on selected public HTTPS origins must return 404 while websites
retain their redirects, trusted HTTPS, and content.

Repository verification completed before application:

- `python3 -m unittest discover -s tests -v`: 26 tests passed.
- `bash -n scripts/install-docker.sh` and `git diff --check`: passed.
- Generated, base example, file overlay, authentication overlay and combined
  Compose models: valid.
- `python3 scripts/smoke-dashboard.py`: a disposable real Traefik 3.7.13
  reproduced the public API failure despite `api.insecure=false`, then passed
  13 public denial and two private-access comparisons; its ordinary route
  still returned 200. No Docker socket or production infrastructure was used.
- Local Markdown links resolve.

The isolated check initially failed readiness because Traefik does not accept
a `.json` extension for its file provider. The fixture now uses `.yaml`
(JSON notation is valid YAML); the assertion was retained and rerun.

Live application completed October 26, 2026 EDT; final server checks were at
00:04 UTC on October 27. The owner authorized the change and established the
needed administrator authentication. The first ordinary SSH session alone did
not grant Docker administration.

- Reviewed source: [e45c6f9](https://github.com/kaw393939/373_hosting/commit/e45c6f990bb30ec465e6f9c6b08eb1d1586dd011),
  [passing CI](https://github.com/kaw393939/373_hosting/actions/runs/40423722648),
  [PR #4](https://github.com/kaw393939/373_hosting/pull/4).
- Before: 11 of 13 selected public paths returned 200; the two debug paths
  already returned 404. After readiness: all 13 returned 404 over trusted HTTPS.
- Positive: an SSH-key tunnel returned 200 for dashboard and version API;
  version 3.7.13. The live dashboard router used only `traefik`, with no TLS
  on that private entry point; host binding was exactly `127.0.0.1:8082`.
  An external TCP connection to that host port did not succeed.
- Eight website roots retained identical content hashes, trusted TLS and
  same-host HTTP-to-HTTPS redirects. Five health/release responses matched
  their pre-change selected fields exactly.
- Only Traefik was recreated. The other 14 container IDs and images were
  unchanged; all 15 containers were running, and Traefik was healthy with its
  original image ID. The installed Compose model equaled the planned model;
  ACME file bytes were unchanged. Protected on-host backups were retained.
- AI browser review: the tunneled dashboard rendered 14 enabled routers and
  16 enabled services, without warnings/errors. Its routing table showed
  `dashboard@docker` → `api@internal` on `traefik`, and calculator routing on
  `websecure`. The public dashboard showed `404 page not found`. The calculator
  returned 42 in both browser and API for 6 × 7, with “Results match.”

A tunnel probe started while recreation was still running returned transient
404s. It was not counted as success: after the migration's readiness check
completed, the same probe passed. No disabled fallback was needed. Signal and
failure recovery were tested locally, not deliberately triggered on production.
The observations above are AI/operator evidence, not a student's explanation
or a claimed human browser review. Private raw evidence and screenshots remain
outside Git; the sanitized dated record is the published teaching artifact.

Public request checks use trusted TLS on a configured website by default. An
existing dashboard origin can also be checked while its old certificate remains
valid; the private route no longer requests or renews that certificate. Selected
requests and configuration assertions provide different evidence, and neither
is a test of every possible public hostname.

## Companion integration

The application adapter is validated by rendering the actual companion Compose
file at a pinned revision in a separate CI job. Checks enforce its external
network, Host rule, port 8000 backend, retained updater policy, and loopback-only
administrative/development ports. No copy of the app source is maintained here.

The public-release checker has tests for stale commits and invalid HTTPS origins.
It checks the existing application's health contract without duplicating its
unit/API/browser tests. A rendered-model check is not an actual WUD update or
rollback rehearsal. No calculator container was deployed to the live classroom
server by this documentation/configuration update.

The subsequent user-authorized public deployment is recorded in
[the September 29 calculator deployment evidence](book/deployments/2026-09-29-calculator.md).
It includes the certificate-inheritance correction, trusted HTTPS release
verification, and seven browser checks against the live endpoint.

## HOST-002: recovery before maintenance

[HOST-002](SPEC.md#host-002--controlled-host-maintenance), [issue #5](https://github.com/kaw393939/373_hosting/issues/5)
and the [dated maintenance record](book/changes/2026-10-26-maintenance.md) track
this separately authorized operational cycle. Its pre-maintenance checks ran
October 26 EDT (October 27 UTC).

- The existing off-host chat backup passed authenticated decryption, strict
  archive/manifest checks, actual isolated PostgreSQL restoration and exact-image
  read-only ORM checks. [Chat PR #43](https://github.com/kaw393939/is373-ai-chat/pull/43)
  records the result; its independent key-custody/alert criteria remain open.
- The final fresh encrypted snapshot, created at 01:00:37.692 UTC, was copied
  off-host and verified at 01:01:21 UTC: ciphertext identity, authenticated age
  decryption, archive members and all 232 regular-file manifest hashes passed.
  Protected configuration was not extracted on the recovery computer.
- All three fresh PostgreSQL dumps restored into isolated test databases with
  schema 0003, fourteen expected tables and valid constraints. The exact running
  v2.0.0 image read every mapped row from each restored database; its counts
  matched those restored snapshots. Database phase: 2.906 seconds; snapshot age
  at database checks: 55.961 seconds. Both newly created containers were removed.
- Separate online SQLite backup/restoration passed integrity and foreign-key
  checks. All fourteen restored tables matched the selected snapshot's rows.
  A synthetic committed-WAL case verified the same online-backup mechanism.
- The new preflight recorded eight trusted-HTTPS site/content/redirect baselines
  and five health/release responses. Narrow effective SSH/UFW checks passed.
  No removed containerd configuration keys were found. APT metadata refreshed;
  simulation proposed 22 upgrades, no additions, removals or held packages.

These are bounded data/application-read rehearsals, not a full host rebuild,
source-live-row comparison, authentication/provider/mail restoration or recovery
of later writes. Private scripts, archives, raw inventories and database values
stay outside Git. The first archive review found a missing release-selection
file; the corrected final archive was regenerated and verified before maintenance.
The version-pinned 22-package installation ran from 01:04:12.687 to
01:08:05.223 UTC, exited 0, and passed `dpkg --audit`. It added or removed no
packages. Docker Engine 29.9.2, containerd 2.4.2, Compose 5.6.1 and Buildx 0.38.1
were verified. Local conffiles were preserved; selected deployment/ACME hashes
were unchanged.

Reboot was issued at 01:09:34 UTC. At 01:11:55.705 UTC, actual `uname` reported
expected kernel 6.8.0-147, the boot ID had changed, the reboot marker was gone,
required services/timers were active and no units had failed. All fifteen
container IDs/images, health, ports and restart policies matched preflight.
Eight site/content/redirect/TLS and five health/release baselines matched after
both package application and reboot. The thirteen public denials and two
SSH-tunnel successes passed again. External TCP checks could not reach the
three loopback management/app/updater ports.

AI browser review found matching browser/API calculator result 42 for 6 × 7;
the tunneled Traefik dashboard showed fourteen enabled routers and sixteen
services, with zero warnings/errors. These are operator observations, not
human acceptance or learner responses.

The external observer recorded 1,446 HTTPS samples across three health
endpoints. Sampled failure windows were 55.025–103.246 seconds during package
restart and 79.802–122.212 seconds around reboot. Transport failures and 404s
preceded healthy backends. These are approximate endpoint observations, not
full-traffic downtime or an availability guarantee. No healthcheck or gate
was weakened to obtain a pass.

At maintenance completion, the chat documentation PR's book check had passed
but its application vulnerability gate had failed for an existing locked certifi
dependency; that PR was unmerged. [HOST-003](#host-003-companion-image-security-maintenance)
tracks the follow-up to [chat #44](https://github.com/kaw393939/is373-ai-chat/issues/44).
Host maintenance preserved application images and did not patch their contents.

## HOST-003: companion image security maintenance

[The worked record](book/changes/2026-10-26-certifi.md) links the application
requirement, [PR #46](https://github.com/kaw393939/is373-ai-chat/pull/46) and
canonical evidence. Full candidate CI and live environment verification were
pending when this crosslink was drafted; no new deployment success is claimed
here. Hosting documentation checks validate these links/content, not the
application image, TLS behavior or production release. Record those results in
the owning application repository before claiming the running dependency is patched.
