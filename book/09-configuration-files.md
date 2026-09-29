# 9 · Read the configuration files

[Contents](../README.md) · [Complete files](../examples/full-stack/README.md)

## Learning goals

Identify every file needed to run the lab, distinguish configuration from runtime
state, and trace a Compose setting to the behavior it controls.

The runnable stack has one Compose model, one content directory per website,
and a persistent certificate directory. The [complete example](../examples/full-stack/compose.yaml)
is checked into GitHub, so you can inspect it without running the generator.
It uses JSON notation accepted by Compose; the optional overlays use conventional
YAML. Both describe the same types of mappings and lists.

## File lifecycle

```text
hosting.json                     Student's input to the generator
    |
    +--> runtime/compose.yaml    Docker's application model
    +--> runtime/sites/...      Apache content, safe to customize
    +--> runtime/letsencrypt/    Private state written by Traefik

Optional file-based variant:
compose.yaml + compose.file-config.yaml + traefik.yml

Optional password variant:
compose.yaml + compose.auth.yaml + credentials/dashboard.htpasswd
```

The example copies contain reserved hostnames and an example email. Real private
keys and password hashes are never necessary teaching material; students create
their own locally. `.gitignore` keeps generated deployments, local settings, and
certificate/password files out of normal commits.

## Compose: top-level settings

| Field | Why it exists |
|---|---|
| `name: hosting373` | Groups these containers into one Compose project |
| `services` | Declares one proxy and five separate Apache processes |
| `networks.web.name: hosting-web` | Gives the shared bridge a predictable Docker name |

The key `web` under `networks` is a Compose reference. The actual network name
`hosting-web` is what Traefik's Docker provider is told to use. A mismatch can
leave a router visible while its backend cannot be reached.

## Traefik container

| Field | Effect |
|---|---|
| `image` | Selects the pinned Traefik release |
| `restart: unless-stopped` | Restarts after failures/daemon startup unless deliberately stopped |
| `ports` | Publishes only host TCP 80 and 443 |
| Docker socket mount | Lets Traefik discover container labels and addresses |
| Certificate directory mount | Keeps account and certificate state across recreation |
| `healthcheck` | Calls Traefik's internal ping command to report readiness |
| `logging` | Caps each container's Docker log history |
| `security_opt` | Prevents gaining additional privileges through mechanisms such as setuid |

The socket is an administrative interface: the `:ro` mount does not turn its API
into a restricted read-only API. No Docker daemon port is published by this stack.

## Static Traefik settings: CLI or a file

The base Compose `command` list configures startup behavior. The commented
[traefik.yml](../examples/full-stack/traefik.yml) expresses the same settings as a
separate file. The [file overlay](../examples/full-stack/compose.file-config.yaml)
replaces the CLI list with one `--configFile` argument and mounts that file.

| Setting group | Responsibility |
|---|---|
| `api` | Enables dashboard inspection; disables a separate insecure listener |
| `providers.docker` | Discovers explicitly enabled containers on the selected network |
| `entryPoints.web` | Listens on 80 and redirects normal HTTP traffic to HTTPS |
| `entryPoints.websecure` | Listens on 443 and applies the default TLS resolver |
| `certificatesResolvers.letsencrypt.acme` | Sets contact email, persisted storage, and HTTP-01 validation |
| `ping`, `log`, `accessLog` | Provides health and operational visibility |

Static settings describe how Traefik starts. Dynamic Docker labels describe which
applications it routes to. Changing a mounted static file requires restarting
Traefik; changes to Compose must be applied with `up -d`.

## Dynamic routing labels

Inspect `site-1` in the Compose file:

| Label | Meaning |
|---|---|
| `traefik.enable=true` | Opt this container into discovery |
| `traefik.http.routers.site-1.rule` | Match the requested hostname |
| `traefik.http.routers.site-1.entrypoints=websecure` | Accept website traffic through HTTPS |
| `traefik.http.services.site-1.loadbalancer.server.port=80` | Forward to Apache's internal port |

There is one declared backend service for each website router; Traefik can infer
that association. Router/service names must stay unique as you add applications.
The dashboard router instead explicitly selects `api@internal`, Traefik's own
inspection service. It does not need an Apache container.

## Apache and the HTML files

The official `httpd` image already contains a working `httpd.conf` that listens on
port 80 and serves `/usr/local/apache2/htdocs`. This lab does not need a custom
Apache configuration or a Dockerfile. Each service mounts its own host directory
over that document root; the five [HTML copies](../examples/full-stack/sites/)
show exactly what is served.

To inspect the version-specific Apache defaults on a running lab:

```bash
sudo docker compose -f runtime/compose.yaml exec site-1 cat /usr/local/apache2/conf/httpd.conf
sudo docker compose -f runtime/compose.yaml exec site-1 httpd -t
```

This avoids presenting a partial default file as if it were a required custom
configuration. Edit host HTML files to change content; edit Compose to change
which directory is mounted. No Apache virtual-host file is needed because each
website gets its own container and Traefik does hostname selection.

## Files that belong outside the repository

`acme.json` is populated by Traefik, not hand-authored. Its empty-file preparation
is documented beside the [certificate directory](../examples/full-stack/letsencrypt/README.md).
A password file is optional and generated locally with `htpasswd`. There is no
`.env` requirement in this design: the generator's input is `hosting.json`, and
the static copies use explicit values.

The host's APT source, firewall rules, and provider DNS records are explained in
the [host configuration examples](../examples/host-config/README.md). These files
are not mounted into the web containers.

## Exercise

Without starting containers, find the setting responsible for each behavior:

1. Visiting HTTP redirects to HTTPS.
2. Editing one welcome page changes only one website.
3. An unlabelled container is not published automatically.
4. Restarting Traefik preserves certificates.
5. Adding the authentication overlay makes the dashboard return 401 without credentials.

Then validate both static configuration methods with `docker compose config` and
compare their merged models. They should have the same five Apache services and
router labels, but different Traefik commands and config mounts.
