# 7 · Operate, extend, and recover

[Contents](../README.md) · [Next: assessment](08-assessment.md)

## Learning goals

Add a hostname without losing content, preserve recovery data, and distinguish restarting from updating.

## Add a site

Create its DNS record, append its hostname to `sites` in `hosting.json`, regenerate, review the Compose difference, and run `up -d`. Keep the existing site order stable if you want numeric service names to remain stable. Reapply any manual dashboard authentication additions before deployment.

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

For longer-lived use, add dashboard access controls, off-server backups, availability and certificate monitoring, deliberate patching, and stronger Docker API isolation. Databases need their own persistence and recovery design.

**Checkpoint:** state what a fresh clone restores and what only your backup restores.
