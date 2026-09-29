# Certificate storage

The Compose bind mount maps this directory to `/letsencrypt` in Traefik.
Before first startup, create an **empty** `acme.json` and set mode 600:

```bash
touch letsencrypt/acme.json
chmod 600 letsencrypt/acme.json
```

Run from the directory containing Compose. `touch` preserves existing contents.
Traefik writes account registration, private keys, and certificates here. Those
values are runtime state, not public configuration. No real or fake account key
is included in this repository. Do not manually create an account JSON structure.

The file must survive container replacement. Back it up securely and never add
it to Git; the repository's ignore rules exclude it.
