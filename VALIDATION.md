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

Live application is pending. The first SSH session could read the deployment,
but Docker access was denied and noninteractive sudo required a password. The
owner subsequently established a privileged session. A successful SSH login
alone does not establish permission to recreate the proxy. Until the migration
is applied and its results are recorded, the observed public exposure remains
unresolved. Offline checks and an isolated container check cannot establish the
live server's final state.

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
