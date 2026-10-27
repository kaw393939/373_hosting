# 7 · Operate, extend, and recover

[Contents](../README.md) · [Next: assessment](08-assessment.md)

## Learning goals

Add a hostname without losing content, preserve recovery data, and distinguish restarting from updating.

## Add a site

Create its DNS record, append its hostname to `sites` in `hosting.json`, regenerate, review the Compose difference, and run `up -d`. Keep the existing site order stable if you want numeric service names to remain stable. If you enabled the optional dashboard authentication overlay, retain its `-f` argument in every Compose command.

If you remove a site from the list, Compose does not automatically remove every old container. After reviewing the removed services, use `up -d --remove-orphans` to remove containers no longer declared by this project. The old page directory remains available for recovery.

To attach a different application, put its container on `hosting-web`, enable Traefik for that service, give its router a unique name and Host rule, select `websecure`, and label its actual internal service port. Do not publish that application's port directly on the VPS. A wildcard DNS record removes repetitive DNS work, not the need to configure a router.

## Restart versus update

```bash
sudo docker compose -f runtime/compose.yaml restart
sudo docker compose -f runtime/compose.yaml ps
```

Restart uses existing containers and images. It does not apply a changed Compose model. Use `up -d` after configuration changes. To update a mutable image tag, back up first, review upstream changes, then run:

```bash
sudo docker compose -f runtime/compose.yaml pull
sudo docker compose -f runtime/compose.yaml up -d
python3 scripts/verify.py --config hosting.json
```

The pinned Traefik version changes only when you deliberately edit its image reference. Record old image digests before an upgrade so rollback has a precise target. Docker package updates through APT and Ubuntu security updates are separate from container image updates.

## Update an existing public dashboard

Pulling repository changes does not change a running deployment:

```bash
git pull --ff-only
```

Read [HOST-001](../SPEC.md) and its [worked migration record](changes/2026-10-26-dashboard.md)
before changing an existing server. Preserve a private backup of its actual
Compose file and certificate state; do not overwrite a customized deployment
with the reserved example configuration. SSH login and Docker administration
are separate permissions. The administrator applying this change needs working
`sudo docker` access.

The dashboard migration recreates only Traefik, causing a brief interruption to
all traffic using that proxy. It must preserve image references, mounts, ACME
state, network identity, and application containers. After application, check
the SSH tunnel, public dashboard/API denial, and ordinary public sites before
recording success. If recovery is needed, keep management access closed while
restoring website routing; do not blindly restore the exposed dashboard route.

For the existing JSON-format deployment, run the
[migration tool](../scripts/restrict-dashboard.py) on the server first without
`--apply`:

```bash
python3 scripts/restrict-dashboard.py --compose /opt/webserver/compose.yaml
```

Review its proposed changes and source SHA-256. This dry run reads that file;
it is not an inventory of running containers. With Docker administrator access,
replace `REVIEWED_SHA256` with the reviewed hash and apply:

```bash
sudo python3 scripts/restrict-dashboard.py --apply --compose /opt/webserver/compose.yaml --expected-sha256 REVIEWED_SHA256
```

The tool requires an unchanged source file, creates a private Compose backup,
validates the candidate, and recreates only the proxy. Its recovery path keeps
management access closed. Record the actual result and rerun the public/private
checks; the current classroom migration is still pending.

## Backup exercise

The critical data are your site directories, Compose configuration, local settings, ACME account/certificates, and any dashboard password hash. A Git clone alone cannot restore those ignored files.

For a simple consistent lab backup, stop the stack briefly, archive the runtime, then start it again. This causes a short outage. Run from the repository directory:

```bash
sudo install -d -m 700 /var/backups/hosting373
sudo docker compose -f runtime/compose.yaml stop
sudo sh -c 'umask 077; tar -czf /var/backups/hosting373/backup-$(date -u +%Y%m%dT%H%M%SZ).tar.gz runtime hosting.json'
sudo docker compose -f runtime/compose.yaml up -d
```

If the archive command fails, start the stack again before investigating the backup failure. Copy the archive to protected off-server storage; a backup on the same VPS does not protect against losing the VPS. Encrypt backups before placing them in shared storage. Never upload these archives to GitHub.

Practice restoration to a separate machine: extract into a private directory, check permissions, validate Compose, arrange DNS/certificate routing, start services, and rerun verification. Do not run two public servers competing for the same domain without planning the cutover.

## Operational boundaries

Log files rotate at three files of 10 MB per container. This limits disk growth but is not centralized monitoring. Restart policies restore containers after daemon startup unless they were deliberately stopped. A reboot test is a useful scheduled lab exercise, not proof of high availability.

For longer-lived use, maintain SSH access controls, off-server backups, availability and certificate monitoring, deliberate patching, and stronger Docker API isolation. The dashboard's loopback binding does not isolate it from trusted host processes or peer containers. Databases need their own persistence and recovery design.

**Checkpoint:** state what a fresh clone restores and what only your backup restores.
