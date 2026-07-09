## Docker guide and instructions

A [docker-compose.yaml](../docker-compose.yaml) is included and runs both the app and its MariaDB database, and comes
shipped with the dashboard UI. Before using it, read the rest of this guide carefully to avoid common
misconfigurations.

### Docker compose

1. Fill in the two `TODO` values in the compose file:
    - `ADMIN_PASSWORD`: the password you'll log in with.
    - `JWT_SECRET`: any long random string ([generator](https://utilitools.net/dev/jwt-secret-generator/)).
2. Set `PUID`/`PGID` to your host user (`id -u` / `id -g`, usually `1000`). Saberr runs as this user, so everything it
   writes on the host ends up owned by you rather than root.
3. Run `docker compose up -d` and open the UI at `http://localhost:8125`.

### Giving Saberr access to your downloads and library

Saberr copies finished torrents out of qBittorrent's download folder and into your organized library, so inside a
container it needs both folders mounted. Uncomment and edit these lines in the compose file:

```yaml
      - /path/to/qbit/downloads:/downloads
      - /path/to/library:/library
```

Because Saberr runs as a non-root user, those host folders must be **owned by your `PUID`/`PGID`**. Docker creates any
missing bind-mount folders as `root`, so run this once (matching the ids you set), and replace the placeholder path
with the actual library path:

```bash
sudo chown -R 1000:1000 /path/to/library
```

Ensure that other apps accessing your library, and any other volumes you mount and `chown`, are also running as the same
`PUID`/`PGID` first.

### Remote path mapping

This setting is needed if qBittorrent reports download paths that Saberr can't access, especially since qBit runs in a
separate container (or a different machine). Ideally you'll have qBit's path to its downloads in volume mapping
identical to that on Saberr, but if this isn't the case, then you should set the mapping as seen in the example below.
If you're still unsure how this works, then you might find
[Servarr's guide](https://wiki.servarr.com/docker-guide#consistent-and-well-planned-paths) helpful.

Example:

> * Remote file path, as seen by qBittorrent: `/downloads/anime/Abc/Episode 1.mkv`
> * Local file path of the same file, as seen by Saberr: `/qbit_downloads/anime/Abc/Episode 1.mkv`

Mapping becomes:

> * Remote path: `/downloads`
> * Local path: `/qbit_downloads`

This settings is accessible within Saberr (Settings > qBit Service).

### Still facing issues

[Join the Discord server](https://discord.gg/3X2e7vgua4) and we're happy to help.
