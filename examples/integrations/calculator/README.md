# Calculator routing adapter

This is the hosting-owned adapter for the separate
[is373_ci_cd application](https://github.com/kaw393939/is373_ci_cd).
It contains no copy of the app, Dockerfile, test suite, or release workflow.

| File | Destination | Role |
|---|---|---|
| [compose.traefik.yaml](compose.traefik.yaml) | App checkout's `compose.override.yaml` | Connect only `prod` to the shared external network and public Host rule |
| [.env.example](.env.example) | App checkout's `.env` | Choose hostname and existing Docker network |

Read [Chapter 10](../../../book/10-application-delivery.md) for the complete
procedure. The overlay is not a standalone Compose application. Merge it with
the app's `compose.yaml`, never with the hosting stack's Compose file.

The app retains its local-only 8090 port for release verification. No new public
host port is added. The existing proxy supplies the `websecure` entry point and
its default Let's Encrypt resolver. WUD and development stay on the app's
default network without public routing labels. The proxy network must already
exist; `external: true` makes a missing network an explicit deployment failure.

The standard hosting generator calls the network `hosting-web`. The earlier
classroom server uses `web`; set `TRAEFIK_NETWORK=web` there. A label explicitly
selects that network so Traefik does not choose the app's other network.

The application Make interface must support the optional override and
production-only `make deploy`; this is implemented by
[application PR #29](https://github.com/kaw393939/is373_ci_cd/pull/29).
Use a release that contains those changes. Historical ARM64-only images do not
work natively on an AMD64 VPS.
