#!/usr/bin/env python3
"""
Tests for describe - AI-native MCP capability manager.

Copyright 2024 James Dominguez
Licensed under the Apache License, Version 2.0
"""

import os
import subprocess
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_manager import MCPConfigManager
from describe import MCPPackageManager, handle_request


@pytest.fixture
async def manager(tmp_path):
    package_manager = MCPPackageManager(home=tmp_path, registry_url="builtin")
    yield package_manager
    await package_manager.cleanup()


@pytest.mark.asyncio
async def test_initialize_advertises_modern_mcp_surface(monkeypatch, tmp_path):
    monkeypatch.setenv("DESCRIBE_HOME", str(tmp_path))
    monkeypatch.setenv("DESCRIBE_REGISTRY", "builtin")

    response = await handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert response["result"]["protocolVersion"] == "2025-11-25"
    assert response["result"]["capabilities"] == {
        "tools": {"listChanged": True},
        "resources": {"listChanged": True},
        "prompts": {"listChanged": True},
    }
    assert response["result"]["serverInfo"]["version"] == "1.1.0"


@pytest.mark.asyncio
async def test_list_tools(monkeypatch, tmp_path):
    monkeypatch.setenv("DESCRIBE_HOME", str(tmp_path))
    monkeypatch.setenv("DESCRIBE_REGISTRY", "builtin")

    response = await handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

    tools = response["result"]["tools"]
    tool_names = {tool["name"] for tool in tools}
    assert tool_names == {
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
        "registry-refresh",
    }
    assert all("inputSchema" in tool for tool in tools)
    assert any(tool["name"] == "search" and "outputSchema" in tool for tool in tools)


@pytest.mark.asyncio
async def test_search_functionality(manager):
    manager._index_registry(
        [
            {"name": "io.test/test-server", "description": "A test MCP server"},
            {"name": "io.test/another-server", "description": "Another server for testing"},
            {"name": "io.test/database-tool", "description": "Database management MCP"},
        ],
        "test",
    )

    results = await manager.search("test")

    assert len(results) == 3
    assert any(result["name"] == "test" for result in results)
    assert any(result["name"] == "another" for result in results)


@pytest.mark.asyncio
async def test_search_uses_registry_search_when_cache_misses(tmp_path):
    package_manager = MCPPackageManager(
        home=tmp_path, registry_url="https://registry.example.test/v0.1/servers"
    )
    package_manager._index_registry(
        [{"name": "io.example/local-only", "description": "Nothing relevant"}],
        "official-registry",
    )
    remote_result = {
        "name": "io.github.example/github-review",
        "title": "GitHub Review",
        "description": "Review pull requests",
        "packages": [{"registryType": "npm", "identifier": "@example/github-review"}],
    }

    with patch.object(
        package_manager, "_search_remote_registry", new_callable=AsyncMock
    ) as mock_search:
        mock_search.return_value = [
            package_manager._normalize_server("0", remote_result, "official-registry-search")
        ]
        results = await package_manager.search("github")

    assert results[0]["registryName"] == "io.github.example/github-review"
    await package_manager.cleanup()


@pytest.mark.asyncio
async def test_install_npm_package(manager):
    manager._index_registry(
        [
            {
                "name": "io.test/test-package",
                "description": "Test package",
                "packages": [
                    {
                        "registryType": "npm",
                        "identifier": "@test/package",
                        "transport": {"type": "stdio"},
                    }
                ],
            }
        ],
        "test",
    )

    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        result = await manager.install("test-package")

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
async def test_install_already_installed(manager):
    manager._index_registry(
        [
            {
                "name": "io.test/existing-package",
                "packages": [{"registryType": "npm", "identifier": "@existing/package"}],
            }
        ],
        "test",
    )
    manager.installed = {"existing-package": {"method": "npm", "details": {}}}
    await manager._save_installed()

    result = await manager.install("existing-package")

    assert "error" in result
    assert "already installed" in result["error"]


@pytest.mark.asyncio
async def test_remote_server_install_is_config_only(manager):
    manager._index_registry(
        [
            {
                "name": "com.example/analytics",
                "remotes": [{"type": "streamable-http", "url": "https://example.com/mcp"}],
            }
        ],
        "test",
    )

    result = await manager.install("analytics")

    assert result["method"] == "remote"
    assert result["url"] == "https://example.com/mcp"
    assert result["status"] == "configured"


@pytest.mark.asyncio
async def test_uninstall_package(manager, tmp_path):
    repo_path = tmp_path / "repos" / "test-package"
    repo_path.mkdir(parents=True)
    manager.installed = {
        "test-package": {
            "method": "git",
            "details": {"path": str(repo_path)},
        }
    }
    await manager._save_installed()

    with patch("shutil.rmtree") as mock_rmtree:
        result = await manager.uninstall("test-package")

    assert result["status"] == "uninstalled"
    assert result["name"] == "test-package"
    mock_rmtree.assert_called_once_with(repo_path.resolve())


@pytest.mark.asyncio
async def test_list_installed_empty(manager):
    result = await manager.list_installed()

    assert result == []


@pytest.mark.asyncio
async def test_registry_fetch_falls_back_to_builtin(tmp_path):
    package_manager = MCPPackageManager(
        home=tmp_path, registry_url="https://registry.example.test/v0.1/servers"
    )
    with patch.object(
        package_manager, "_fetch_remote_registry", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.side_effect = Exception("Network error")
        await package_manager._fetch_registry(force=True)

    assert package_manager.registry_source == "built-in"
    assert "filesystem" in package_manager.registry
    await package_manager.cleanup()


@pytest.mark.asyncio
async def test_config_list_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("DESCRIBE_HOME", str(tmp_path))
    monkeypatch.setenv("DESCRIBE_REGISTRY", "builtin")
    request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "config-list", "arguments": {}},
    }

    with patch.object(
        MCPConfigManager, "load_config", new_callable=AsyncMock, return_value={"mcpServers": {}}
    ):
        response = await handle_request(request)

    assert response["result"]["structuredContent"] == {"servers": [], "count": 0}


@pytest.mark.asyncio
async def test_config_add_not_installed(monkeypatch, tmp_path):
    monkeypatch.setenv("DESCRIBE_HOME", str(tmp_path))
    monkeypatch.setenv("DESCRIBE_REGISTRY", "builtin")
    request = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {"name": "config-add", "arguments": {"name": "nonexistent-server"}},
    }

    response = await handle_request(request)

    result = response["result"]["structuredContent"]
    assert "error" in result
    assert "not installed" in result["error"]


@pytest.mark.asyncio
async def test_resources_and_prompts(monkeypatch, tmp_path):
    monkeypatch.setenv("DESCRIBE_HOME", str(tmp_path))
    monkeypatch.setenv("DESCRIBE_REGISTRY", "builtin")

    resources = await handle_request({"jsonrpc": "2.0", "id": 5, "method": "resources/list"})
    assert {item["uri"] for item in resources["result"]["resources"]} >= {
        "describe://registry/available",
        "describe://servers/installed",
        "describe://guide/agent-stack",
    }

    resource = await handle_request(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "resources/read",
            "params": {"uri": "describe://guide/agent-stack"},
        }
    )
    assert "AI-native MCP stack design" in resource["result"]["contents"][0]["text"]

    prompt = await handle_request(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "prompts/get",
            "params": {
                "name": "compose-agent-stack",
                "arguments": {"goal": "review GitHub pull requests"},
            },
        }
    )
    assert "review GitHub pull requests" in prompt["result"]["messages"][0]["content"]["text"]


def test_config_manager_initialization(tmp_path):
    config_mgr = MCPConfigManager(home=tmp_path)

    assert config_mgr.backup_dir.exists()
    assert config_mgr.config_path is not None


def test_config_manager_generate_config(tmp_path, monkeypatch):
    monkeypatch.setenv("API_KEY", "secret-from-env")
    config_mgr = MCPConfigManager(home=tmp_path)

    npm_details = {
        "method": "npm",
        "package": "@test/server",
        "environmentVariables": [{"name": "API_KEY", "isSecret": True}],
        "packageArguments": [{"default": "--readonly"}],
    }
    config = config_mgr.generate_server_config(npm_details)
    assert config["command"] == "npx"
    assert config["args"] == ["-y", "@test/server", "--readonly"]
    assert config["env"] == {"API_KEY": "secret-from-env"}

    remote_details = {
        "method": "remote",
        "url": "https://example.com/mcp",
        "transport": {"type": "streamable-http"},
    }
    config = config_mgr.generate_server_config(remote_details)
    assert config == {"type": "streamable-http", "url": "https://example.com/mcp"}

    git_details = {"method": "git", "path": str(tmp_path / "repo")}
    config = config_mgr.generate_server_config(git_details)
    assert config["command"] == "python"
    assert "server.py" in config["args"][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
