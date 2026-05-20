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
from typing import Any, Optional, Union

logger = logging.getLogger("describe.config")


class MCPConfigManager:
    """Manages MCP configuration files across different platforms."""

    def __init__(
        self,
        home: Optional[Union[Path, str]] = None,
        config_path: Optional[Union[Path, str]] = None,
    ):
        self.home = Path(home or os.environ.get("DESCRIBE_HOME", Path.home() / ".describe"))
        self.config_path = (
            Path(config_path).expanduser() if config_path else self._find_config_path()
        )
        self.config: dict[str, Any] = {}
        self.backup_dir = self.home / "backups"
        self.backup_dir.mkdir(exist_ok=True, parents=True)

    def _find_config_path(self) -> Optional[Path]:
        """Find the MCP config file based on platform"""
        override = os.environ.get("DESCRIBE_MCP_CONFIG")
        if override:
            return Path(override).expanduser()

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
            try:
                if path.exists():
                    logger.info(f"Found MCP config at: {path}")
                    return path
            except OSError as e:
                logger.debug(f"Cannot inspect MCP config candidate {path}: {e}")

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
            with open(self.config_path, encoding="utf-8") as f:
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
            with open(self.config_path, "w", encoding="utf-8") as f:
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
            server = {
                "name": name,
                "command": config.get("command", ""),
                "args": config.get("args", []),
                "env": config.get("env", {}),
            }
            if "type" in config:
                server["type"] = config["type"]
            if "url" in config:
                server["url"] = config["url"]
            servers.append(server)

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
        env = self._environment_from_registry(server_info)
        package_args = self._package_args_from_registry(server_info)

        if method == "npm":
            package = server_info.get("package", "")
            config: dict[str, Any] = {"command": "npx", "args": ["-y", package, *package_args]}
            if env:
                config["env"] = env
            return config
        elif method == "docker":
            image = server_info.get("image", "")
            config = {"command": "docker", "args": ["run", "-i", "--rm", image, *package_args]}
            if env:
                config["env"] = env
            return config
        elif method == "pypi":
            package = server_info.get("package", "")
            config = {"command": "uvx", "args": [package, *package_args]}
            if env:
                config["env"] = env
            return config
        elif method == "remote":
            url = server_info.get("url", "")
            transport = server_info.get("transport", {}).get("type", "streamable-http")
            return {"type": transport, "url": url}
        elif method == "git":
            repo_path = server_info.get("path", "")
            # Assume there's a main script
            config = {
                "command": "python",
                "args": [f"{repo_path}/server.py"],
                "env": {"PYTHONPATH": repo_path},
            }
            config["env"].update(env)
            return config
        else:
            # Generic config
            return {"command": "echo", "args": ["Server needs manual configuration"]}

    @staticmethod
    def _environment_from_registry(server_info: dict[str, Any]) -> dict[str, str]:
        env: dict[str, str] = {}
        for item in server_info.get("environmentVariables", []):
            name = item.get("name")
            if not name:
                continue
            if os.environ.get(name):
                env[name] = os.environ[name]
            elif "default" in item and not item.get("isSecret"):
                env[name] = str(item["default"])
        return env

    @staticmethod
    def _package_args_from_registry(server_info: dict[str, Any]) -> list[str]:
        args: list[str] = []
        for item in server_info.get("packageArguments", []):
            value = item.get("default") or item.get("value")
            if value is None:
                continue
            if isinstance(value, list):
                args.extend(str(part) for part in value)
            else:
                args.append(str(value))
        return args
