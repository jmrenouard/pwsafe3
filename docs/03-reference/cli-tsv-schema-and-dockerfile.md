# CLI, TSV Schema, and Dockerfile Reference

Exact parameters, file formats, container configuration, and exit rules implemented by **pwsafe3**.

## `convert.pl` CLI Contract

| Item | Specification | Notes |
| :--- | :--- | :--- |
| Invocation | `perl convert.pl <input.tsv> <output.psafe3> [password]` | `--help` / `-h` prints usage and exits `0` |
| `PWSAFE3_PASSWORD` | Optional passphrase environment variable | Used when `[password]` positional argument is omitted |
| `USER` | Optional username metadata environment variable | Populates `whoami` header (default: `pwsafe3`) |
| `savedonhost` | Header field set to `localhost` | Applied via `addheader()` before `markmodified()` + `save()` |
| Overwrite guard | Refuses execution if `<output.psafe3>` exists (`-e`) | Exits non-zero with message |
| Input validation | Requires readable `<input.tsv>` (`-f`); warns and skips lines with `< 5` fields | Tabs (`\t`) separate columns via `split(/\t/, $line, -1)` |

## TSV Input Schema (`input.tsv`)

| Line Type | Pattern | Behavior |
| :--- | :--- | :--- |
| Blank / whitespace | `^\s*$` | Ignored |
| Group header | `^GROUP:(.*)$` | Sets current vault record group (`$group`) |
| Entry line | `<host>\t<database>\t<account>\t<access_type>\t<password>` | Creates `title=<host>`, `user=<account>@<database>`, `group=$group`, `passwd=<password>`, `notes="Server: ...\nDatabase: ...\nAccess Type: ..."` |

## `Dockerfile` and `drun.sh` Specification

| File | Setting | Value / Behavior |
| :--- | :--- | :--- |
| `Dockerfile` base | `FROM fedora:41` | Pinned Fedora image installing `perl-Data-Dumper` and `perl-Crypt-PWSafe3`, cleaning `/var/cache/dnf` |
| `Dockerfile` user | `USER app` (`uid 10001`) | Non-root container user with ownership of `/data` and `/usr/local/bin/convert.pl` |
| `Dockerfile` entrypoint | `ENTRYPOINT ["perl", "/usr/local/bin/convert.pl"]` | Binary resides outside `/data` so host bind mounts do not shadow it |
| `drun.sh` | `docker build -t psafe3 .` + `docker run --rm --user "$(id -u):$(id -g)" -e PWSAFE3_PASSWORD -v "$(pwd):/data" psafe3 "$@"` | Quotes host path and args, removes stopped container (`--rm`), preserves host file ownership |
