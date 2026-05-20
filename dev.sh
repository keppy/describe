#!/bin/bash
# Development setup script for describe
# Copyright 2024 James Dominguez
# Licensed under the Apache License, Version 2.0

set -e

echo "Setting up describe development environment..."

if ! command -v python3 > /dev/null 2>&1; then
    echo "Python 3 is required but was not found"
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Creating development virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "Installing development dependencies..."
if command -v uv > /dev/null 2>&1; then
    echo "Using uv"
    uv pip install -e ".[dev]"
else
    echo "Using pip"
    pip install --upgrade pip
    pip install -e ".[dev]"
fi

echo "Development environment ready."
echo ""
echo "To activate the environment:"
echo "  source .venv/bin/activate"
echo ""
echo "To run tests:"
echo "  pytest"
echo ""
echo "To run the MCP server:"
echo "  python describe.py"
