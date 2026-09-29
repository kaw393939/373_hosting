# 8 · Assessment and glossary

[Contents](../README.md)

## Final practical

Build the lab on a VPS you control. Submit a short report containing:

1. A diagram tracing a request through DNS, TLS, Traefik, and Apache.
2. DNS answers for each configured hostname, including an explanation of any AAAA record.
3. Five distinct welcome pages with your own text, or a smaller instructor-approved list.
4. Verification output showing HTTP redirects and trusted HTTPS.
5. A dashboard screenshot identifying one router, service, and entry point.
6. A controlled failure, your hypothesis, the evidence, and the fix.
7. A backup and restore plan describing which files must stay private.

Do not submit passwords, tokens, `acme.json`, private keys, or backup archives. Screenshots should omit unrelated personal information.

## Suggested rubric

| Area | Points | Evidence |
|---|---:|---|
| Architecture explanation | 20 | Correct request path and responsibilities |
| DNS and connectivity | 15 | Correct records and layer-specific checks |
| Containers and content | 20 | Distinct pages, persistent mounts, internal networking |
| HTTPS and routing | 20 | Trusted certificates, redirects, correct Host rules |
| Troubleshooting | 15 | Reproducible problem and reasoned diagnosis |
| Operations | 10 | Recovery plan and appropriate secret handling |

## Review questions with answer notes

**Does `apt-get update` install all available upgrades?** No. It refreshes package metadata. Installation and upgrades are separate operations.

**What happens if a hostname resolves correctly but no router matches it?** Reaching the machine is possible, but Traefik has no intended backend for that hostname. HTTPS may also present a default certificate if none covers the name.

**Why does wildcard DNS not produce a wildcard certificate?** DNS resolution and certificate issuance are separate mechanisms. Wildcard certificates require DNS-01 validation.

**Why can a welcome page survive container replacement?** The content is bind-mounted from the host rather than stored only in the container's writable layer.

**What does a 401 tell you that a timeout does not?** An HTTP server responded and requested authentication; a timeout does not establish that an HTTP response was received.

**Can you configure new routes by clicking the dashboard?** No. This deployment's dashboard shows configuration; Docker labels and Compose define it.

**Does a read-only Docker socket mount make the Docker API safe to expose?** No. Mount permissions do not restrict API operations. The socket is an administrative trust boundary.

## Glossary

| Term | Meaning in this lab |
|---|---|
| A / AAAA | DNS records mapping names to IPv4 / IPv6 addresses |
| ACME | Protocol used to automate certificate management |
| Bind mount | Host file or directory made available inside a container |
| Certificate resolver | Traefik configuration for obtaining and renewing certificates |
| Compose | Declarative description and lifecycle tool for related containers |
| Entry point | Traefik listener, such as port 80 or 443 |
| Host rule | Router condition matching an HTTP hostname |
| HTTP-01 | Proof of domain control using an HTTP challenge |
| Image digest | Identifier for an exact container image build |
| Middleware | Request/response behavior such as authentication |
| Reverse proxy | Public server forwarding requests to backend services |
| Router | Rule connecting incoming requests to a service |
| Service | Backend destination configuration used by Traefik |
| TLS | Protocol protecting connections and authenticating servers |
| TTL | DNS caching lifetime |
| VPS | Virtual private server |
