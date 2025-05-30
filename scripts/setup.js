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
const { spawn, execSync } = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');

// Check Node.js version compatibility
const nodeVersion = process.version;
const majorVersion = parseInt(nodeVersion.split('.')[0].substring(1));

if (majorVersion < 18) {
    console.error(\`Error: Node.js \${nodeVersion} is not supported. Please use Node.js 18 or higher.\`);
    process.exit(1);
}

const describePath = path.join(__dirname, '..', 'describe.py');

// Find Python - try multiple common locations
function findPython() {
    const pythonCandidates = ['python3', 'python', 'python3.12', 'python3.11', 'python3.10', 'python3.9'];
    
    for (const pythonCmd of pythonCandidates) {
        try {
            const result = execSync(\`\${pythonCmd} --version\`, { encoding: 'utf8', stdio: 'pipe' });
            const version = result.trim();
            if (version.includes('Python 3.')) {
                const majorMinor = version.match(/Python 3\\.(\\d+)/);
                if (majorMinor && parseInt(majorMinor[1]) >= 9) {
                    return pythonCmd;
                }
            }
        } catch (e) {
            // Continue to next candidate
        }
    }
    return null;
}

// Install aiohttp if needed
function ensureAiohttp(pythonCmd) {
    try {
        execSync(\`\${pythonCmd} -c "import aiohttp"\`, { stdio: 'ignore' });
        return true;
    } catch (e) {
        console.error('Installing aiohttp...');
        
        // Try different installation methods
        const installMethods = [
            \`\${pythonCmd} -m pip install --user "aiohttp>=3.9.0"\`,
            \`\${pythonCmd} -m pip install --user --break-system-packages "aiohttp>=3.9.0"\`,
            \`\${pythonCmd} -m pip install "aiohttp>=3.9.0" --break-system-packages\`
        ];
        
        for (const method of installMethods) {
            try {
                execSync(method, { stdio: 'inherit' });
                return true;
            } catch (installError) {
                // Continue to next method
            }
        }
        
        console.error('Failed to install aiohttp automatically.');
        console.error('Please install manually:');
        console.error('  pip3 install --user aiohttp>=3.9.0');
        console.error('  OR: pip3 install --break-system-packages aiohttp>=3.9.0');
        console.error('  OR: pipx install aiohttp>=3.9.0');
        return false;
    }
}

// Main execution
function main() {
    const pythonPath = findPython();
    
    if (!pythonPath) {
        console.error('Error: Python 3.9+ not found. Please install Python 3.9 or higher.');
        process.exit(1);
    }
    
    if (!ensureAiohttp(pythonPath)) {
        process.exit(1);
    }
    
    const child = spawn(pythonPath, [describePath, ...process.argv.slice(2)], {
        stdio: 'inherit',
        env: { ...process.env, PYTHONUNBUFFERED: '1' }
    });

    child.on('exit', (code) => {
        process.exit(code || 0);
    });
    
    child.on('error', (error) => {
        console.error('Failed to start describe:', error.message);
        process.exit(1);
    });
}

main();
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
