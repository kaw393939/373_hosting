# HOST-001 · Make the dashboard private

[Contents](../../README.md) · [Specification](../../SPEC.md) ·
[Issue #3](https://github.com/kaw393939/373_hosting/issues/3) ·
[Validation](../../VALIDATION.md)

**Status on October 26, 2026:** the repository change is staged for review.
The live migration and final observations are pending.

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

Live application has not occurred. The first SSH login succeeded, but that user
could not access Docker and noninteractive sudo required a password. The owner
subsequently established a privileged session. The distinction matters: SSH
connectivity alone did not grant authority to recreate the proxy. The historical
public exposure remains unresolved until the change is applied and verified.

After application, check a positive case through the SSH tunnel and negative
cases against the former public dashboard origin while its certificate is valid.
New deployments use a website origin with trusted TLS; the private route does
not request or renew a dashboard hostname certificate. Selected requests
complement configuration checks and do not prove every possible hostname.
Check ordinary site redirects, TLS, and content as regressions.
Positive/negative describe expected outcomes;
unit, integration, and live/browser checks describe where the check runs.

The administrator's browser observation is still pending: open the tunneled
dashboard, identify an actual router and service, and confirm an ordinary
public website still looks and behaves as expected. Record what was observed;
do not substitute an invented learner response or screenshot.

## Keep: close the loop with evidence

Retain the change and close the issue only after the live results satisfy
HOST-001. Link the reviewed change, actual check results, and administrator
observation back to the specification and issue. Until then, this record is a
prepared correction with an explicit deployment gap.
