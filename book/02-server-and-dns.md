# 2 · Prepare the server and DNS

[Contents](../README.md) · [Next: Docker](03-docker.md)

## Learning goals

Establish an SSH session, inspect the machine, and verify public DNS before requesting certificates.

Create a fresh Ubuntu 24.04 LTS VPS with a public IPv4 address. A small instance with 2 GB RAM is sufficient for this static-page lab. Keep the provider's recovery console available while changing firewall rules. Use an SSH key and a user with sudo access.

On your own computer, connect using your real values:

```bash
ssh YOUR_USER@YOUR_SERVER_IP
```

Verify a first-connection host-key fingerprint against the provider console before accepting it. Once connected, these commands describe the remote host:

```bash
whoami
cat /etc/os-release
sudo ss -lntup
df -h /
sudo ufw status verbose
```

Ports 80 and 443 must be free. If another web server already owns them, investigate before stopping services. This book assumes a fresh machine; it is not an automatic migration tool.

## DNS lab

In your DNS provider's record editor, create records like these. Replace `SERVER_IP` with the VPS address and use domains you own.

| Zone | Type | Name | Value |
|---|---|---|---|
| example.com | A | @ | SERVER_IP |
| example.com | A | www | SERVER_IP |
| example.com | A | dev | SERVER_IP |
| example.com | A | traefik | SERVER_IP |
| example.org | A | @ | SERVER_IP |
| example.org | A | www | SERVER_IP |
| example.org | A | * | SERVER_IP, optional |

`@` means the zone's root name. A wildcard DNS record answers for eligible otherwise-undefined names; it does not cover the zone root or grant a wildcard TLS certificate. Existing specific records take precedence. Leave unrelated mail records alone.

Use a short TTL such as 600 seconds while learning. TTL controls resolver caching; changing a record does not instantly clear every cache.

On Ubuntu, install DNS tools and inspect both address families:

```bash
sudo apt-get update
sudo apt-get install -y dnsutils
dig +short A example.com
dig +short AAAA example.com
dig @1.1.1.1 +short A traefik.example.com
```

An old AAAA record can send IPv6-capable clients to a different machine. Correct or remove it if this deployment has no working public IPv6 service. Check each hostname, not just the apex.

## Firewall lab

Allow your actual SSH port before enabling a firewall. For the standard SSH port 22:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status verbose
```

If SSH uses another port, explicitly allow that port first. Any provider-level cloud firewall must also allow inbound TCP 80 and 443, and your SSH connection. HTTP-01 certificate validation requires public access to port 80.

Docker-published ports can bypass UFW filtering. The lab publishes only Traefik's 80 and 443; do not add public port mappings to databases or Apache just to make routing work. See [Docker's firewall explanation](https://docs.docker.com/engine/network/packet-filtering-firewalls/).

**Checkpoint:** from a second terminal, confirm SSH still works. Record the A/AAAA answers for every hostname. Do not proceed with names pointing at a different machine.
