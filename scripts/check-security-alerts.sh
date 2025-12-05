#!/usr/bin/env bash
# Check for security vulnerabilities in Python dependencies
set -euo pipefail

echo "=== Security Vulnerability Check ==="
echo ""

# Check if pip-audit is available
if ! command -v pip-audit &> /dev/null; then
    echo "Installing pip-audit..."
    uvx pip-audit --help &> /dev/null || uv tool install pip-audit
fi

echo "Scanning Python dependencies for known vulnerabilities..."
echo ""

# Run pip-audit on requirements.txt
if [ -f "requirements.txt" ]; then
    echo "📦 Scanning requirements.txt..."
    uvx pip-audit -r requirements.txt --format json > /tmp/pip-audit-results.json 2>&1 || true

    # Display results
    if [ -f "/tmp/pip-audit-results.json" ]; then
        uvx pip-audit -r requirements.txt --format markdown || true
    fi
fi

echo ""
echo "=== Trivy Scan ==="
if command -v trivy &> /dev/null; then
    trivy fs --severity HIGH,CRITICAL . || true
else
    echo "Trivy not installed. Skipping..."
fi

echo ""
echo "=== Safety Check ==="
if [ -f "requirements.txt" ]; then
    uvx safety check -r requirements.txt || true
fi

echo ""
echo "✅ Security scan complete"
