# HOST-002 · Verify recovery, update packages, and reboot

[Contents](../../README.md) · [Specification](../../SPEC.md#host-002--controlled-host-maintenance) ·
[Issue #5](https://github.com/kaw393939/373_hosting/issues/5) ·
[Validation](../../VALIDATION.md)

Data-recovery follow-through: [chat #4](https://github.com/kaw393939/is373-ai-chat/issues/4)
and [chat restore checks, PR #43](https://github.com/kaw393939/is373-ai-chat/pull/43).
The separate application SQLite recovery record remains in its owning private
repository; its private runtime identities are omitted here.

**Status:** recovery, updates, reboot, and AI terminal/browser checks passed
on October 26, 2026 EDT (October 27 UTC). This is an instructor's operational record, not an added
student exercise or permission to change another server.
**Reviewed change:** [PR #6](https://github.com/kaw393939/373_hosting/pull/6) ·
[passing hosting CI](https://github.com/kaw393939/373_hosting/actions/runs/40430799758).

## 1 · Establish the preflight and recovery scope

The October 26 EDT preflight (October 27 UTC) observed Ubuntu 24.04.5, kernel
`6.8.0-146` running with `6.8.0-147` installed, and a reboot marker. All 15
containers were running; the proxy and application services reported healthy.
APT metadata was subsequently refreshed and the candidates reviewed below. The prior
[HOST-001 record](2026-10-26-dashboard.md) supplies a dated successful baseline,
not a substitute for the new preflight.

Preflight also checked effective access policy: SSH root/password login was
disabled and public-key authentication enabled; UFW allowed only TCP 22/80/443
for IPv4 and IPv6. Docker-published bindings remain a separate check.
Package changes and a host reboot can interrupt all hosted services. The actual
operation times and sampled interruptions are recorded below.

| Recovery input | Scope | Current result |
|---|---|---|
| Existing encrypted chat backup | Earlier daily archive, aged 17.90 hours at restore, within its 36-hour window | Decryption and isolated database/ORM restoration passed |
| Fresh pre-maintenance snapshot | Three PostgreSQL dumps, six deployment configurations including `release.env`, proxy ACME/sites, application project files, and selected SSH/UFW/Docker/containerd/netplan configuration | Off-host identity, authenticated decryption, manifest/path coverage, and hashes passed |
| Separate application SQLite data | Consistent selected snapshot | Isolated integrity/foreign-key/table comparisons passed; details remain private |

These are distinct recovery inputs. An old chat archive cannot establish that
the separate application's current SQLite data or proxy state is recoverable. Keep actual archives,
SQLite data, credentials, decryption material, and raw manifests outside Git.

## 2 · Verify the off-host artifacts

The final snapshot was taken at **2026-10-27 01:00:37.692004 UTC** and verified
off-host at **01:01:21 UTC**. The encrypted artifact was 1,997,480 bytes. Its
copy identity, `age` authenticated decryption, all **232 regular-file hashes**,
and strict archive-path/manifest checks passed. Protected configuration files
were not extracted on the Mac.

A coverage check found a missing release-selection file (`release.env`) in the
initial snapshot. The backup was corrected and regenerated before maintenance.
This was a coverage failure despite an otherwise readable archive; hashing alone
could not establish that the needed file was included.

**Result:** passed for the recorded artifacts and scope. Readable, matching
artifacts do not establish usable restored applications or include later writes.

## 3 · Restore into an isolated target

The earlier daily chat archive passed an isolated 14-table database and ORM
check: the database phase took 1.929 seconds and completed at 00:54 UTC; the
overall trial completed at **00:55:31 UTC**.

The fresh production, development, and QA PostgreSQL dumps each restored
schema `0003` and 14 tables, with valid constraints, read-only SQL checks, and
ORM reads using the exact v2 application image. Database checks completed at
**01:01:33.652959 UTC**, when the snapshot was **55.961 seconds old**. The
database phase including initialization took **2.906 seconds**; the complete
harness took **28.540 seconds**. Both disposable containers were removed.

The separate SQLite restore passed integrity checks, had zero foreign-key
violations, and matched the complete rows in all 14 tables against the selected snapshot.
Its backup method also passed a synthetic committed-WAL test. That fixture does
not establish live-source parity or add production observations.

**Result:** the bounded data/ORM restores passed. No full authenticated
application journey, complete host rebuild, public DNS/TLS recovery, or recovery
of newer writes is claimed. Configuration/certificate material verified in the
archive was not exercised as a full host restoration.

## 4 · Review and apply package updates

The final exact-version simulation contained **22 upgrades**, with no package
additions, removals, or held packages. The reviewed version-pinned set was
installed from **01:04:12.687 to 01:08:05.223 UTC** on October 27 using
`apt-get install --only-upgrade --no-remove`, with
`APT::Get::Upgrade-Allow-New=false` and `Dpkg::Options::=--force-confold`.
APT exited 0 and `dpkg --audit` was clean. Verified runtime versions were:

| Package | Before → verified after |
|---|---|
| Docker Engine | 29.8.1 → 29.9.2 |
| containerd | 2.3.6 → 2.4.2 |
| Docker Compose | 5.5.1 → 5.6.1 |
| Buildx | 0.37.1 → 0.38.1 |

Kernel `6.8.0-147` was already installed; no new kernel was a candidate. The
preflight found none of the removed containerd configuration keys. The operation
stayed within Ubuntu 24.04; no OS release upgrade occurred.

**Result:** installation passed. All 15 container identities/images and recorded
health, port, and restart fields matched preflight. Six selected deployment
configuration hashes and ACME bytes were unchanged. No replacement application images were pulled on the VPS and no live
application containers were recreated. Health checks were not relaxed and
production databases were not restored.

## 5 · Reboot and check the running result

Reboot was issued at **01:09:34 UTC**. At **01:11:55.705 UTC**, the host ran
the expected kernel `6.8.0-147`, its boot ID had changed, and the reboot marker
was absent. Docker, containerd, SSH, fail2ban, UFW, and unattended upgrades were
active, as were chat backup and metrics timers. No failed units were reported.
All 15 containers retained their identities/images and recorded health, port,
and restart fields; selected configuration/ACME hashes were still unchanged.

After both package installation and reboot, eight public sites retained exact
content hashes, same-host redirects, and trusted TLS; five health/release
results matched preflight. All 13 selected public management paths returned
404, while the tunneled dashboard and version API returned 200: all 15 access
comparisons passed. Applications became healthy after warmup.

An observer collected **1,446 samples**, including **423 non-200 results**,
across three selected health endpoints. Approximate sampled failure-window
lengths ranged from **55.025–103.246 seconds** during package updates and
**79.802–122.212 seconds** around reboot. It observed HTTP 404 and transport
unavailability before backends became healthy. These endpoint sample windows
are not exact downtime for all traffic or a service-level guarantee; reboot
command-to-check time is also not a downtime measurement.

**Result:** host and HTTP checks passed. AI browser review passed: calculator browser/API both returned 42 for 6 × 7;
the private dashboard showed fourteen enabled routers and sixteen enabled
services, with zero warnings/errors. These
operator checks are separate from human observations and learner responses.
The 2.906-second database restoration measured the small selected snapshot;
it does not establish full host recovery time.

## Separate application dependency finding

The chat restore PR's book check passed, but its verification gate rejected
`certifi 2026.7.22` for `GHSA-6q48-6c7w-9gw2`.
[Chat issue #44](https://github.com/kaw393939/is373-ai-chat/issues/44) tracks the
recommended update to `2026.10.19` or later. PR #43 remains unmerged and the
gate remains unchanged. This is separate from the passed host maintenance:
preserved application images retain their own dependencies, which host package
updates do not patch.
