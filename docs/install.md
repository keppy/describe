# describe Installation Guide

## Requirements

- Node.js 18 or higher
- Python 3.9 or higher
- An MCP-compatible client

describe has no Python runtime dependency beyond the standard library. The npm
package only needs Python available so it can launch `describe.py`.

## Install

```bash
npm install -g @keppylab/describe
```

## Add To Your MCP Client

For Claude Desktop and many compatible clients, add:

```json
{
  "describe": {
    "command": "npx",
    "args": ["-y", "@keppylab/describe"]
  }
}
```

Restart the client after editing the config.

## Verify

Ask your client:

```text
Use describe to search for GitHub MCP servers.
```

Or verify from the terminal:

```bash
describe --json search github
```

## Platform Notes

### macOS and Linux

If global npm installs require elevated permissions, prefer fixing npm's global
prefix over using `sudo`:

```bash
npm config set prefix ~/.npm-global
export PATH="$HOME/.npm-global/bin:$PATH"
```

### Windows

Install from PowerShell or Command Prompt. Python can be available as `py -3`,
`python`, or `python3`; the npm wrapper checks all three.

If Python is installed somewhere custom, set `PYTHON` to the full executable
path before launching describe.

## Configuration Paths

describe looks for Claude Desktop's MCP config by default:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/claude/claude_desktop_config.json`

Set `DESCRIBE_MCP_CONFIG` to target a specific config file.

## Local State

describe stores state in `~/.describe`:

```text
~/.describe/
  installed.json
  backups/
  cache/
```

Set `DESCRIBE_HOME` to use another directory.

## Offline Mode

Use the built-in starter registry when offline or testing:

```bash
DESCRIBE_REGISTRY=builtin describe list
```

PowerShell:

```powershell
$env:DESCRIBE_REGISTRY = "builtin"
describe list
```

## Development Install

```bash
git clone https://github.com/keppy/describe.git
cd describe
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

On Windows:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
```

## Uninstall

```bash
npm uninstall -g @keppylab/describe
rm -rf ~/.describe
```

On Windows, remove `%USERPROFILE%\.describe` if you want to delete local state.
