#!/usr/bin/env python3
"""
describe - AI-native MCP capability manager.

describe discovers, installs, and configures MCP servers, then exposes the
result as tools, resources, and prompts that an AI client can reason over.

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

import argparse
import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from config_manager import MCPConfigManager

VERSION = "1.1.0"
MCP_PROTOCOL_VERSION = os.environ.get("DESCRIBE_MCP_PROTOCOL_VERSION", "2025-11-25")
DEFAULT_REGISTRY_URL = "https://registry.modelcontextprotocol.io/v0.1/servers"
DEFAULT_REGISTRY_LIMIT = 250
DEFAULT_CACHE_TTL_SECONDS = 60 * 60

DESCRIBE_HOME = Path(os.environ.get("DESCRIBE_HOME", Path.home() / ".describe")).expanduser()
INSTALLED_DB = DESCRIBE_HOME / "installed.json"
CACHE_DIR = DESCRIBE_HOME / "cache"
REGISTRY_URL = os.environ.get("DESCRIBE_REGISTRY", DEFAULT_REGISTRY_URL)

logging.basicConfig(
    level=os.environ.get("DESCRIBE_LOG_LEVEL", "WARNING").upper(),
    stream=sys.stderr,
)
logger = logging.getLogger("describe")


def _fallback_registry() -> dict[str, dict[str, Any]]:
    """Small, known-good catalog used when the official Registry is unavailable."""
    servers = {
        "filesystem": (
            "Filesystem",
            "Secure local filesystem access for approved directories.",
            "@modelcontextprotocol/server-filesystem",
        ),
        "postgres": (
            "Postgres",
            "Read-only PostgreSQL access with schema inspection.",
            "@modelcontextprotocol/server-postgres",
        ),
        "brave-search": (
            "Brave Search",
            "Web and local search using Brave Search API.",
            "@modelcontextprotocol/server-brave-search",
        ),
        "github": (
            "GitHub",
            "Repository, issue, pull request, and file operations through GitHub.",
            "@modelcontextprotocol/server-github",
        ),
        "git": (
            "Git",
            "Read, search, and manipulate local Git repositories.",
            "@modelcontextprotocol/server-git",
        ),
        "fetch": (
            "Fetch",
            "Fetch and convert web content for efficient model context.",
            "@modelcontextprotocol/server-fetch",
        ),
        "puppeteer": (
            "Puppeteer",
            "Browser automation and web scraping.",
            "@modelcontextprotocol/server-puppeteer",
        ),
        "memory": (
            "Memory",
            "Knowledge graph based persistent memory.",
            "@modelcontextprotocol/server-memory",
        ),
        "gdrive": (
            "Google Drive",
            "Google Drive file access and search.",
            "@modelcontextprotocol/server-gdrive",
        ),
        "google-maps": (
            "Google Maps",
            "Location, directions, and place detail tools.",
            "@modelcontextprotocol/server-google-maps",
        ),
        "sequential-thinking": (
            "Sequential Thinking",
            "Structured reasoning workspace for multi-step problems.",
            "@modelcontextprotocol/server-sequential-thinking",
        ),
        "time": (
            "Time",
            "Time zone conversion and current-time tools.",
            "@modelcontextprotocol/server-time",
        ),
    }

    return {
        key: {
            "name": f"io.modelcontextprotocol/{key}",
            "title": title,
            "description": description,
            "version": "latest",
            "status": "active",
            "packages": [
                {
                    "registryType": "npm",
                    "identifier": package,
                    "transport": {"type": "stdio"},
                }
            ],
            "_meta": {"describe/fallbackAlias": key},
        }
        for key, (title, description, package) in servers.items()
    }


FALLBACK_REGISTRY = _fallback_registry()


def _json_dumps(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True)


def _safe_int(value: Optional[str], default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _now() -> float:
    return time.time()


class MCPPackageManager:
    def __init__(
        self,
        home: Optional[Union[Path, str]] = None,
        registry_url: Optional[str] = None,
        cache_ttl_seconds: Optional[int] = None,
        registry_limit: Optional[int] = None,
    ):
        self.home = Path(home or os.environ.get("DESCRIBE_HOME", DESCRIBE_HOME)).expanduser()
        self.installed_db = self.home / "installed.json"
        self.cache_dir = self.home / "cache"
        self.registry_cache = self.cache_dir / "registry.json"
        self.registry_url = registry_url or os.environ.get("DESCRIBE_REGISTRY", REGISTRY_URL)
        self.cache_ttl_seconds = cache_ttl_seconds or _safe_int(
            os.environ.get("DESCRIBE_CACHE_TTL_SECONDS"), DEFAULT_CACHE_TTL_SECONDS
        )
        self.registry_limit = registry_limit or _safe_int(
            os.environ.get("DESCRIBE_REGISTRY_LIMIT"), DEFAULT_REGISTRY_LIMIT
        )
        self.session = None
        self.registry: dict[str, dict[str, Any]] = {}
        self.aliases: dict[str, str] = {}
        self.installed: dict[str, Any] = {}
        self.registry_source = "unloaded"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create describe's local state directories."""
        self.home.mkdir(exist_ok=True, parents=True)
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        if not self.installed_db.exists():
            self.installed_db.write_text("{}", encoding="utf-8")

    async def _load_installed(self) -> None:
        try:
            self.installed = json.loads(self.installed_db.read_text(encoding="utf-8"))
        except Exception:
            self.installed = {}

    async def _save_installed(self) -> None:
        self.installed_db.write_text(_json_dumps(self.installed), encoding="utf-8")

    def _cache_is_fresh(self) -> bool:
        if self.cache_ttl_seconds <= 0 or not self.registry_cache.exists():
            return False
        return (_now() - self.registry_cache.stat().st_mtime) <= self.cache_ttl_seconds

    def _load_cached_registry(self) -> Optional[list[dict[str, Any]]]:
        if not self.registry_cache.exists():
            return None
        try:
            payload = json.loads(self.registry_cache.read_text(encoding="utf-8"))
            servers = payload.get("servers", [])
            if isinstance(servers, list):
                return servers
        except Exception as exc:
            logger.debug("Failed to read registry cache: %s", exc)
        return None

    def _save_cached_registry(self, servers: list[dict[str, Any]], source: str) -> None:
        payload = {
            "fetchedAt": int(_now()),
            "source": source,
            "servers": servers,
        }
        self.registry_cache.write_text(_json_dumps(payload), encoding="utf-8")

    async def _fetch_registry_page(self, params: dict[str, Any]) -> dict[str, Any]:
        def read_json() -> dict[str, Any]:
            separator = "&" if "?" in self.registry_url else "?"
            url = f"{self.registry_url}{separator}{urlencode(params)}"
            request = Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": f"describe/{VERSION}",
                },
            )
            with urlopen(request, timeout=20) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return json.loads(response.read().decode(charset))

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, read_json)

    async def _fetch_remote_registry(self) -> list[dict[str, Any]]:
        servers: list[dict[str, Any]] = []
        cursor: Optional[str] = None

        while len(servers) < self.registry_limit:
            page_limit = min(100, self.registry_limit - len(servers))
            params: dict[str, Any] = {"limit": page_limit}
            if cursor:
                params["cursor"] = cursor

            payload = await self._fetch_registry_page(params)

            if isinstance(payload, dict) and isinstance(payload.get("servers"), list):
                servers.extend(payload["servers"])
                cursor = payload.get("metadata", {}).get("nextCursor")
                if not cursor:
                    break
                continue

            if isinstance(payload, dict) and isinstance(payload.get("objects"), list):
                servers.extend(self._normalize_npm_search(payload["objects"]))
                break

            if isinstance(payload, dict):
                servers.extend(value for value in payload.values() if isinstance(value, dict))
                break

            break

        if not servers:
            raise RuntimeError("Registry returned no servers")

        return servers

    async def _search_remote_registry(self, query: str) -> list[dict[str, Any]]:
        if self.registry_url.lower() == "builtin":
            return []

        payload = await self._fetch_registry_page(
            {"limit": min(100, self.registry_limit), "search": query}
        )
        if isinstance(payload, dict) and isinstance(payload.get("servers"), list):
            return [
                self._normalize_server(str(index), server, "official-registry-search")
                for index, server in enumerate(payload["servers"])
            ]
        return []

    @staticmethod
    def _normalize_npm_search(objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
        servers = []
        for item in objects:
            package = item.get("package", {})
            name = package.get("name")
            if not name:
                continue
            servers.append(
                {
                    "name": f"npm/{name}",
                    "title": name,
                    "description": package.get("description", ""),
                    "version": package.get("version", ""),
                    "packages": [
                        {
                            "registryType": "npm",
                            "identifier": name,
                            "version": package.get("version", ""),
                            "transport": {"type": "stdio"},
                        }
                    ],
                }
            )
        return servers

    async def _fetch_registry(self, force: bool = False) -> None:
        """Load MCP server registry data from cache, the official API, or fallback."""
        if self.registry and not force:
            return

        if not force and self._cache_is_fresh():
            cached = self._load_cached_registry()
            if cached:
                self._index_registry(cached, "cache")
                return

        if self.registry_url.lower() == "builtin":
            self._index_registry(list(FALLBACK_REGISTRY.values()), "built-in")
            return

        try:
            servers = await self._fetch_remote_registry()
            self._save_cached_registry(servers, self.registry_url)
            self._index_registry(servers, "official-registry")
            return
        except Exception as exc:
            logger.warning("Registry fetch failed; using fallback data: %s", exc)

        cached = self._load_cached_registry()
        if cached:
            self._index_registry(cached, "stale-cache")
            return

        self._index_registry(list(FALLBACK_REGISTRY.values()), "built-in")

    def _index_registry(self, servers: list[dict[str, Any]], source: str) -> None:
        self.registry = {}
        self.aliases = {}
        self.registry_source = source

        for index, server in enumerate(servers):
            fallback_key = str(server.get("_meta", {}).get("describe/fallbackAlias") or index)
            normalized = self._normalize_server(fallback_key, server, source)
            key = normalized["shortName"]
            if key in self.registry:
                key = normalized["name"]
            self.registry[key] = normalized
            for alias in normalized["aliases"]:
                self.aliases.setdefault(alias.lower(), key)

    def _normalize_server(
        self, fallback_key: str, server: dict[str, Any], source: str
    ) -> dict[str, Any]:
        if isinstance(server.get("server"), dict):
            registry_meta = server.get("_meta", {})
            official_meta = registry_meta.get("io.modelcontextprotocol.registry/official", {})
            server = {**server["server"], "_registryMeta": registry_meta}
            if official_meta.get("status"):
                server["status"] = official_meta["status"]
            server["isLatest"] = official_meta.get("isLatest", True)

        if "npm" in server and "packages" not in server:
            server = {
                **server,
                "packages": [
                    {
                        "registryType": "npm",
                        "identifier": server["npm"],
                        "transport": {"type": "stdio"},
                    }
                ],
            }

        name = str(server.get("name") or server.get("id") or fallback_key)
        title = str(server.get("title") or self._human_title(name))
        short_name = self._short_name(name, fallback_key)
        packages = server.get("packages", [])
        remotes = server.get("remotes", [])
        if not isinstance(packages, list):
            packages = []
        if not isinstance(remotes, list):
            remotes = []

        aliases = {name, short_name, title, fallback_key}
        for package in packages:
            identifier = package.get("identifier") or package.get("name")
            if identifier:
                aliases.update(
                    {
                        str(identifier),
                        self._short_name(str(identifier), str(identifier)),
                    }
                )

        methods = self._installation_candidates({"packages": packages, "remotes": remotes})
        return {
            "name": name,
            "shortName": short_name,
            "title": title,
            "description": str(server.get("description") or ""),
            "version": str(server.get("version") or ""),
            "status": str(server.get("status") or "active"),
            "isLatest": bool(server.get("isLatest", True)),
            "packages": packages,
            "remotes": remotes,
            "repository": server.get("repository", {}),
            "source": source,
            "installMethods": [method["method"] for method in methods],
            "aliases": sorted({alias.lower() for alias in aliases if alias}),
        }

    @staticmethod
    def _human_title(name: str) -> str:
        tail = name.split("/")[-1]
        for prefix in ("server-", "mcp-server-", "mcp-"):
            if tail.startswith(prefix):
                tail = tail[len(prefix) :]
        for suffix in ("-server", "-mcp"):
            if tail.endswith(suffix):
                tail = tail[: -len(suffix)]
        return tail.replace("-", " ").replace("_", " ").title()

    @classmethod
    def _short_name(cls, name: str, fallback: str) -> str:
        candidate = name.split("/")[-1].split(":")[-1].lower()
        for prefix in ("@modelcontextprotocol/server-", "server-", "mcp-server-", "mcp-"):
            if candidate.startswith(prefix):
                candidate = candidate[len(prefix) :]
        for suffix in ("-server", "-mcp"):
            if candidate.endswith(suffix):
                candidate = candidate[: -len(suffix)]
        return candidate or fallback

    def _installation_candidates(self, server: dict[str, Any]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []

        for package in server.get("packages", []):
            registry_type = (
                package.get("registryType")
                or package.get("registry_type")
                or package.get("registry")
                or ""
            ).lower()
            identifier = package.get("identifier") or package.get("name")
            if not identifier:
                continue

            if registry_type == "npm":
                candidates.append(
                    {
                        "method": "npm",
                        "package": identifier,
                        "version": package.get("version"),
                        "transport": package.get("transport", {}),
                        "environmentVariables": package.get("environmentVariables", []),
                        "packageArguments": package.get("packageArguments", []),
                    }
                )
            elif registry_type in {"oci", "docker"}:
                candidates.append(
                    {
                        "method": "docker",
                        "image": identifier,
                        "transport": package.get("transport", {}),
                        "environmentVariables": package.get("environmentVariables", []),
                        "packageArguments": package.get("packageArguments", []),
                    }
                )
            elif registry_type == "pypi":
                candidates.append(
                    {
                        "method": "pypi",
                        "package": identifier,
                        "version": package.get("version"),
                        "transport": package.get("transport", {}),
                        "environmentVariables": package.get("environmentVariables", []),
                        "packageArguments": package.get("packageArguments", []),
                    }
                )

        for remote in server.get("remotes", []):
            if remote.get("url"):
                candidates.append(
                    {
                        "method": "remote",
                        "url": remote["url"],
                        "transport": {"type": remote.get("type", "streamable-http")},
                        "variables": remote.get("variables", {}),
                    }
                )

        return candidates

    def _resolve_server(self, name: str) -> Optional[dict[str, Any]]:
        query = name.strip().lower()
        if not query:
            return None
        if query in self.registry:
            return self.registry[query]
        if query in self.aliases:
            return self.registry[self.aliases[query]]

        matches = [
            server
            for server in self.registry.values()
            if query
            in " ".join(
                [
                    server["name"].lower(),
                    server["shortName"].lower(),
                    server["title"].lower(),
                    server["description"].lower(),
                    " ".join(server["aliases"]),
                ]
            )
        ]
        if len(matches) == 1:
            return matches[0]
        return None

    async def list_available(self) -> list[dict[str, Any]]:
        await self._fetch_registry()
        await self._load_installed()
        installed_names = {
            str(value.get("server", {}).get("name") or key).lower()
            for key, value in self.installed.items()
        }
        servers = [
            {
                "name": server["shortName"],
                "registryName": server["name"],
                "title": server["title"],
                "description": server["description"],
                "version": server["version"],
                "status": server["status"],
                "source": server["source"],
                "installMethods": server["installMethods"],
                "installed": server["name"].lower() in installed_names
                or server["shortName"].lower() in self.installed,
            }
            for server in self.registry.values()
            if server["status"] != "deleted" and server["isLatest"]
        ]
        return sorted(servers, key=lambda item: item["name"])

    async def search(self, query: str) -> list[dict[str, Any]]:
        await self._fetch_registry()
        query = query.lower().strip()
        if not query:
            return await self.list_available()

        results = []
        for server in self.registry.values():
            if not server["isLatest"]:
                continue
            haystack = " ".join(
                [
                    server["name"],
                    server["shortName"],
                    server["title"],
                    server["description"],
                    " ".join(server["aliases"]),
                ]
            ).lower()
            if query in haystack:
                results.append(
                    {
                        "name": server["shortName"],
                        "registryName": server["name"],
                        "title": server["title"],
                        "description": server["description"],
                        "version": server["version"],
                        "status": server["status"],
                        "installMethods": server["installMethods"],
                    }
                )

        if self.registry_url.lower() != "builtin":
            try:
                known_names = {result["registryName"] for result in results}
                for server in await self._search_remote_registry(query):
                    if not server["isLatest"]:
                        continue
                    if server["name"] in known_names:
                        continue
                    known_names.add(server["name"])
                    results.append(
                        {
                            "name": server["shortName"],
                            "registryName": server["name"],
                            "title": server["title"],
                            "description": server["description"],
                            "version": server["version"],
                            "status": server["status"],
                            "installMethods": server["installMethods"],
                        }
                    )
            except Exception as exc:
                logger.debug("Registry search failed; using local cache only: %s", exc)
        return sorted(results, key=lambda item: item["name"])

    async def install(self, name: str, method: Optional[str] = None) -> dict[str, Any]:
        await self._fetch_registry()
        await self._load_installed()

        server = self._resolve_server(name)
        if server is None:
            return {"error": f"Server '{name}' not found in registry"}

        installed_key = server["shortName"]
        if installed_key in self.installed:
            return {"error": f"Server '{installed_key}' already installed"}

        candidates = self._installation_candidates(server)
        if method:
            candidates = [candidate for candidate in candidates if candidate["method"] == method]
        candidates = [
            candidate
            for candidate in candidates
            if candidate["method"] in {"npm", "docker", "remote", "pypi"}
        ]
        if not candidates:
            return {
                "error": f"No supported installation method found for '{server['name']}'",
                "availableMethods": server["installMethods"],
            }

        candidate = candidates[0]
        if candidate["method"] == "npm":
            result = await self._install_npm(candidate["package"])
        elif candidate["method"] == "docker":
            result = await self._install_docker(candidate["image"])
        elif candidate["method"] == "pypi":
            result = await self._install_pypi(candidate["package"])
        else:
            result = {
                "method": "remote",
                "url": candidate["url"],
                "transport": candidate.get("transport", {}),
                "status": "configured",
                "note": "Remote MCP servers do not require a local package install.",
            }

        if "error" not in result:
            details = {
                **result,
                "server": server,
                "environmentVariables": candidate.get("environmentVariables", []),
                "packageArguments": candidate.get("packageArguments", []),
                "variables": candidate.get("variables", {}),
            }
            self.installed[installed_key] = {"method": result["method"], "details": details}
            await self._save_installed()

        return result

    async def _install_npm(self, package: str) -> dict[str, Any]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "npm",
                "install",
                "-g",
                package,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            _stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                return {"method": "npm", "package": package, "status": "installed"}
            return {"error": stderr.decode(errors="replace")}
        except Exception as exc:
            return {"error": str(exc)}

    async def _install_docker(self, image: str) -> dict[str, Any]:
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker",
                "pull",
                image,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            _stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                return {"method": "docker", "image": image, "status": "pulled"}
            return {"error": stderr.decode(errors="replace")}
        except Exception as exc:
            return {"error": str(exc)}

    async def _install_pypi(self, package: str) -> dict[str, Any]:
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "pip",
                "install",
                "--user",
                package,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            _stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                return {"method": "pypi", "package": package, "status": "installed"}
            return {"error": stderr.decode(errors="replace")}
        except Exception as exc:
            return {"error": str(exc)}

    async def uninstall(self, name: str) -> dict[str, Any]:
        await self._load_installed()

        key = name.lower()
        if key not in self.installed:
            return {"error": f"Server '{name}' not installed"}

        info = self.installed[key]
        details = info.get("details", {})
        if info.get("method") == "git" and details.get("path"):
            path = Path(details["path"]).expanduser().resolve()
            home = self.home.resolve()
            if path.exists() and (path == home or home in path.parents):
                shutil.rmtree(path)

        del self.installed[key]
        await self._save_installed()
        return {"status": "uninstalled", "name": key}

    async def list_installed(self) -> list[dict[str, Any]]:
        await self._load_installed()
        return [{"name": key, **value} for key, value in sorted(self.installed.items())]

    async def refresh_registry(self) -> dict[str, Any]:
        await self._fetch_registry(force=True)
        return {
            "status": "refreshed",
            "source": self.registry_source,
            "count": len(self.registry),
            "cache": str(self.registry_cache),
        }

    async def cleanup(self) -> None:
        return None


def tool_definitions() -> list[dict[str, Any]]:
    def string_arg(description: str) -> dict[str, str]:
        return {"type": "string", "description": description}

    return [
        {
            "name": "list",
            "title": "List MCP Servers",
            "description": "List servers available from the official MCP Registry cache.",
            "inputSchema": {"type": "object", "properties": {}},
            "outputSchema": {
                "type": "object",
                "properties": {"servers": {"type": "array"}, "count": {"type": "integer"}},
                "required": ["servers", "count"],
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "search",
            "title": "Search MCP Servers",
            "description": "Search registry servers by name, package, capability, or description.",
            "inputSchema": {
                "type": "object",
                "properties": {"query": string_arg("Search query.")},
                "required": ["query"],
            },
            "outputSchema": {
                "type": "object",
                "properties": {"servers": {"type": "array"}, "count": {"type": "integer"}},
                "required": ["servers", "count"],
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": True},
        },
        {
            "name": "install",
            "title": "Install MCP Server",
            "description": "Install or register an MCP server from the registry.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": string_arg("Server short name, registry name, or package name."),
                    "method": string_arg("Optional method: npm, docker, pypi, or remote."),
                },
                "required": ["name"],
            },
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": True,
            },
        },
        {
            "name": "uninstall",
            "title": "Uninstall MCP Server",
            "description": "Remove a server from describe's installed database.",
            "inputSchema": {
                "type": "object",
                "properties": {"name": string_arg("Installed server name.")},
                "required": ["name"],
            },
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": True,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        },
        {
            "name": "installed",
            "title": "List Installed Servers",
            "description": "List MCP servers currently tracked by describe.",
            "inputSchema": {"type": "object", "properties": {}},
            "annotations": {"readOnlyHint": True, "openWorldHint": False},
        },
        {
            "name": "config-add",
            "title": "Add Server Config",
            "description": "Add an installed server to the MCP client configuration.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": string_arg("Installed server name."),
                    "command": string_arg("Optional command override."),
                    "args": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name"],
            },
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        },
        {
            "name": "config-remove",
            "title": "Remove Server Config",
            "description": "Remove a server from the MCP client configuration.",
            "inputSchema": {
                "type": "object",
                "properties": {"name": string_arg("Configured server name.")},
                "required": ["name"],
            },
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": True,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        },
        {
            "name": "config-list",
            "title": "List MCP Config",
            "description": "List servers currently present in the MCP client configuration.",
            "inputSchema": {"type": "object", "properties": {}},
            "annotations": {"readOnlyHint": True, "openWorldHint": False},
        },
        {
            "name": "config-backup",
            "title": "Back Up MCP Config",
            "description": "Create a timestamped backup of the MCP client configuration.",
            "inputSchema": {"type": "object", "properties": {}},
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": False,
                "openWorldHint": False,
            },
        },
        {
            "name": "config-restore",
            "title": "Restore MCP Config",
            "description": "Restore a previously created MCP client configuration backup.",
            "inputSchema": {
                "type": "object",
                "properties": {"backup": string_arg("Backup filename or path.")},
                "required": ["backup"],
            },
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": True,
                "idempotentHint": False,
                "openWorldHint": False,
            },
        },
        {
            "name": "registry-refresh",
            "title": "Refresh Registry",
            "description": "Refresh describe's MCP Registry cache.",
            "inputSchema": {"type": "object", "properties": {}},
            "annotations": {
                "readOnlyHint": False,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": True,
            },
        },
    ]


def resource_definitions() -> list[dict[str, Any]]:
    return [
        {
            "uri": "describe://registry/available",
            "name": "available_servers",
            "title": "Available MCP Servers",
            "description": "Registry servers currently visible to describe.",
            "mimeType": "application/json",
            "annotations": {"audience": ["assistant"], "priority": 0.9},
        },
        {
            "uri": "describe://servers/installed",
            "name": "installed_servers",
            "title": "Installed Servers",
            "description": "Servers installed or registered through describe.",
            "mimeType": "application/json",
            "annotations": {"audience": ["assistant"], "priority": 0.8},
        },
        {
            "uri": "describe://guide/agent-stack",
            "name": "agent_stack_guide",
            "title": "Agent Stack Guide",
            "description": "A short guide for composing MCP servers into AI-native workflows.",
            "mimeType": "text/markdown",
            "annotations": {"audience": ["assistant", "user"], "priority": 0.7},
        },
    ]


def prompt_definitions() -> list[dict[str, Any]]:
    return [
        {
            "name": "compose-agent-stack",
            "title": "Compose Agent Stack",
            "description": "Plan the smallest MCP server set for a workflow.",
            "arguments": [
                {
                    "name": "goal",
                    "title": "Goal",
                    "description": "The user workflow or system to build.",
                    "required": True,
                }
            ],
        },
        {
            "name": "harden-mcp-config",
            "title": "Harden MCP Config",
            "description": "Review an MCP setup for secrets, scope, and risky tools.",
        },
    ]


async def read_resource(uri: str, manager: MCPPackageManager) -> dict[str, Any]:
    if uri == "describe://registry/available":
        servers = await manager.list_available()
        text = _json_dumps(
            {
                "source": manager.registry_source,
                "count": len(servers),
                "servers": servers,
            }
        )
        mime_type = "application/json"
    elif uri == "describe://servers/installed":
        installed = await manager.list_installed()
        text = _json_dumps({"count": len(installed), "servers": installed})
        mime_type = "application/json"
    elif uri == "describe://guide/agent-stack":
        text = (
            "# AI-native MCP stack design\n\n"
            "Start with the task, not the package name. Pick the smallest set of MCP "
            "servers that gives the model the right sensory inputs, controlled actions, "
            "and durable state.\n\n"
            "1. Add context servers first: filesystem, git, database, docs, or search.\n"
            "2. Add action servers only when the workflow needs them: GitHub, browser, "
            "deployment, messaging, or internal APIs.\n"
            "3. Keep secrets explicit and scoped. Prefer read-only servers for inspection.\n"
            "4. Use describe resources to show the model what is installed before asking "
            "it to install more.\n"
        )
        mime_type = "text/markdown"
    else:
        return {"error": f"Unknown resource: {uri}"}

    return {"contents": [{"uri": uri, "mimeType": mime_type, "text": text}]}


def get_prompt(name: str, arguments: Optional[dict[str, str]] = None) -> dict[str, Any]:
    arguments = arguments or {}
    if name == "compose-agent-stack":
        goal = arguments.get("goal", "the user's workflow")
        text = (
            "Design a minimal, safe MCP server stack for this goal:\n\n"
            f"{goal}\n\n"
            "Return the recommended servers, why each one is needed, which operations "
            "should stay read-only, which credentials are required, and the smallest "
            "next command to run through describe."
        )
    elif name == "harden-mcp-config":
        text = (
            "Review the current MCP configuration. Identify broad filesystem scopes, "
            "unnecessary write-capable tools, missing environment variables, duplicated "
            "servers, stale packages, and secrets that should move into environment "
            "variables. Recommend the smallest corrective changes."
        )
    else:
        return {"error": f"Unknown prompt: {name}"}

    return {
        "description": next(
            prompt["description"] for prompt in prompt_definitions() if prompt["name"] == name
        ),
        "messages": [{"role": "user", "content": {"type": "text", "text": text}}],
    }


def jsonrpc_result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def jsonrpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def tool_call_result(payload: Any) -> dict[str, Any]:
    structured = payload if isinstance(payload, dict) else {"result": payload}
    result = {
        "content": [{"type": "text", "text": _json_dumps(payload)}],
        "structuredContent": structured,
    }
    if isinstance(payload, dict) and "error" in payload:
        result["isError"] = True
    return result


async def call_tool(tool: str, args: dict[str, Any], manager: MCPPackageManager) -> Any:
    if tool == "list":
        servers = await manager.list_available()
        return {"servers": servers, "count": len(servers), "source": manager.registry_source}
    if tool == "search":
        servers = await manager.search(str(args.get("query", "")))
        return {"servers": servers, "count": len(servers)}
    if tool == "install":
        return await manager.install(args.get("name", ""), args.get("method"))
    if tool == "uninstall":
        return await manager.uninstall(args.get("name", ""))
    if tool == "installed":
        servers = await manager.list_installed()
        return {"servers": servers, "count": len(servers)}
    if tool == "config-add":
        config_mgr = MCPConfigManager(home=manager.home)
        server_name = str(args.get("name", "")).lower()

        await manager._load_installed()
        if server_name not in manager.installed:
            return {"error": f"Server '{server_name}' not installed. Install it first."}

        server_info = manager.installed[server_name]
        server_config = config_mgr.generate_server_config(server_info["details"])

        if "command" in args:
            server_config["command"] = args["command"]
        if "args" in args:
            server_config["args"] = args["args"]

        return await config_mgr.add_server(server_name, server_config)
    if tool == "config-remove":
        config_mgr = MCPConfigManager(home=manager.home)
        return await config_mgr.remove_server(args.get("name", ""))
    if tool == "config-list":
        config_mgr = MCPConfigManager(home=manager.home)
        servers = await config_mgr.list_configured()
        return {"servers": servers, "count": len(servers)}
    if tool == "config-backup":
        config_mgr = MCPConfigManager(home=manager.home)
        backup_path = await config_mgr.backup_config()
        return {"backup": backup_path}
    if tool == "config-restore":
        config_mgr = MCPConfigManager(home=manager.home)
        return await config_mgr.restore_backup(args.get("backup", ""))
    if tool == "registry-refresh":
        return await manager.refresh_registry()
    return {"error": f"Unknown tool: {tool}"}


async def handle_request(request: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Dispatch one JSON-RPC MCP request."""
    manager = MCPPackageManager()
    request_id = request.get("id")

    try:
        method = request.get("method", "")
        params = request.get("params", {}) or {}

        if method == "initialize":
            return jsonrpc_result(
                request_id,
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {"listChanged": True},
                        "prompts": {"listChanged": True},
                    },
                    "serverInfo": {
                        "name": "describe",
                        "title": "describe",
                        "version": VERSION,
                        "description": "AI-native MCP capability discovery, install, and config.",
                        "websiteUrl": "https://github.com/keppy/describe",
                    },
                    "instructions": (
                        "Use describe to discover MCP servers, install the smallest useful "
                        "capability set, and expose installed state as model-readable resources."
                    ),
                },
            )

        if method == "initialized":
            return None

        if method == "tools/list":
            return jsonrpc_result(request_id, {"tools": tool_definitions()})

        if method == "tools/call":
            payload = await call_tool(
                params.get("name", ""), params.get("arguments", {}) or {}, manager
            )
            return jsonrpc_result(request_id, tool_call_result(payload))

        if method == "resources/list":
            return jsonrpc_result(request_id, {"resources": resource_definitions()})

        if method == "resources/read":
            return jsonrpc_result(request_id, await read_resource(params.get("uri", ""), manager))

        if method == "prompts/list":
            return jsonrpc_result(request_id, {"prompts": prompt_definitions()})

        if method == "prompts/get":
            return jsonrpc_result(
                request_id,
                get_prompt(params.get("name", ""), params.get("arguments", {}) or {}),
            )

        return jsonrpc_error(request_id, -32601, "Method not found")

    except Exception as exc:
        logger.exception("Error handling request")
        return jsonrpc_error(request_id, -32603, str(exc))
    finally:
        await manager.cleanup()


async def main() -> None:
    """Run describe as an MCP stdio server."""
    async for line in async_stdin():
        try:
            request = json.loads(line)
            response = await handle_request(request)
            if response is not None:
                print(json.dumps(response), flush=True)
        except json.JSONDecodeError as exc:
            response = jsonrpc_error(None, -32700, f"Parse error: {exc}")
            print(json.dumps(response), flush=True)


async def async_stdin():
    """Cross-platform async stdin reader."""
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        yield line.strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="describe",
        description="Discover, install, and configure MCP servers for AI-native workflows.",
    )
    parser.add_argument("--version", action="store_true", help="Show describe version and exit.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("list", help="List available MCP servers.")

    search_parser = subparsers.add_parser("search", help="Search MCP servers.")
    search_parser.add_argument("query")

    install_parser = subparsers.add_parser("install", help="Install or register an MCP server.")
    install_parser.add_argument("name")
    install_parser.add_argument("--method", choices=["npm", "docker", "pypi", "remote"])

    uninstall_parser = subparsers.add_parser("uninstall", help="Remove an installed server.")
    uninstall_parser.add_argument("name")

    subparsers.add_parser("installed", help="List installed servers.")

    config_add_parser = subparsers.add_parser(
        "config-add", help="Add an installed server to MCP config."
    )
    config_add_parser.add_argument("name")

    config_remove_parser = subparsers.add_parser(
        "config-remove", help="Remove a server from MCP config."
    )
    config_remove_parser.add_argument("name")

    subparsers.add_parser("config-list", help="List configured MCP servers.")
    subparsers.add_parser("config-backup", help="Back up MCP configuration.")

    restore_parser = subparsers.add_parser(
        "config-restore", help="Restore MCP configuration backup."
    )
    restore_parser.add_argument("backup")

    subparsers.add_parser("registry-refresh", help="Refresh the MCP Registry cache.")

    return parser


def _print_result(result: Any, as_json: bool) -> None:
    if as_json:
        print(_json_dumps(result))
        return

    if isinstance(result, dict) and "error" in result:
        print(f"Error: {result['error']}")
        return

    if isinstance(result, list):
        for item in result:
            if isinstance(item, dict):
                name = item.get("name")
                if item.get("description"):
                    title = item.get("title") or name
                    print(f"{name}: {title} - {item['description']}")
                elif item.get("type") and item.get("url"):
                    print(f"{name}: {item['type']} {item['url']}")
                elif item.get("command"):
                    print(f"{name}: {item['command']} {' '.join(item.get('args', []))}")
                else:
                    print(_json_dumps(item))
            else:
                print(item)
        return

    if isinstance(result, dict) and "servers" in result:
        _print_result(result["servers"], as_json=False)
        return

    print(_json_dumps(result))


async def cli_main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.debug:
        logger.setLevel(logging.DEBUG)

    if args.version:
        print(f"describe {VERSION}")
        return 0

    if not args.command:
        parser.print_help()
        return 0

    manager = MCPPackageManager()
    try:
        if args.command == "list":
            result = await manager.list_available()
        elif args.command == "search":
            result = await manager.search(args.query)
        elif args.command == "install":
            result = await manager.install(args.name, args.method)
        elif args.command == "uninstall":
            result = await manager.uninstall(args.name)
        elif args.command == "installed":
            result = await manager.list_installed()
        elif args.command == "config-add":
            result = await call_tool("config-add", {"name": args.name}, manager)
        elif args.command == "config-remove":
            result = await call_tool("config-remove", {"name": args.name}, manager)
        elif args.command == "config-list":
            result = await call_tool("config-list", {}, manager)
        elif args.command == "config-backup":
            result = await call_tool("config-backup", {}, manager)
        elif args.command == "config-restore":
            result = await call_tool("config-restore", {"backup": args.backup}, manager)
        elif args.command == "registry-refresh":
            result = await manager.refresh_registry()
        else:
            parser.print_help()
            return 1

        _print_result(result, args.json)
        return 1 if isinstance(result, dict) and "error" in result else 0
    finally:
        await manager.cleanup()


def cli_entrypoint() -> None:
    sys.exit(asyncio.run(cli_main()))


def server_entrypoint() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(asyncio.run(cli_main()))
    asyncio.run(main())
