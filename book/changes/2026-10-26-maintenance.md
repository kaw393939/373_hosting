# HOST-002 · Verify recovery, update packages, and reboot

[Contents](../../README.md) · [Specification](../../SPEC.md#host-002--controlled-host-maintenance) ·
[Issue #5](https://github.com/kaw393939/373_hosting/issues/5) ·
[Validation](../../VALIDATION.md)

Data-recovery follow-through: [chat #4](https://github.com/kaw393939/is373-ai-chat/issues/4)
and [chat restore checks, PR #43](https://github.com/kaw393939/is373-ai-chat/pull/43).
The separate application SQLite recovery record remains in its owning private
repository; its private runtime identities are omitted here.

**Status:** recovery verification and bounded isolated restores passed;
package installation and reboot remain pending. This is an instructor's operational record, not an added
student exercise or permission to change another server.

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
Package changes and a host reboot can interrupt all hosted services;
record the start, return, and observed downtime of the bounded maintenance window.

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
violations, and matched all 14 table row counts against the selected snapshot.
Its backup method also passed a synthetic committed-WAL test. That fixture does
not establish live-source parity or add production observations.

**Result:** the bounded data/ORM restores passed. No full authenticated
application journey, complete host rebuild, public DNS/TLS recovery, or recovery
of newer writes is claimed. Configuration/certificate material verified in the
archive was not exercised as a full host restoration.

## 4 · Review and apply package updates

The refreshed plan contains **22 upgrades**, with no package additions,
removals, or held packages. Selected runtime candidates include:

| Package | Installed → candidate |
|---|---|
| Docker Engine | 29.8.1 → 29.9.2 |
| containerd | 2.3.6 → 2.4.2 |
| Docker Compose | 5.5.1 → 5.6.1 |
| Buildx | 0.37.1 → 0.38.1 |

Kernel `6.8.0-147` was already installed; no new kernel was a candidate. The
preflight found none of the removed containerd configuration keys. This stays
within Ubuntu 24.04; an OS release upgrade is outside the maintenance. Preserve
application images/releases, private management access, configuration, and data.

**Result:** candidate review passed; package installation is pending.

## 5 · Reboot and check the running result

Record the reboot and return times, running kernel, required service/container
state, and published ports. Compare selected public content and release/health
checks with the preflight. Repeat HOST-001's public dashboard/API denial and
private SSH dashboard/API access checks, then inspect a normal website.

**Result:** pending. A returned SSH session alone does not establish service
recovery. Record AI/operator terminal and browser observations separately from
any human observation; none supplies a learner response. Keep issue #5 open
until the agreed acceptance checks and any recovery actions are recorded.
