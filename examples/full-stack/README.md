# Complete example files

This directory is a **checked-in copy of the entire generated example stack**. Browse the files directly on GitHub before running any scripts. The hostnames are reserved examples; replace them with domains you own before deployment.

## Required files

| File | Purpose | Who creates it? |
|---|---|---|
| [compose.yaml](compose.yaml) | Declares Traefik, five Apache containers, mounts, ports, routes, and the shared network | Checked-in teaching copy; normally the generator |
| [example.com/index.html](sites/example.com/index.html) | First apex site's welcome page | Generator, then you edit it |
| [www.example.com/index.html](sites/www.example.com/index.html) | First `www` site's page | Generator, then you edit it |
| [dev.example.com/index.html](sites/dev.example.com/index.html) | Development site's page | Generator, then you edit it |
| [example.org/index.html](sites/example.org/index.html) | Second apex site's page | Generator, then you edit it |
| [www.example.org/index.html](sites/www.example.org/index.html) | Second `www` site's page | Generator, then you edit it |
| `letsencrypt/acme.json` | Persistent private certificate/account state | Empty file prepared locally; populated by Traefik |

[hosting.example.json](../hosting.example.json) supplies the generator's email and hostname inputs. It is **not** read by Docker or Traefik. The normal workflow copies it to ignored `hosting.json` and creates an ignored `runtime` directory. This teaching directory stays unchanged so students can compare their work with the reference.

## Configuration variants

Use the base Compose file by itself first. These optional files show two deliberate extensions:

- [traefik.yml](traefik.yml) is a complete file-based equivalent of the base Compose `command` options, with comments.
- [compose.file-config.yaml](compose.file-config.yaml) replaces the command list with a config-file argument and mounts `traefik.yml`. It is an overlay, not a standalone stack.
- [compose.auth.yaml](compose.auth.yaml) adds dashboard authentication using a locally created password hash file. It too is an overlay.

Do not copy options into both CLI flags and the static Traefik configuration. Select one static configuration method. Dynamic routing labels remain in Compose in either method.

## Manual deployment exercise

On a fresh server prepared through Chapters 2–3, run from the repository root:

```bash
cp -R examples/full-stack runtime-manual
cd runtime-manual
```

Edit `compose.yaml`: replace all five website names and the dashboard hostname in the Host rules, replace the email in the ACME option, and edit each welcome page. You can keep the example directory names as local folder names; the bind mount, not the directory's spelling, determines which content a container serves. If you rename folders, update their mount paths too.

Prepare certificate storage without truncating an existing file:

```bash
install -d -m 700 letsencrypt
touch letsencrypt/acme.json
chmod 600 letsencrypt/acme.json
sudo docker compose config --quiet
sudo docker compose up -d
```

This is an alternative to the generated deployment, not a second stack to start alongside it. Both use ports 80/443, project `hosting373`, and network `hosting-web`.

### Use a separate Traefik configuration file

Edit the contact email in `traefik.yml` as well as your Host rules in Compose, then use:

```bash
sudo docker compose -f compose.yaml -f compose.file-config.yaml config --quiet
sudo docker compose -f compose.yaml -f compose.file-config.yaml up -d
```

Compose replaces the service's `command` with the overlay's command and adds the config-file mount. Use the same `-f` list for subsequent management commands so Compose sees the same model.

### Add dashboard authentication

Create the hash locally, using an interactive password prompt:

```bash
sudo apt-get install -y apache2-utils
sudo install -d -m 700 credentials
sudo htpasswd -cB credentials/dashboard.htpasswd admin
sudo chmod 600 credentials/dashboard.htpasswd
sudo docker compose -f compose.yaml -f compose.auth.yaml config --quiet
sudo docker compose -f compose.yaml -f compose.auth.yaml up -d
```

The `-c` flag creates/replaces the password file; omit it when changing a user in an existing file. To combine both extensions, include all three files, with the base first:

```bash
sudo docker compose -f compose.yaml -f compose.file-config.yaml -f compose.auth.yaml up -d
```

The base example has no password, matching the initial classroom lab. The authentication overlay protects both the dashboard and its API through the same router.

## Other machine-level files

[Host configuration examples](../host-config/README.md) show the Docker APT source, firewall commands, and DNS record worksheet. These are applied to the host or DNS provider, not mounted into a container.

For a detailed field-by-field walkthrough, read [Chapter 9: configuration files](../../book/09-configuration-files.md).
