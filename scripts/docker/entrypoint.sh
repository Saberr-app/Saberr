#!/bin/sh
set -e

PUID=${PUID:-1000}
PGID=${PGID:-1000}

# Remap the runtime user/group to the ids the host wants to own the mounted data.
if [ "$(id -g saber)" != "$PGID" ]; then
    groupmod -o -g "$PGID" saber
fi
if [ "$(id -u saber)" != "$PUID" ]; then
    usermod -o -u "$PUID" saber
fi

# Fix ownership of Saberr's own writable paths (NOT user-mounted library volumes,
# which must already be writable by PUID/PGID). Runs as root before dropping down.
mkdir -p /app/data
chown -R saber:saber /app/data /home/saber

# Drop to the unprivileged user for the actual app.
exec gosu saber "$@"