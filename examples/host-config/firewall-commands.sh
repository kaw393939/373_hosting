#!/usr/bin/env bash
# Reference only: review your SSH port and provider firewall first.
# Print the commands by default; this file does not change the firewall.
cat <<'COMMANDS'
# Assumes SSH on standard port 22. Allow a custom SSH port before enabling UFW.
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status verbose
COMMANDS
