# 3 · Install Docker and understand its parts

[Contents](../README.md) · [Next: deployment](04-deploy.md)

## Learning goals

Install Docker from its official repository and distinguish persistent files from disposable containers.

`apt-get update` refreshes the package catalog. It does not upgrade every installed package. The installer then adds Docker's signed APT repository and installs Docker Engine, its CLI, containerd, Buildx, and the Compose plugin. It enables Docker at boot and runs the small `hello-world` smoke test.

After cloning this repository on the VPS, read and execute the installer:

```bash
less scripts/install-docker.sh
sudo bash scripts/install-docker.sh
sudo systemctl status docker --no-pager
sudo docker version
sudo docker compose version
```

The script deliberately stops on unsupported Ubuntu releases or conflicting distribution packages. Removing an existing container runtime can disrupt workloads, so it does not remove one automatically. It uses the [official Docker APT installation method](https://docs.docker.com/engine/install/ubuntu/).

If APT reports a lock, another package operation owns it. Inspect processes and wait for that operation to finish. Do not delete lock files to force an installation.

## Four Docker concepts in this lab

**Image:** `httpd:2.4-alpine` contains Apache and its runtime. The tag can move as patches are published. A digest identifies an exact image build.

**Container:** a running instance of an image. Recreating it replaces its writable filesystem layer. Our actual site content lives outside that layer.

**Bind mount:** a host directory appears at a path inside a container. `runtime/sites/example.com` is mounted at Apache's `/usr/local/apache2/htdocs`. The `:ro` suffix prevents Apache from writing through this mount, while you can still edit the host files.

**Network:** Docker's `hosting-web` bridge gives the proxy and websites a shared private network. A container port is not automatically a public host port.

Compose describes these relationships as one application. `docker compose up -d` reconciles the declared application with the running containers. It may recreate changed containers; it is not merely a “start” command.

## Administrative access

Commands in this book use `sudo docker`. Membership in the Docker group also gives powerful control over the host; treat it as administrator access rather than an ordinary convenience permission.

Traefik reads Docker metadata through the mounted Docker socket. A read-only bind mount does not make the Docker API read-only. For deployments requiring stronger isolation, use a restricted socket proxy or a file-based provider and avoid exposing the raw socket to the reverse proxy.

**Checkpoint:** explain why deleting an Apache container should not delete the welcome page. Then locate the host directory that preserves it in the next chapter.
