# 4 · Generate and deploy the hosting stack

[Contents](../README.md) · [Next: HTTPS](05-https-dashboard.md)

## Learning goals

Create five distinguishable websites, inspect a Compose model, and verify that requests reach the intended container.

Copy the settings and replace the example values:

```bash
cp examples/hosting.example.json hosting.json
nano hosting.json
```

`email` is the certificate account contact, `dashboard` is the management hostname, and `sites` is the ordered list of website hostnames. Use lowercase names without `https://`, slashes, or wildcards. The generator rejects duplicates, including a dashboard name reused as a website.

```bash
python3 scripts/configure.py --config hosting.json --output runtime
sudo docker compose -f runtime/compose.yaml config --quiet
less runtime/compose.yaml
sudo docker compose -f runtime/compose.yaml up -d
sudo docker compose -f runtime/compose.yaml ps
```

The generated `compose.yaml` uses JSON syntax, which Compose accepts as YAML-compatible input. This keeps the generator dependent only on Python's standard library. All relative bind mounts resolve beside that Compose file, inside `runtime`.

The first launch downloads images. Traefik needs to discover containers and pass its health check before its own dashboard route appears. A short startup delay is normal. Follow progress with:

```bash
sudo docker compose -f runtime/compose.yaml logs --tail=100 -f traefik
```

Press Ctrl-C to stop following logs; this does not stop the containers.

## What the generator preserves

Running the generator again replaces the generated Compose model but **does not overwrite existing welcome pages or certificate data**. It tightens permissions on the certificate directory and file. If Docker-owned files prevent regeneration, use sudo for the generator and continue editing as an administrator.

Manual edits to Compose, including the optional authentication configuration in Chapter 5, must be reapplied after regeneration. Keep a copy before experimenting. Removed hostname directories remain on disk; review them before deleting anything.

## Customize a page

Edit a hostname's `index.html` on the VPS:

```bash
nano runtime/sites/example.com/index.html
```

Replace the hostname with your configured name. Add your name, the course number, and a short explanation of reverse proxies. Refresh the website. You do not need to rebuild an image or restart Apache for a bind-mounted HTML change.

Run the verifier from the repository directory:

```bash
python3 scripts/verify.py --config hosting.json
```

It checks DNS resolution, the HTTP redirect, trusted TLS, and the expected hostname in each website's response. Its expected dashboard response is 200 because this lab starts without authentication. If you later enable authentication, a dashboard 401 is intentional. Keep the hostname in your page when using this verifier.

Also run the verifier from your laptop, using a local copy of the configuration, to test the public route rather than only the server's network view.

**Checkpoint:** each website returns its own hostname; HTTP redirects to HTTPS; the dashboard loads. Save these results as evidence, never certificate private keys.
