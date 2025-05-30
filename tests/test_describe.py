#!/usr/bin/env python3
"""
Tests for describe - The MCP Package Manager

Copyright 2024 James Dominguez
Licensed under the Apache License, Version 2.0
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_manager import MCPConfigManager
from describe import MCPPackageManager, handle_request


@pytest.fixture
async def describe():
    """Create a test instance of MCPPackageManager"""
    manager = MCPPackageManager()
    # Use a temporary directory for testing
    manager.describe_HOME = Path("/tmp/test_describe")
    manager.INSTALLED_DB = manager.describe_HOME / "installed.json"
    manager.CACHE_DIR = manager.describe_HOME / "cache"
    manager._ensure_dirs()
    yield manager
    # Cleanup
    if manager.session:
        await manager.cleanup()


@pytest.mark.asyncio
async def test_list_tools():
    """Test that tool listing works correctly"""
    response = await handle_request({"method": "tools/list"})
    assert "tools" in response
    tools = response["tools"]
    assert len(tools) == 10
    tool_names = {tool["name"] for tool in tools}
    expected_tools = {
        "list",
        "search",
        "install",
        "uninstall",
        "installed",
        "config-add",
        "config-remove",
        "config-list",
        "config-backup",
        "config-restore",
    }
    assert tool_names == expected_tools


@pytest.mark.asyncio
async def test_search_functionality(describe):
    """Test search functionality"""
    # Mock registry - bypass network call
    describe.registry = {
        "test-server": {"description": "A test MCP server"},
        "another-server": {"description": "Another server for testing"},
        "database-tool": {"description": "Database management MCP"},
    }

    with patch.object(describe, "_fetch_registry", new_callable=AsyncMock) as mock_fetch:
        results = await describe.search("test")

    assert len(results) == 2
    assert any(r["name"] == "test-server" for r in results)
    assert any(r["name"] == "another-server" for r in results)


@pytest.mark.asyncio
async def test_install_npm_package(describe):
    """Test npm package installation"""
    describe.registry = {"test-package": {"npm": "@test/package", "description": "Test package"}}

    with patch.object(describe, "_fetch_registry", new_callable=AsyncMock):
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b"", b""))
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            result = await describe.install("test-package")

            assert result["method"] == "npm"
            assert result["package"] == "@test/package"
            assert result["status"] == "installed"
            mock_exec.assert_called_once_with(
                "npm",
                "install",
                "-g",
                "@test/package",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )


@pytest.mark.asyncio
async def test_install_already_installed(describe):
    """Test installing an already installed package"""
    describe.installed = {"existing-package": {"method": "npm", "details": {}}}
    describe.registry = {"existing-package": {"npm": "@existing/package"}}

    with patch.object(describe, "_fetch_registry", new_callable=AsyncMock):
        with patch.object(describe, "_load_installed", new_callable=AsyncMock):
            result = await describe.install("existing-package")

    assert "error" in result
    assert "already installed" in result["error"]


@pytest.mark.asyncio
async def test_uninstall_package(describe):
    """Test package uninstallation"""
    # Setup installed package
    describe.installed = {
        "test-package": {
            "method": "git",
            "details": {"path": "/tmp/test_describe/repos/test-package"},
        }
    }

    with patch("pathlib.Path.exists", return_value=True):
        with patch("shutil.rmtree") as mock_rmtree:
            result = await describe.uninstall("test-package")

            assert result["status"] == "uninstalled"
            assert result["name"] == "test-package"
            assert "test-package" not in describe.installed


@pytest.mark.asyncio
async def test_list_installed_empty(describe):
    """Test listing installed packages when none are installed"""
    describe.installed = {}
    result = await describe.list_installed()
    assert result == []


@pytest.mark.asyncio
async def test_registry_fetch_error(describe):
    """Test handling of registry fetch errors"""
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_get.side_effect = Exception("Network error")

        with pytest.raises(Exception):
            await describe._fetch_registry()


@pytest.mark.asyncio
async def test_config_list_empty():
    """Test config-list tool with no configs"""
    request = {"method": "tools/call", "params": {"name": "config-list", "arguments": {}}}

    with patch.object(
        MCPConfigManager, "load_config", new_callable=AsyncMock, return_value={"mcpServers": {}}
    ):
        response = await handle_request(request)

    assert "content" in response
    result = json.loads(response["content"][0]["text"])
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_config_add_not_installed():
    """Test config-add with server not installed"""
    request = {
        "method": "tools/call",
        "params": {"name": "config-add", "arguments": {"name": "nonexistent-server"}},
    }

    response = await handle_request(request)
    assert "content" in response
    result = json.loads(response["content"][0]["text"])
    assert "error" in result
    assert "not installed" in result["error"]


@pytest.mark.asyncio
async def test_config_backup():
    """Test config backup functionality"""
    request = {"method": "tools/call", "params": {"name": "config-backup", "arguments": {}}}

    with patch.object(MCPConfigManager, "backup_config") as mock_backup:
        mock_backup.return_value = "/tmp/backup_20240101_120000"

        response = await handle_request(request)

    assert "content" in response
    result = json.loads(response["content"][0]["text"])
    assert "backup" in result
    assert result["backup"] == "/tmp/backup_20240101_120000"


def test_config_manager_initialization():
    """Test config manager initialization"""
    config_mgr = MCPConfigManager()

    # Should not crash and should initialize properly
    assert config_mgr.backup_dir.exists()
    assert config_mgr.config_path is not None


def test_config_manager_generate_config():
    """Test server config generation"""
    config_mgr = MCPConfigManager()

    # Test npm server config
    npm_details = {"method": "npm", "package": "@test/server"}
    config = config_mgr.generate_server_config(npm_details)
    assert config["command"] == "npx"
    assert config["args"] == ["-y", "@test/server"]

    # Test git server config
    git_details = {"method": "git", "path": "/tmp/test-repo"}
    config = config_mgr.generate_server_config(git_details)
    assert config["command"] == "python"
    assert "/tmp/test-repo/server.py" in config["args"][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
