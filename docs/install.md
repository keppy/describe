# describe Installation Guide

## Prerequisites

- **Node.js** 18.0 or higher
- **Python** 3.9 or higher  
- **Claude Desktop** (or compatible MCP client)

## Quick Install

```bash
npm install -g @keppylab/describe
```

That's it. describe handles the rest.

## Configure Claude Desktop

Add describe to your Claude Desktop configuration:

1. Open Claude Desktop settings
2. Find the MCP servers configuration
3. Add:

```json
{
  "describe": {
    "command": "npx",
    "args": ["-y", "@keppylab/describe"]
  }
}
```

4. Restart Claude Desktop

## Verify Installation

In Claude Desktop:
```
Human: Search for available servers
Claude: I'll search for available MCP servers...
```

If Claude can search and show results, you're ready.

## Platform-Specific Notes

### macOS
Everything should work out of the box. If you get permission errors:
```bash
sudo npm install -g @keppylab/describe
```

### Windows
Run the installation in an Administrator command prompt or PowerShell.

Python must be accessible as `python` (not `python3`).

### Linux
You may need to configure npm's global directory:
```bash
npm config set prefix ~/.npm-global
export PATH=~/.npm-global/bin:$PATH
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
```

## Troubleshooting

### "describe: command not found"
Check your npm global installation path:
```bash
npm config get prefix
# Add the bin directory to your PATH
```

### "Python not found"
describe needs Python 3.9+:
```bash
python --version  # or python3 --version
```

### "Cannot find Claude config"
describe will create the config file if it doesn't exist. Make sure Claude Desktop is installed first.

## Development Installation

To hack on describe itself:

```bash
git clone https://github.com/keppy/describe.git
cd describe
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Uninstall

```bash
npm uninstall -g @keppylab/describe
rm -rf ~/.describe  # Remove data directory
```

## Next Steps

Ready to speak your first system into existence? Try:

```
"Install filesystem and sqlite servers"
"Create a document database"
"Make it searchable"
```

Welcome to conversational infrastructure.