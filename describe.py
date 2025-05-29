#!/usr/bin/env python3
"""
describe - The MCP Package Manager
"The package manager that manages package managers"
Inspired by apt, cargo, and nix - but for MCP servers.

Copyright 2024 James Dominguez

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import asyncio
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import aiohttp

from config_manager import MCPConfigManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("describe")

# The registry of power
REGISTRY_URL = "https://registry.npmjs.org/-/v1/search?text=scope:modelcontextprotocol&size=250"
describe_HOME = Path.home() / ".describe"
INSTALLED_DB = describe_HOME / "installed.json"
CACHE_DIR = describe_HOME / "cache"


class MCPPackageManager:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.registry: dict[str, Any] = {}
        self.installed: dict[str, Any] = {}
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Create the sacred directories"""
        describe_HOME.mkdir(exist_ok=True)
        CACHE_DIR.mkdir(exist_ok=True)
        if not INSTALLED_DB.exists():
            INSTALLED_DB.write_text("{}")

    async def _load_installed(self):
        """Load the tome of installed servers"""
        try:
            self.installed = json.loads(INSTALLED_DB.read_text())
        except:
            self.installed = {}

    async def _save_installed(self):
        """Persist the installation state"""
        INSTALLED_DB.write_text(json.dumps(self.installed, indent=2))

    async def _fetch_registry(self):
        """Load MCP servers registry"""
        # Use built-in registry of verified MCP servers from @modelcontextprotocol scope
        self.registry = {
            "filesystem": {
                "id": "filesystem",
                "description": "MCP server for filesystem access",
                "npm": "@modelcontextprotocol/server-filesystem"
            },
            "postgres": {
                "id": "postgres", 
                "description": "Read-only database access with schema inspection",
                "npm": "@modelcontextprotocol/server-postgres"
            },
            "brave-search": {
                "id": "brave-search",
                "description": "Web and local search using Brave's Search API",
                "npm": "@modelcontextprotocol/server-brave-search"
            },
            "github": {
                "id": "github",
                "description": "Repository management, file operations, and GitHub API integration", 
                "npm": "@modelcontextprotocol/server-github"
            },
            "git": {
                "id": "git",
                "description": "Tools to read, search, and manipulate Git repositories",
                "npm": "@modelcontextprotocol/server-git"
            },
            "fetch": {
                "id": "fetch",
                "description": "Web content fetching and conversion for efficient LLM usage",
                "npm": "@modelcontextprotocol/server-fetch"
            },
            "puppeteer": {
                "id": "puppeteer", 
                "description": "Browser automation and web scraping",
                "npm": "@modelcontextprotocol/server-puppeteer"
            },
            "memory": {
                "id": "memory",
                "description": "Knowledge graph-based persistent memory system",
                "npm": "@modelcontextprotocol/server-memory"
            },
            "gdrive": {
                "id": "gdrive",
                "description": "File access and search capabilities for Google Drive",
                "npm": "@modelcontextprotocol/server-gdrive"
            },
            "google-maps": {
                "id": "google-maps",
                "description": "Location services, directions, and place details",
                "npm": "@modelcontextprotocol/server-google-maps"
            }
        }

    async def list_available(self) -> list[dict[str, Any]]:
        """List all servers in the multiverse"""
        await self._fetch_registry()
        return [
            {"name": k, "description": v.get("description", ""), "installed": k in self.installed}
            for k, v in self.registry.items()
        ]

    async def search(self, query: str) -> list[dict[str, Any]]:
        """Search the cosmic registry"""
        await self._fetch_registry()
        query = query.lower()
        results = []
        for name, server in self.registry.items():
            if query in name.lower() or query in server.get("description", "").lower():
                results.append({"name": name, "description": server.get("description", "")})
        return results

    async def install(self, name: str) -> dict[str, Any]:
        """Install a server from the void"""
        await self._fetch_registry()
        await self._load_installed()

        if name not in self.registry:
            return {"error": f"Server '{name}' not found in registry"}

        if name in self.installed:
            return {"error": f"Server '{name}' already installed"}

        server = self.registry[name]

        # Determine installation method
        if "npm" in server:
            result = await self._install_npm(name, server["npm"])
        elif "docker" in server:
            result = await self._install_docker(name, server["docker"])
        elif "git" in server:
            result = await self._install_git(name, server["git"])
        else:
            return {"error": f"No installation method found for '{name}'"}

        if "error" not in result:
            self.installed[name] = {"method": result["method"], "details": result}
            await self._save_installed()

        return result

    async def _install_npm(self, name: str, package: str) -> dict[str, Any]:
        """Channel the npm spirits"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "npm", "install", "-g", package, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                return {"method": "npm", "package": package, "status": "installed"}
            return {"error": stderr.decode()}
        except Exception as e:
            return {"error": str(e)}

    async def _install_docker(self, name: str, image: str) -> dict[str, Any]:
        """Summon the container daemon"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "pull", image, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                return {"method": "docker", "image": image, "status": "pulled"}
            return {"error": stderr.decode()}
        except Exception as e:
            return {"error": str(e)}

    async def _install_git(self, name: str, repo: str) -> dict[str, Any]:
        """Clone from the source"""
        target = describe_HOME / "repos" / name
        target.parent.mkdir(exist_ok=True)
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "clone", repo, str(target), stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                return {"method": "git", "repo": repo, "path": str(target), "status": "cloned"}
            return {"error": stderr.decode()}
        except Exception as e:
            return {"error": str(e)}

    async def uninstall(self, name: str) -> dict[str, Any]:
        """Banish a server back to the void"""
        await self._load_installed()

        if name not in self.installed:
            return {"error": f"Server '{name}' not installed"}

        info = self.installed[name]

        # Clean up based on installation method
        if info["method"] == "git" and "path" in info["details"]:
            path = Path(info["details"]["path"])
            if path.exists():
                import shutil

                shutil.rmtree(path)

        del self.installed[name]
        await self._save_installed()
        return {"status": "uninstalled", "name": name}

    async def list_installed(self) -> list[dict[str, Any]]:
        """Show the chosen ones"""
        await self._load_installed()
        return [{"name": k, **v} for k, v in self.installed.items()]

    async def cleanup(self):
        """Release resources"""
        if self.session:
            await self.session.close()


# MCP Server Interface
async def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    """The grand dispatcher"""
    describe = MCPPackageManager()

    try:
        method = request.get("method", "")
        params = request.get("params", {})

        if method == "tools/list":
            return {
                "tools": [
                    {"name": "list", "description": "List all available MCP servers"},
                    {"name": "search", "description": "Search for MCP servers"},
                    {"name": "install", "description": "Install an MCP server"},
                    {"name": "uninstall", "description": "Remove an installed server"},
                    {"name": "installed", "description": "List installed servers"},
                    {"name": "config-add", "description": "Add installed server to MCP config"},
                    {"name": "config-remove", "description": "Remove server from MCP config"},
                    {"name": "config-list", "description": "List servers in MCP config"},
                    {"name": "config-backup", "description": "Backup current MCP config"},
                    {"name": "config-restore", "description": "Restore MCP config from backup"},
                ]
            }

        elif method == "tools/call":
            tool = params.get("name")
            args = params.get("arguments", {})

            if tool == "list":
                result = await describe.list_available()
            elif tool == "search":
                result = await describe.search(args.get("query", ""))
            elif tool == "install":
                result = await describe.install(args.get("name", ""))
            elif tool == "uninstall":
                result = await describe.uninstall(args.get("name", ""))
            elif tool == "installed":
                result = await describe.list_installed()
            elif tool == "config-add":
                config_mgr = MCPConfigManager()
                server_name = args.get("name", "")

                await describe._load_installed()
                if server_name not in describe.installed:
                    result = {"error": f"Server '{server_name}' not installed. Install it first."}
                else:
                    server_info = describe.installed[server_name]
                    server_config = config_mgr.generate_server_config(server_info["details"])

                    if "command" in args:
                        server_config["command"] = args["command"]
                    if "args" in args:
                        server_config["args"] = args["args"]

                    result = await config_mgr.add_server(server_name, server_config)

            elif tool == "config-remove":
                config_mgr = MCPConfigManager()
                result = await config_mgr.remove_server(args.get("name", ""))

            elif tool == "config-list":
                config_mgr = MCPConfigManager()
                result = await config_mgr.list_configured()

            elif tool == "config-backup":
                config_mgr = MCPConfigManager()
                backup_path = await config_mgr.backup_config()
                result = {"backup": backup_path}

            elif tool == "config-restore":
                config_mgr = MCPConfigManager()
                result = await config_mgr.restore_backup(args.get("backup", ""))
            else:
                result = {"error": f"Unknown tool: {tool}"}

            return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

    finally:
        await describe.cleanup()

    return {"error": {"code": -32601, "message": "Method not found"}}


async def main():
    """The eternal loop"""
    logger.info("describe awakens...")

    async for line in async_stdin():
        try:
            request = json.loads(line)
            response = await handle_request(request)
            print(json.dumps(response))
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"Error: {e}")


async def async_stdin():
    """Async stdin reader"""
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        line = await reader.readline()
        if not line:
            break
        yield line.decode().strip()


async def cli_main():
    """CLI interface for describe"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: describe <command> [args...]")
        print("Commands: list, search, install, uninstall, installed, config-add, config-remove, config-list, config-backup, config-restore")
        return
    
    command = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []
    
    describe = MCPPackageManager()
    
    try:
        if command == "list":
            result = await describe.list_available()
            for server in result:
                print(f"{server['name']}: {server['description']}")
        
        elif command == "search":
            if not args:
                print("Usage: describe search <query>")
                return
            result = await describe.search(args[0])
            for server in result:
                print(f"{server['name']}: {server['description']}")
        
        elif command == "install":
            if not args:
                print("Usage: describe install <server_name>")
                return
            result = await describe.install(args[0])
            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                print(f"✅ Installed {args[0]}")
        
        elif command == "uninstall":
            if not args:
                print("Usage: describe uninstall <server_name>")
                return
            result = await describe.uninstall(args[0])
            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                print(f"✅ Uninstalled {args[0]}")
        
        elif command == "installed":
            result = await describe.list_installed()
            for server in result:
                print(f"{server['name']}: {server['method']}")
        
        elif command in ["config-add", "config-remove", "config-list", "config-backup", "config-restore"]:
            from config_manager import MCPConfigManager
            config_mgr = MCPConfigManager()
            
            if command == "config-add":
                if not args:
                    print("Usage: describe config-add <server_name>")
                    return
                await describe._load_installed()
                if args[0] not in describe.installed:
                    print(f"Error: Server '{args[0]}' not installed. Install it first.")
                    return
                server_info = describe.installed[args[0]]
                server_config = config_mgr.generate_server_config(server_info["details"])
                result = await config_mgr.add_server(args[0], server_config)
                print(f"✅ Added {args[0]} to MCP config" if result else f"❌ Failed to add {args[0]}")
            
            elif command == "config-remove":
                if not args:
                    print("Usage: describe config-remove <server_name>")
                    return
                result = await config_mgr.remove_server(args[0])
                print(f"✅ Removed {args[0]} from config" if result else f"❌ Failed to remove {args[0]}")
            
            elif command == "config-list":
                result = await config_mgr.list_configured()
                for server in result:
                    print(f"{server['name']}: {server['command']} {' '.join(server.get('args', []))}")
            
            elif command == "config-backup":
                backup_path = await config_mgr.backup_config()
                print(f"✅ Config backed up to: {backup_path}")
            
            elif command == "config-restore":
                if not args:
                    print("Usage: describe config-restore <backup_file>")
                    return
                result = await config_mgr.restore_backup(args[0])
                print(f"✅ Config restored" if result else f"❌ Failed to restore config")
        
        else:
            print(f"Unknown command: {command}")
    
    finally:
        await describe.cleanup()


if __name__ == "__main__":
    # Check if running as CLI or MCP server
    if len(sys.argv) > 1:
        # CLI mode
        asyncio.run(cli_main())
    else:
        # MCP server mode
        asyncio.run(main())
