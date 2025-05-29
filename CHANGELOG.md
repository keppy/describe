# Changelog

All notable changes to describe will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-05-28

### Changed
- **🎯 REBRANDED**: MCPM is now **describe** - "Speak systems into existence"
- **Package name**: `@keppylab/mcpm` → `@keppylab/describe`
- **Binary command**: `mcpm` → `describe`
- **Core philosophy**: From "package manager" to "conversational infrastructure"
- **Positioning**: Transform infrastructure from configuration to conversation

### Migration
- Old users: `npm uninstall -g @keppylab/mcpm && npm install -g @keppylab/describe`
- Update configs: Change command from `mcpm` to `describe`
- All functionality remains identical, just better branding

---

## Previous Releases (as MCPM)

## [0.1.5] - 2025-05-28

### Fixed
- **CLI config-list**: Fixed bug where CLI expected dict but method returned list
- **Error handling**: Improved consistency between CLI and MCP interfaces

### Changed
- **Testing**: Comprehensive CLI command testing for edge cases and error conditions

## [0.1.4] - 2025-05-28

### Fixed
- **Registry connectivity**: Fixed timeout issues with MCP server registry fetching
- **Async handling**: Resolved asyncio errors in CLI mode by adding proper CLI interface
- **Search functionality**: Registry now uses built-in verified MCP servers from @modelcontextprotocol scope

### Added
- **CLI interface**: Added direct command-line interface alongside MCP server mode
- **Error handling**: Improved timeout and error handling for network requests
- **Built-in registry**: Curated list of verified MCP servers including:
  - filesystem: File operations and document indexing
  - postgres: Database access with schema inspection
  - brave-search: Web search using Brave Search API
  - github: Repository management and GitHub API integration
  - git: Git repository tools
  - fetch: Web content fetching and conversion
  - puppeteer: Browser automation and web scraping
  - memory: Knowledge graph-based persistent memory
  - gdrive: Google Drive file access
  - google-maps: Location services and directions

### Changed
- **Registry source**: Switched from unreliable remote registry to built-in verified servers
- **Startup time**: Significantly improved startup performance by removing network dependency

## [0.1.3] - 2025-05-26

### Added
- **Config management**: Complete MCP configuration automation with 5 new tools:
  - `config-add`: Add installed servers to MCP config
  - `config-remove`: Remove servers from MCP config  
  - `config-list`: List configured MCP servers
  - `config-backup`: Backup current MCP configuration
  - `config-restore`: Restore MCP config from backup
- **Cross-platform support**: Automatic MCP config detection for macOS, Windows, and Linux
- **Backup system**: Automatic config backups before modifications for safe operations
- **GitHub branding**: Theme-aware logos (light/dark mode) with describe → arrow concept
- **Modern Python**: Updated to use modern type annotations (dict/list vs typing.Dict/List)

### Changed
- **Type annotations**: Migrated from `typing.Dict`/`List` to modern `dict`/`list` syntax
- **Package metadata**: Updated Discord link to permanent invite
- **Logo assets**: Added comprehensive branding suite (logo.svg, logo-dark.svg, icon.svg, favicon.svg)

### Fixed
- **Virtual environment**: Improved Python dependency isolation using dedicated venv
- **Global installation**: Fixed npm global installation issues with bin wrapper
- **Test coverage**: Updated tests to cover new config management functionality

## [0.1.2] - 2025-05-25

### Fixed
- **Python virtual environment**: Fixed issues with Python dependency management
- **Installation process**: Improved setup script reliability

### Changed
- **Dependency management**: Enhanced virtual environment handling for better isolation

## [0.1.1] - 2025-05-25

### Added
- **Core functionality**: Basic MCP server package management
- **Installation methods**: Support for npm, docker, and git installation methods
- **Server registry**: Dynamic server discovery and installation
- **MCP integration**: Full Model Context Protocol server implementation

### Features
- **5 core tools**:
  - `list`: List all available MCP servers
  - `search`: Search servers by name or description
  - `install`: Install MCP servers via npm/docker/git
  - `uninstall`: Remove installed servers
  - `installed`: List currently installed servers

## [0.1.0] - 2025-05-24

### Added
- **Initial release**: describe - The MCP Package Manager
- **Vision**: "The package manager that manages package managers"
- **Core concept**: Conversational infrastructure management
- **MCP protocol**: Full Model Context Protocol implementation
- **Package management**: Basic server installation and management

### Architecture
- **Node.js wrapper**: Global npm installation with Python backend
- **Virtual environment**: Isolated Python dependencies
- **Cross-platform**: Support for macOS, Linux, and Windows
- **Extensible**: Plugin architecture for future MCP servers

---

## Version History Summary

- **v0.1.4**: Fixed registry and added CLI interface
- **v0.1.3**: Added complete config management and branding  
- **v0.1.2**: Fixed virtual environment issues
- **v0.1.1**: Core MCP package management functionality
- **v0.1.0**: Initial release and architecture

## Roadmap

### Upcoming Features
- **Dynamic registry**: Real-time npm registry integration
- **Server templates**: Create custom MCP servers from templates
- **Dependency resolution**: Smart dependency management between MCP servers
- **Health monitoring**: Server status and health checking
- **Performance metrics**: Usage analytics and optimization suggestions

### Long-term Vision
- **Ecosystem growth**: Become the standard package manager for MCP
- **Community packages**: Support for community-contributed MCP servers
- **Enterprise features**: Team management and private registries
- **Integration platform**: Bridge between different AI tooling ecosystems