# describe•

Watch me build a complete RAG system in 7 prompts:

```
1. "Find me filesystem and database servers"
2. "Install them"
3. "Create an embedding schema"
4. "Read my documents"
5. "Index them"
6. "Make it searchable"
7. "Give me a terminal interface"
```

**Result**: Working RAG system. No config files. No documentation. Just conversation.

## What Is This?

describe transforms infrastructure from something you configure to something you converse with.

The old way took hours. The new way takes minutes. The difference isn't speed—it's that you never leave the conversation.

## See It In Action

### Build a GitHub PR Analyzer (5 prompts)
```
"Install github and code-analysis servers"
"Connect to my repo"
"Analyze open PRs for complexity"
"Flag potential issues"
"Show me the results"
```

### Create a SQL Chat Interface (4 prompts)
```
"Install sqlite server"
"Connect to my database"
"Let me query it in plain English"
"Show results as tables"
```

### Turn CSVs into an API (6 prompts)
```
"Install filesystem and data servers"
"Read all CSVs from ~/data"
"Create REST endpoints for each"
"Add search functionality"
"Add JSON export"
"Start the server"
```

## Quick Start

```bash
npm install -g @keppylab/describe
```

Add to Claude Desktop config:
```json
{
  "describe": {
    "command": "npx",
    "args": ["-y", "@keppylab/describe"]
  }
}
```

Restart Claude. Start describing.

## The Paradigm Shift

**Before**: Learn tools → Configure tools → Build with tools

**After**: Describe what you want → Get it running → Iterate by talking

This isn't just about saving time. It's about who can build systems:
- A researcher can build a knowledge base
- A designer can create data pipelines  
- A student can build analysis tools

The barrier isn't syntax anymore. It's imagination.

## Examples That Will Break Your Brain

### Self-Modifying Systems
```
Human: My RAG system is too slow
Claude: I see it's scanning all documents on each query. Let me add caching...
*modifies the running system*
Claude: Try now - should be 10x faster
```

### Conversational Debugging
```
Human: Something's wrong with the search
Claude: I see the index is corrupted. Let me rebuild it...
*fixes itself*
Claude: Fixed. Try your search again.
```

### Infrastructure That Explains Itself
```
Human: How does this work?
Claude: Let me show you the data flow...
*generates visualization of the running system*
Claude: Your query goes through these steps...
```

## Installation

**Requirements**: Node.js 18+, Python 3.9+, Claude Desktop/claude code

**Platforms**: macOS, Windows, Linux

**Details**: See [installation guide](docs/install.md)

**CLI Mode**: Power users, see [CLI documentation](docs/cli.md)

## Philosophy

We're not building better tools. We're removing the need to think about tools at all.

Infrastructure should be a conversation, not a configuration.

## Status

**Now**: v1.0 - Full conversational infrastructure  
**Next**: Self-assembling systems, infrastructure that dreams

---

*The best interface is no interface. The best configuration is conversation.*

<a href="https://github.com/keppy/describe">GitHub</a> • 
<a href="https://twitter.com/keppylab_ai">Twitter</a> • 
<a href="https://discord.gg/6rd4M4e4hT">Discord</a>