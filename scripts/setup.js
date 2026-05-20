// Copyright 2024 James Dominguez
// Licensed under the Apache License, Version 2.0

const { execFileSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

console.log('Setting up describe - AI-native MCP capability manager...');

function pythonCandidates() {
  const candidates = [];
  if (process.env.PYTHON) {
    candidates.push({ command: process.env.PYTHON, args: [] });
  }
  candidates.push(
    { command: 'python3', args: [] },
    { command: 'python', args: [] },
    { command: 'python3.13', args: [] },
    { command: 'python3.12', args: [] },
    { command: 'python3.11', args: [] },
    { command: 'python3.10', args: [] },
    { command: 'python3.9', args: [] },
    { command: 'py', args: ['-3'] }
  );
  return candidates;
}

function findPython() {
  for (const candidate of pythonCandidates()) {
    try {
      const output = execFileSync(candidate.command, [...candidate.args, '--version'], {
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'pipe']
      }).trim();
      const match = output.match(/Python 3\.(\d+)/);
      if (match && Number.parseInt(match[1], 10) >= 9) {
        return { ...candidate, version: output };
      }
    } catch (_error) {
      // Try the next candidate.
    }
  }
  return null;
}

const python = findPython();
if (!python) {
  console.error('Python 3.9+ is required but was not found in PATH.');
  process.exit(1);
}
console.log(`Found ${python.version}`);

const describeHome = path.join(os.homedir(), '.describe');
fs.mkdirSync(describeHome, { recursive: true });
console.log(`Using describe home at ${describeHome}`);

const binPath = path.join(__dirname, '..', 'bin', 'describe');
if (process.platform !== 'win32' && fs.existsSync(binPath)) {
  fs.chmodSync(binPath, 0o755);
}

console.log('describe setup complete.');
console.log('Add this MCP server to your client:');
console.log(JSON.stringify({
  describe: {
    command: 'npx',
    args: ['-y', '@keppylab/describe']
  }
}, null, 2));
