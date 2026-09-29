# Live calculator deployment · September 29, 2026

Public URL: [calc.mywebclass.org](https://calc.mywebclass.org).

## Release and placement

- Application commit: `334877c00690464c15892999ed22b4279b857cd7`.
- Passing native tests and publication: [workflow 36615046705](https://github.com/kaw393939/is373_ci_cd/actions/runs/36615046705).
- Published index: `kaw393939/is373_ci_cd@sha256:a77d4a96cb2c9a08d129a411c66be442cba62b39ba1f6aa1386557adbf986c5a`.
- The running container's inspected image ID also reported `sha256:a77d4a96cb2c9a08d129a411c66be442cba62b39ba1f6aa1386557adbf986c5a` on this Docker installation.
- Application checkout: `/opt/is373_ci_cd`; hosting reference checkout: `/opt/373_hosting`.
- Production container: `is373-ci-cd-prod-1`, attached to `is373-ci-cd_default` and the existing proxy network `web`.
- Local deployment configuration: `APP_HOST=calc.mywebclass.org`, `TRAEFIK_NETWORK=web`.

The wildcard DNS record resolved the hostname to the intended VPS. No DNS record
change or replacement of an Apache welcome page was required. `make deploy`
started the published application and WUD without starting development.

## Certificate correction discovered during deployment

The initial adapter explicitly set the router's `tls=true`. On this Traefik
configuration that created router TLS options without inheriting the entry-point
certificate resolver. The API showed `tls.options=default` but no resolver, and
the public endpoint presented the default self-signed certificate.

Removing that label let the existing `websecure` entry-point defaults apply.
The router then reported `certResolver=letsencrypt`; HTTP-01 validation completed
and the public hostname received a trusted certificate. The checked-in adapter
and integration validator were corrected accordingly.

## Observed verification

- `make verify-production` passed image identity and health checks.
- Public HTTPS `/health` reported production, status `ok`, and the expected full commit.
- The public release checker passed with normal certificate verification.
- HTTP redirected to HTTPS (308 observed).
- All seven existing Playwright browser tests passed against the live HTTPS URL
  in 3.10 seconds, including calculation, input errors, decimal handling, and
  the narrow-screen/keyboard path. API-failure and mismatch cases were simulated
  in the test browser only; the production server was not modified by those tests.
- WUD's authenticated local API listed exactly one watched container:
  `is373-ci-cd-prod-1`. Its dashboard remains bound to loopback port 8091.
- The five existing welcome-page hostnames returned 200; Traefik's root returned
  its dashboard redirect.

This records the initial public deployment. A second automatic update and a live
rollback/resume rehearsal have not been performed as part of this deployment.
Future releases may change the running commit; the details above are a dated
observation, not a claim that production always runs this version.
