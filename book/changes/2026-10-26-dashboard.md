# HOST-001 · Make the dashboard private

[Contents](../../README.md) · [Specification](../../SPEC.md) ·
[Issue #3](https://github.com/kaw393939/373_hosting/issues/3) ·
[Validation](../../VALIDATION.md)

**Status on October 26, 2026 (EDT):** applied and verified on the live VPS.
Final checks completed October 27 at 00:04 UTC.
**Reviewed change:** [PR #4](https://github.com/kaw393939/373_hosting/pull/4).

## Try: observe the failure

The classroom Traefik 3.7.13 dashboard and API returned 200 to public requests
without credentials. HTTPS protected traffic in transit, but did not control
who could read routing and service metadata. The live Compose file is
`/opt/webserver/compose.yaml`, written in JSON notation; the production file and
its private state are not copied into this repository.

This is the worked failure: `api.insecure=false` was already present, yet an
explicit public router exposed `api@internal`. That setting alone never added
authentication or made the router private.

## Decide: save the requirement

[HOST-001](../../SPEC.md) records the decision linked to
[issue #3](https://github.com/kaw393939/373_hosting/issues/3): use existing SSH
access for management, with no new dashboard password. The private route uses
the `traefik` entry point at container port 8080 and host mapping
`127.0.0.1:8082:8080`. It matches both `/api` and `/dashboard`; public entry
points have no management route.

The intended result is specific: an administrator can inspect the dashboard
through SSH, dashboard/API paths on selected public HTTPS origins return 404,
and ordinary websites continue serving their existing content over HTTPS. Host processes and peer
containers remain within the trust boundary.

## Build: prepare a reviewable change

The [generator](../../scripts/configure.py),
[complete example](../../examples/full-stack/compose.yaml),
[static-file equivalent](../../examples/full-stack/traefik.yml), and
[public verifier](../../scripts/verify.py) carry the requirement into code.
[Chapter 5](../05-https-dashboard.md) gives the administrator's tunnel command.
The optional authentication overlay remains an extra check inside the tunnel.

An existing server needs a deliberate migration of its own Compose file using
the [migration tool](../../scripts/restrict-dashboard.py).
Preserve a protected backup and review the difference; keep images, mounts,
ACME state, network identity, and application containers unchanged. Recreating
only the proxy briefly interrupts all gateway traffic. Recovery must restore
website routing while keeping public management access closed.

## Check: distinguish preparation from live evidence

AI checks must cover the generated model, the verifier's expected failure
cases, and an isolated real-Traefik routing check. Their actual commands and
results will be recorded in [VALIDATION.md](../../VALIDATION.md). A model test
can establish that the loopback mapping is generated; it cannot establish that
a particular VPS is running it.

The owner authorized the operational correction and established administrator
authentication. An ordinary SSH login alone had not granted Docker access.
A protected on-host archive saved the existing Compose file and certificate
state. The deployed helper was byte-identical to reviewed
[commit e45c6f9](https://github.com/kaw393939/373_hosting/commit/e45c6f990bb30ec465e6f9c6b08eb1d1586dd011),
after [CI passed](https://github.com/kaw393939/373_hosting/actions/runs/40423722648).
The migration required the reviewed original Compose SHA-256 and recreated only
Traefik, without pulling or building an image.

| Case | Actual result after readiness |
|---|---|
| Negative: 13 management/debug paths on former public dashboard origin | All 404 over trusted HTTPS; 11 had returned 200 before |
| Positive: SSH tunnel to dashboard and version API | Both 200; version 3.7.13 |
| Structural runtime check | `dashboard@docker` used only `traefik`; exact loopback mapping; external port connection unavailable |
| Website regression | Eight roots retained content hashes, redirects and trusted HTTPS; five health/release results unchanged |
| Preservation | Only proxy recreated; other 14 container IDs/images unchanged; proxy image and ACME bytes unchanged |
| AI browser observation | 14 enabled routers, 16 enabled services; no warnings/errors; public dashboard showed 404; calculator 6 × 7 returned matching browser/API 42 |

A probe made while recreation was still running returned temporary private
404s. Wait for the migration's readiness result before interpreting the final
check; the same probe passed afterward. No recovery fallback was needed.
Locally, an interrupted apply was tested to attempt a disabled-dashboard
fallback; SIGKILL, power loss and full host recovery were not tested.

The existing dashboard certificate was still valid for the public negative
check. New deployments use a website origin with trusted TLS; the private
route does not request or renew a dashboard hostname certificate. Selected
requests complement configuration checks and do not prove every hostname or
isolate trusted host processes and peer containers.

These browser/terminal findings are AI/operator observations, not invented
student responses or a claimed human review. Raw private evidence and
screenshots remain outside Git. Full commands, check scope and results are in
[VALIDATION.md](../../VALIDATION.md).

## Keep: close the loop with evidence

The live results satisfy HOST-001. The requirement, implementation, tests,
[issue #3](https://github.com/kaw393939/373_hosting/issues/3), and
[PR #4](https://github.com/kaw393939/373_hosting/pull/4) form one reviewable change.
This is an instructor's separately authorized operational example. The IS373
student documentation exercise remains read-only on the existing server.
