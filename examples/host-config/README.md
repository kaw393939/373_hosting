# Host and DNS configuration copies

| Example | Actual destination | Explanation |
|---|---|---|
| [docker.sources](docker.sources) | `/etc/apt/sources.list.d/docker.sources` | Adds Docker's signed Ubuntu package repository; `noble` is Ubuntu 24.04 and `amd64` is the illustrated architecture |
| [firewall-commands.sh](firewall-commands.sh) | UFW rules on the VPS | Prints the SSH, HTTP, and HTTPS rules for you to review and execute; does not change them itself |
| [dns-records.example.csv](dns-records.example.csv) | Your domain provider's record editor | Worksheet for two zones and their subdomains; not a guaranteed provider-specific import format |

`203.0.113.10` is a documentation address, not the classroom server. Replace it
with your own VPS address. The wildcard row is optional, and is not a wildcard
certificate. Check for conflicting AAAA records separately. See Chapter 2 before
changing DNS or firewall settings.

The Docker installer downloads the repository's public signing key to
`/etc/apt/keyrings/docker.asc`. That key is acquired from Docker's official URL;
it is not a private credential or a file students should invent. The installer
generates the correct architecture in `docker.sources` instead of requiring a
manual copy of this amd64 example.

No custom Docker `daemon.json` is needed: the stack uses the daemon defaults and
sets log rotation per container in Compose. No SSH server configuration change
is needed. Do not overwrite working host configurations just because another
lab uses a different file layout.
