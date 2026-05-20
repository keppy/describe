# Example: Build A Pull Request Review Stack

This example shows describe in its current shape: not just installing servers,
but giving the AI client a capability map it can inspect before it acts.

## Goal

Review GitHub pull requests with repository context, code search, and a durable
record of what was checked.

## Conversation

### 1. Find The Smallest Stack

```text
Use describe's compose-agent-stack prompt for this goal:
review open GitHub pull requests with local repository context.
```

The client should look for capabilities, not package names:

- GitHub access for pull request metadata and review posting.
- Git access for local diffs and history.
- Filesystem access for scoped repo reads.
- Optional memory for review notes across sessions.

### 2. Search The Registry

```text
Use describe to search for GitHub, git, filesystem, and memory MCP servers.
```

Equivalent CLI:

```bash
describe search github
describe search git
describe search filesystem
describe search memory
```

### 3. Install Only What Is Needed

```text
Install github, git, and filesystem. Skip memory for now.
```

Equivalent CLI:

```bash
describe install github
describe install git
describe install filesystem
```

### 4. Add Config

```text
Add those installed servers to my MCP config and show the backup path.
```

Equivalent CLI:

```bash
describe config-add github
describe config-add git
describe config-add filesystem
describe config-list
```

### 5. Inspect The Capability Map

```text
Read describe://servers/installed before reviewing the PR.
```

The client now has a model-readable resource that tells it what was installed,
which install method was used, and which config it can rely on.

### 6. Harden Before Use

```text
Use describe's harden-mcp-config prompt and check for broad filesystem scope,
missing environment variables, and duplicated servers.
```

The result should be a small risk review before the AI starts calling tools.

## What Changed From The Old Demo

The old describe demo focused on "RAG in seven prompts." That was useful, but
it treated MCP servers like packages. The current design treats them as an
agent capability graph:

- Discovery comes from the Registry, with an offline fallback.
- Tools are annotated for read-only versus state-changing behavior.
- Installed state is exposed as resources.
- Reusable prompts help the client compose and harden stacks.
- Remote servers are registered as endpoints rather than fake local installs.

The workflow is still conversational. It is just less magical and more useful.
