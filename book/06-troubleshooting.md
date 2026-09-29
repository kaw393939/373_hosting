# 6 · Troubleshoot one layer at a time

[Contents](../README.md) · [Next: operations](07-operations.md)

## Learning goals

Use observable evidence to distinguish DNS, network, TLS, routing, and content failures.

“Site can't be reached” is not a diagnosis. Record the exact browser error, URL, and time. Start with the lowest layer that fails instead of repeatedly restarting every container.

| Symptom | Likely layer | Next check |
|---|---|---|
| Name not resolved | DNS | A/AAAA answers and authoritative records |
| Connection timed out | Network | Provider firewall, UFW, public IP |
| Connection refused | Listener | Is Traefik running and publishing 443? |
| Certificate warning | TLS | Hostname, certificate issuer, ACME logs |
| 404 | Routing or content | Matching Host rule; requested file exists |
| 502 / 504 | Backend | Network membership, Apache process and port |
| 401 | Authentication | Expected if dashboard protection is enabled |
| Wrong welcome page | Host rule/content | Configured hostname and mounted directory |

## Diagnostic sequence

Replace the example hostname in these commands:

```bash
dig +short A example.com
dig +short AAAA example.com
curl -I --connect-timeout 5 http://example.com/
curl -I --connect-timeout 5 https://example.com/
sudo docker compose -f runtime/compose.yaml ps
sudo docker compose -f runtime/compose.yaml logs --tail=100 traefik
sudo docker compose -f runtime/compose.yaml logs --tail=50 site-1
sudo ss -lntup
```

Expected results are a redirect on HTTP and 200 on an existing HTTPS welcome page. A successful `curl` with normal certificate verification is stronger evidence than one using `-k`, which bypasses identity checks. Never use `-k` as your final certificate test.

To separate DNS from server routing, use the real server IP with `--resolve`:

```bash
curl --resolve example.com:443:YOUR_SERVER_IP https://example.com/
```

This preserves the requested TLS hostname while overriding DNS for that request. If this works but normal access fails, examine DNS answers, cached results, and IPv6. A raw `https://IP_ADDRESS` test is not equivalent because the certificate was issued for a hostname.

## Common classroom failures

**APT is locked:** inspect `ps -ef` for package operations and allow them to finish. Do not remove locks or interrupt a running package configuration blindly.

**Port already allocated:** another stack or host web server is publishing the same port. Identify its owner before changing it. Only one process can bind the same address/port combination.

**ACME validation fails:** check every requested name, public port 80 access, IPv6 records, restrictive CAA records, and certificate rate-limit messages. An existing DNS record is not proof it has propagated to the authority's resolvers.

**Dashboard briefly returns 404 after restart:** the Docker provider may omit the Traefik container until its health check passes. Wait a short interval and inspect health before changing router rules.

**Browser fails while external curl succeeds:** compare the browser's exact hostname and error. Consider cached DNS, a proxy, a VPN, or browser-specific restrictions. Do not conclude the server is broken solely from one client, or conclude all clients work from one successful test.

**Exercise:** make a request for an unconfigured hostname using `curl --resolve`. Predict the certificate and routing outcome before running it. Restore normal settings after each experiment.
