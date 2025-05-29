// Copyright 2024 James Dominguez
// Licensed under the Apache License, Version 2.0

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

console.log('🚀 Setting up describe - The MCP Package Manager...');

// Check for Python
try {
    const pythonVersion = execSync('python3 --version', { encoding: 'utf8' });
    console.log(`✓ Found ${pythonVersion.trim()}`);
} catch (e) {
    console.error('❌ Python 3 is required but not found in PATH');
    process.exit(1);
}

// Create .describe directory and venv
const describeHome = path.join(os.homedir(), '.describe');
const venvPath = path.join(describeHome, 'venv');

if (!fs.existsSync(describeHome)) {
    fs.mkdirSync(describeHome, { recursive: true });
    console.log(`✓ Created describe home directory at ${describeHome}`);
}

// Create virtual environment
console.log('📦 Creating virtual environment...');
try {
    execSync(`python3 -m venv ${venvPath}`, { stdio: 'inherit' });
    console.log('✓ Virtual environment created');
} catch (e) {
    console.error('❌ Failed to create virtual environment');
    process.exit(1);
}

// Determine pip path based on platform
const pipPath = process.platform === 'win32'
    ? path.join(venvPath, 'Scripts', 'pip.exe')
    : path.join(venvPath, 'bin', 'pip');

// Install dependencies into venv
console.log('📥 Installing dependencies...');
try {
    // Check for uv first
    execSync('uv --version', { encoding: 'utf8', stdio: 'ignore' });
    console.log('✓ Found uv - Installing with uv...');
    execSync(`uv pip install --python ${venvPath} aiohttp>=3.9.0`, { stdio: 'inherit' });
} catch (e) {
    // Fallback to regular pip
    console.log('⚡ Using pip to install dependencies...');
    try {
        execSync(`${pipPath} install --upgrade pip`, { stdio: 'inherit' });
        execSync(`${pipPath} install aiohttp>=3.9.0`, { stdio: 'inherit' });
        console.log('✓ Dependencies installed');
    } catch (pipError) {
        console.error('❌ Failed to install dependencies:', pipError.message);
        process.exit(1);
    }
}

// Create bin wrapper
const binDir = path.join(__dirname, '..', 'bin');
if (!fs.existsSync(binDir)) {
    fs.mkdirSync(binDir);
}

const binScript = `#!/usr/bin/env node
const { spawn } = require('child_process');
const path = require('path');
const os = require('os');

const describePath = path.join(__dirname, '..', 'describe.py');
const venvPath = path.join(os.homedir(), '.describe', 'venv');

// Use Python from venv
let pythonPath;
if (process.platform === 'win32') {
    pythonPath = path.join(venvPath, 'Scripts', 'python.exe');
} else {
    pythonPath = path.join(venvPath, 'bin', 'python');
}

// Fallback to system Python if venv doesn't exist
const fs = require('fs');
if (!fs.existsSync(pythonPath)) {
    console.error('describe virtual environment not found. Running setup...');
    // Re-run setup
    const setupPath = path.join(__dirname, '..', 'scripts', 'setup.js');
    require(setupPath);
    process.exit(1);
}

const child = spawn(pythonPath, [describePath, ...process.argv.slice(2)], {
    stdio: 'inherit',
    env: { ...process.env, PYTHONUNBUFFERED: '1' }
});

child.on('exit', (code) => {
    process.exit(code || 0);
});
`;

const binPath = path.join(binDir, 'describe');
fs.writeFileSync(binPath, binScript);
if (process.platform !== 'win32') {
    fs.chmodSync(binPath, '755');
}

console.log('\n✨ describe setup complete!');
console.log('💡 You can now use describe as an MCP server');
console.log('\n📝 Add to your MCP settings:');
console.log(JSON.stringify({
    "describe": {
        "command": "npx",
        "args": ["-y", "@keppylab/describe"]
    }
}, null, 2));
