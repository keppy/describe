# describe CLI Reference

While describe is designed for conversational use through Claude Desktop, it also provides a powerful CLI for direct terminal usage, scripting, and automation.

## Installation

```bash
npm install -g @keppylab/describe
```

## Command Overview

```bash
describe <command> [options]
```

## Package Management Commands

### `describe list`
List all available MCP servers from the official registry.

```bash
describe list
# Shows all available servers with descriptions
```

### `describe search <query>`
Search for MCP servers by name or description.

```bash
describe search database
# Find all database-related servers

describe search github
# Find GitHub integration servers
```

### `describe install <server>`
Install an MCP server from the registry.

```bash
describe install @modelcontextprotocol/server-github
# Installs the GitHub MCP server

describe install sqlite
# Installs the SQLite server
```

Supports multiple installation methods:
- **npm packages**: Installed globally via npm
- **Docker images**: Pulled and configured
- **Git repositories**: Cloned to `~/.describe/repos/`

### `describe uninstall <server>`
Remove an installed MCP server.

```bash
describe uninstall server-github
# Removes the GitHub server
```

### `describe installed`
Show all currently installed MCP servers.

```bash
describe installed
# Lists installed servers with their installation method
```

## Configuration Management Commands

### `describe config-add <server> [options]`
Add an installed server to your MCP configuration.

```bash
describe config-add server-github
# Auto-generates appropriate config

describe config-add my-server --command "python" --args "/path/to/server.py"
# Custom configuration
```

Options:
- `--command <cmd>`: Override the command to run
- `--args <args>`: Override command arguments (comma-separated)
- `--env <vars>`: Add environment variables (KEY=value,KEY2=value2)

### `describe config-remove <server>`
Remove a server from your MCP configuration.

```bash
describe config-remove server-github
# Removes from config (backup created automatically)
```

### `describe config-list`
List all servers in your MCP configuration.

```bash
describe config-list
# Shows configured servers with their commands
```

### `describe config-backup`
Create a backup of your current MCP configuration.

```bash
describe config-backup
# Creates timestamped backup in ~/.describe/backups/
```

### `describe config-restore <backup>`
Restore a configuration from backup.

```bash
describe config-restore config_backup_20240126_143022.json
# Restores specific backup

describe config-restore --latest
# Restores most recent backup
```

## Global Options

### `--version`
Show describe version.

```bash
describe --version
# describe v1.0.0
```

### `--help`
Show help for any command.

```bash
describe --help
# General help

describe install --help
# Command-specific help
```

### `--debug`
Enable debug logging.

```bash
describe --debug install server-github
# Shows detailed installation process
```

## Configuration Files

### MCP Config Locations
describe automatically finds your MCP configuration:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/claude/claude_desktop_config.json`

### describe Config
describe stores its own data in `~/.describe/`:

```
~/.describe/
├── installed.json      # Installed servers database
├── backups/           # Configuration backups
├── repos/             # Git-based servers
└── cache/             # Downloaded artifacts
```

## Scripting Examples

### Batch Installation
```bash
#!/bin/bash
servers=("filesystem" "github" "sqlite" "postgres")

for server in "${servers[@]}"; do
  describe install "$server"
  describe config-add "$server"
done
```

### Backup Before Changes
```bash
describe config-backup
describe install new-server
describe config-add new-server
```

### Search and Install
```bash
describe search database | grep postgres
describe install @modelcontextprotocol/server-postgres
```

## Environment Variables

### `DESCRIBE_HOME`
Override describe's data directory (default: `~/.describe`)

```bash
export DESCRIBE_HOME=/custom/path
describe list
```

### `DESCRIBE_REGISTRY`
Use a custom MCP registry URL (for private registries)

```bash
export DESCRIBE_REGISTRY=https://my-company.com/mcp-registry.json
describe list
```

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Server not found
- `3`: Already installed
- `4`: Configuration error
- `5`: Network error

## Advanced Usage

### Custom Installation
```bash
# Install from specific npm version
describe install @modelcontextprotocol/server-github@1.2.3

# Install from git URL
describe install git+https://github.com/user/mcp-server.git

# Install from local path
describe install file:///path/to/local/server
```

### Dry Run
```bash
describe install server-github --dry-run
# Shows what would be installed without doing it
```

### Force Reinstall
```bash
describe install server-github --force
# Reinstalls even if already installed
```

## Troubleshooting

### Debug Mode
```bash
describe --debug <command>
# Shows detailed logs for debugging
```

### Reset describe
```bash
rm -rf ~/.describe
npm reinstall -g @keppylab/describe
```

### Common Issues

**"Server not found"**
- Check spelling: `describe search <partial-name>`
- Update registry: `describe update-registry`

**"Config file not found"**
- Ensure Claude Desktop is installed
- Check platform-specific paths above
- describe will create if missing

**"Permission denied"**
- npm global installs may need sudo
- Use npm prefix: `npm config set prefix ~/.npm-global`

## Integration with CI/CD

### GitHub Actions Example
```yaml
- name: Setup describe
  run: npm install -g @keppylab/describe

- name: Install MCP servers
  run: |
    describe install filesystem
    describe install sqlite
    describe config-add filesystem
    describe config-add sqlite
```

### Docker Example
```dockerfile
FROM node:18
RUN npm install -g @keppylab/describe
RUN describe install filesystem sqlite
```

---

**Note**: While these CLI commands are powerful for automation and scripting, the magic of describe happens when you use it conversationally through Claude Desktop. The CLI exists for power users and automation—the revolution is in the conversation.