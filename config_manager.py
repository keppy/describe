#!/usr/bin/env python3
"""
MCP Config Manager - Handles MCP configuration file management
Copyright 2024 James Dominguez
Licensed under the Apache License, Version 2.0
"""

import json
import logging
import os
import platform
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("describe.config")


class MCPConfigManager:
    """Manages MCP configuration files across different platforms"""

    def __init__(self):
        self.config_path = self._find_config_path()
        self.config: dict[str, Any] = {}
        self.backup_dir = Path.home() / ".describe" / "backups"
        self.backup_dir.mkdir(exist_ok=True, parents=True)

    def _find_config_path(self) -> Optional[Path]:
        """Find the MCP config file based on platform"""
        possible_paths = []

        if platform.system() == "Darwin":  # macOS
            possible_paths.extend(
                [
                    Path.home()
                    / "Library"
                    / "Application Support"
                    / "Claude"
                    / "claude_desktop_config.json",
                    Path.home() / ".config" / "claude" / "claude_desktop_config.json",
                ]
            )
        elif platform.system() == "Windows":
            possible_paths.extend(
                [
                    Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json",
                    Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",
                ]
            )
        else:  # Linux
            possible_paths.extend(
                [
                    Path.home() / ".config" / "claude" / "claude_desktop_config.json",
                    Path.home() / ".claude" / "claude_desktop_config.json",
                ]
            )

        # Check each path
        for path in possible_paths:
            if path.exists():
                logger.info(f"Found MCP config at: {path}")
                return path

        # If not found, return the most likely path for the platform
        if platform.system() == "Darwin":
            default = (
                Path.home()
                / "Library"
                / "Application Support"
                / "Claude"
                / "claude_desktop_config.json"
            )
        elif platform.system() == "Windows":
            default = (
                Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
                / "Claude"
                / "claude_desktop_config.json"
            )
        else:
            default = Path.home() / ".config" / "claude" / "claude_desktop_config.json"

        logger.info(f"No config found, will create at: {default}")
        return default

    async def load_config(self) -> dict[str, Any]:
        """Load the current MCP configuration"""
        if not self.config_path or not self.config_path.exists():
            logger.info("No existing config file, starting with empty config")
            return {"mcpServers": {}}

        try:
            with open(self.config_path) as f:
                self.config = json.load(f)

            # Ensure mcpServers key exists
            if "mcpServers" not in self.config:
                self.config["mcpServers"] = {}

            return self.config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise Exception(f"Failed to load MCP config: {e}") from e

    async def backup_config(self) -> str:
        """Create a backup of the current config"""
        if not self.config_path or not self.config_path.exists():
            return "No config to backup"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"config_backup_{timestamp}.json"

        try:
            shutil.copy2(self.config_path, backup_path)
            logger.info(f"Created backup at: {backup_path}")
            return str(backup_path)
        except Exception as e:
            logger.error(f"Failed to backup config: {e}")
            raise Exception(f"Failed to backup config: {e}") from e

    async def save_config(self) -> None:
        """Save the current configuration"""
        if not self.config_path:
            raise Exception("No config path available")

        # Ensure directory exists
        self.config_path.parent.mkdir(exist_ok=True, parents=True)

        try:
            # Write with pretty formatting
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Saved config to: {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise Exception(f"Failed to save config: {e}") from e

    async def add_server(self, name: str, server_config: dict[str, Any]) -> dict[str, Any]:
        """Add a server to the configuration"""
        await self.load_config()

        if name in self.config.get("mcpServers", {}):
            return {"error": f"Server '{name}' already exists in config"}

        # Backup before making changes
        backup_path = await self.backup_config()

        # Add the server
        if "mcpServers" not in self.config:
            self.config["mcpServers"] = {}

        self.config["mcpServers"][name] = server_config

        # Save the updated config
        await self.save_config()

        return {
            "status": "added",
            "name": name,
            "config": server_config,
            "backup": backup_path,
            "config_path": str(self.config_path),
        }

    async def remove_server(self, name: str) -> dict[str, Any]:
        """Remove a server from the configuration"""
        await self.load_config()

        if name not in self.config.get("mcpServers", {}):
            return {"error": f"Server '{name}' not found in config"}

        # Backup before making changes
        backup_path = await self.backup_config()

        # Remove the server
        removed_config = self.config["mcpServers"].pop(name)

        # Save the updated config
        await self.save_config()

        return {
            "status": "removed",
            "name": name,
            "removed_config": removed_config,
            "backup": backup_path,
        }

    async def list_configured(self) -> list[dict[str, Any]]:
        """List all configured servers"""
        await self.load_config()

        servers = []
        for name, config in self.config.get("mcpServers", {}).items():
            servers.append(
                {
                    "name": name,
                    "command": config.get("command", ""),
                    "args": config.get("args", []),
                    "env": config.get("env", {}),
                }
            )

        return servers

    async def get_server_config(self, name: str) -> Optional[dict[str, Any]]:
        """Get configuration for a specific server"""
        await self.load_config()
        return self.config.get("mcpServers", {}).get(name)

    async def restore_backup(self, backup_name: str) -> dict[str, Any]:
        """Restore a configuration backup"""
        backup_path = self.backup_dir / backup_name

        if not backup_path.exists():
            # Try full path
            backup_path = Path(backup_name)
            if not backup_path.exists():
                return {"error": f"Backup not found: {backup_name}"}

        try:
            # Backup current config first
            current_backup = await self.backup_config()

            # Copy backup to config location
            shutil.copy2(backup_path, self.config_path)

            # Reload config
            await self.load_config()

            return {
                "status": "restored",
                "restored_from": str(backup_path),
                "previous_backup": current_backup,
            }
        except Exception as e:
            return {"error": f"Failed to restore backup: {e}"}

    async def list_backups(self) -> list[dict[str, Any]]:
        """List all available backups"""
        backups = []

        for backup_file in sorted(self.backup_dir.glob("config_backup_*.json"), reverse=True):
            stat = backup_file.stat()
            backups.append(
                {
                    "name": backup_file.name,
                    "path": str(backup_file),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )

        return backups

    def generate_server_config(self, server_info: dict[str, Any]) -> dict[str, Any]:
        """Generate appropriate config for a server based on its installation method"""
        method = server_info.get("method", "")

        if method == "npm":
            package = server_info.get("package", "")
            return {"command": "npx", "args": ["-y", package]}
        elif method == "docker":
            image = server_info.get("image", "")
            return {"command": "docker", "args": ["run", "-i", "--rm", image]}
        elif method == "git":
            repo_path = server_info.get("path", "")
            # Assume there's a main script
            return {
                "command": "python",
                "args": [f"{repo_path}/server.py"],
                "env": {"PYTHONPATH": repo_path},
            }
        else:
            # Generic config
            return {"command": "echo", "args": ["Server needs manual configuration"]}
