# Validation record

The classroom deployment behind this book used Ubuntu 24.04, Docker Engine 29.8.1, Traefik 3.7.13, and the official Apache `httpd:2.4-alpine` image. Five website hostnames returned their distinct welcome pages over trusted HTTPS; HTTP redirected to HTTPS. The dashboard and its API returned 200 without authentication after the instructor disabled the password. Six public certificates were issued.

The repository generalizes that deployment with replaceable hostnames. It does not export the live server's passwords, ACME state, or private keys.

Repository checks cover generator behavior, preservation of edited content and certificate state, invalid hostname rejection, shell syntax, and the generated Docker Compose model. CI repeats those checks without deploying public infrastructure. It does not test DNS-provider changes or request production certificates.

The installer follows the Docker repository commands used on the classroom server. A second clean VPS was not provisioned for this publication. Students should perform the complete public verification in Chapter 4 on their own host.

The checked-in complete example is compared against the generator in tests,
including every HTML page. CI validates the base Compose file, each optional
overlay, and both overlays combined. Overlay validation checks the merged model;
it does not request certificates or provision a password file. The optional
file-based Traefik configuration is an instructional equivalent of the base CLI
settings, not a change applied to the classroom server.
