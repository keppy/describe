# describe CLI Reference

describe is designed to be used by an MCP client, but every operation is also
available from the terminal.

## Usage

```bash
describe [--json] [--debug] <command> [arguments]
```

Global options:

- `--json`: print machine-readable JSON.
- `--debug`: enable debug logging.
- `--version`: print the describe version.

## Registry Commands

### `describe list`

List servers visible through the Registry cache.

```bash
describe list
```

### `describe search <query>`

Search by short name, registry name, package name, title, or description.

```bash
describe search github
describe search database
```

### `describe registry-refresh`

Refresh the local Registry cache.

```bash
describe registry-refresh
```

## Install Commands

### `describe install <server>`

Install or register a server. The server can be a short name, full Registry
name, or package identifier.

```bash
describe install github
describe install @modelcontextprotocol/server-filesystem
```

Optionally force an installation method:

```bash
describe install github --method npm
describe install com.example/analytics --method remote
```

Supported methods:

- `npm`: installs globally with `npm install -g`.
- `docker`: pulls an OCI image with `docker pull`.
- `pypi`: installs with `python -m pip install --user`.
- `remote`: records the remote MCP endpoint; no local package install.

### `describe uninstall <server>`

Remove a server from describe's installed database.

```bash
describe uninstall github
```

### `describe installed`

Show installed or registered servers.

```bash
describe installed
```

## Config Commands

### `describe config-add <server>`

Generate MCP client config for an installed server and write it to the detected
client config.

```bash
describe install github
describe config-add github
```

If Registry metadata declares environment variables, describe uses values from
your process environment or non-secret defaults. It does not invent secrets.

### `describe config-remove <server>`

Remove a server from the MCP client config.

```bash
describe config-remove github
```

### `describe config-list`

List configured MCP servers.

```bash
describe config-list
```

### `describe config-backup`

Create a timestamped backup under `~/.describe/backups`.

```bash
describe config-backup
```

### `describe config-restore <backup>`

Restore a backup by filename or full path.

```bash
describe config-restore config_backup_20260520_120000.json
```

## Environment Variables

- `DESCRIBE_HOME`: local state directory. Default: `~/.describe`.
- `DESCRIBE_REGISTRY`: Registry API URL. Use `builtin` for offline mode.
- `DESCRIBE_REGISTRY_LIMIT`: maximum servers to cache. Default: `250`.
- `DESCRIBE_CACHE_TTL_SECONDS`: cache lifetime. Default: `3600`.
- `DESCRIBE_MCP_CONFIG`: exact MCP config file to edit.
- `DESCRIBE_MCP_PROTOCOL_VERSION`: protocol version advertised in `initialize`.

## JSON Examples

```bash
describe --json search postgres
```

```json
[
  {
    "name": "postgres",
    "registryName": "io.modelcontextprotocol/postgres",
    "title": "Postgres",
    "description": "Read-only PostgreSQL access with schema inspection.",
    "version": "latest",
    "status": "active",
    "installMethods": ["npm"]
  }
]
```

## Scripting Example

```bash
set -e

describe install filesystem
describe config-add filesystem
describe install github
describe config-add github
describe config-list
```

## Exit Codes

- `0`: command completed successfully.
- `1`: command failed or returned an error payload.
