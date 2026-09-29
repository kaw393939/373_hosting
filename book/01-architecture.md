# 1 · The request's journey

[Contents](../README.md) · [Next: server and DNS](02-server-and-dns.md)

## Learning goals

Explain how one server can host multiple domains, and identify which component is responsible when a request fails.

Imagine a visitor opening `https://www.example.com`. The browser first asks DNS for an address. An A record supplies IPv4; an AAAA record supplies IPv6. DNS does not select a Docker container, issue a certificate, or redirect a browser. It answers a naming question.

The browser connects to that address on TCP port 443. Traefik accepts the connection and presents a TLS certificate for the requested hostname. A trusted certificate helps the browser verify the server's identity and establish an encrypted connection. Certificate validation occurs before the browser can safely process the website's HTTP response.

Next, Traefik evaluates the HTTP hostname against its router rules. A rule such as ``Host(`www.example.com`)`` selects a service. That service forwards the request to the appropriate Apache container on port 80 inside the Docker network. Apache reads `index.html` from its document root and returns a response through Traefik.

## Three different meanings of “server”

| Term | In this lab |
|---|---|
| VPS / host | The Ubuntu machine with the public IP |
| Reverse proxy | Traefik, the public HTTP and HTTPS entry point |
| Web server | Apache HTTP Server, which serves page files |

A container is a running process with isolation, networking, and a filesystem view. An image is the packaged starting point for that container. Five containers can use the same `httpd` image while mounting five different directories of content.

The two HTTPS connections people sometimes imagine are actually different here: the browser-to-Traefik connection uses TLS; Traefik-to-Apache traffic uses HTTP on the local Docker bridge. This lab does not implement encryption between containers on separate machines.

## Read the configuration as a sentence

“When a request arrives on `websecure` and its hostname matches this router, forward it to this service's container port 80.” The `websecure` entry point sets the default certificate resolver, so each matching named router can request a certificate.

The dashboard shows discovered routes and services. It is not a graphical editor for creating containers. Changes start in configuration files and take effect through Docker Compose.

## Check your understanding

1. Why can all five website DNS records point to the same address?
2. Why does each Apache container listen on port 80 without causing a conflict?
3. If TLS fails before a page loads, is editing `index.html` likely to help?

**Answers:** Traefik distinguishes hostnames; each container has its own network namespace and does not publish host port 80; a certificate problem occurs before page rendering.
