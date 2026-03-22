#!/usr/bin/env bash
# Podman DevContainer Smoke Test
# This script validates that Podman and Ansible tools are working correctly
set -Eeo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
UNKNOWN_VALUE="unknown"

info() {
    local message="${1:-}"
    echo -e "${BLUE}ℹ️  ${message}${NC}"
    return 0
}

success() {
    local message="${1:-}"
    echo -e "${GREEN}✅ ${message}${NC}"
    return 0
}

warning() {
    local message="${1:-}"
    echo -e "${YELLOW}⚠️  ${message}${NC}"
    return 0
}

error() {
    local message="${1:-}"
    echo -e "${RED}❌ ${message}${NC}"
    return 0
}

WORKSPACE_DIR="${WORKSPACE:-${WORKSPACE_FOLDER:-/workspace}}"
TEMPLATE_ROOT="${DEVCONTAINER_TEMPLATE_ROOT:-/usr/local/share/devcontainer-skel}"

info "Starting Podman DevContainer smoke test..."
echo ""

# ===========================
# 1. Create cache directories
# ===========================
info "Creating cache directories..."
mkdir -p "${WORKSPACE_DIR}/.cache/pre-commit" \
         "${WORKSPACE_DIR}/.cache/ansible/tmp" \
         "${WORKSPACE_DIR}/.cache/podman" || {
    error "Failed to create cache directories"
    exit 1
}
success "Cache directories created"

# ===========================
# 2. Copy execution-environment.yml template if not exists
# ===========================
EE_TEMPLATE="${TEMPLATE_ROOT}/ansible/execution-environment.yml"
EE_TARGET="${WORKSPACE_DIR}/execution-environment.yml"

if [[ -f "${EE_TEMPLATE}" && ! -f "${EE_TARGET}" ]]; then
    info "Copying execution-environment.yml template to workspace..."
    cp "${EE_TEMPLATE}" "${EE_TARGET}"
    success "execution-environment.yml template copied"
elif [[ -f "${EE_TARGET}" ]]; then
    info "execution-environment.yml already exists in workspace"
else
    warning "execution-environment.yml template not found, skipping"
fi

# ===========================
# 3. Pre-commit setup
# ===========================
info "Setting up pre-commit hooks..."
if command -v ensure-precommit &> /dev/null; then
    if ensure-precommit; then
        success "Pre-commit hooks configured"
    else
        warning "ensure-precommit failed, continuing..."
    fi
else
    warning "ensure-precommit not found, skipping"
fi

# ===========================
# 4. Ansible Galaxy collections (idempotent)
# ===========================
if [[ -f "${WORKSPACE_DIR}/requirements.yml" ]]; then
    info "Installing Ansible Galaxy collections from requirements.yml..."
    if ansible-galaxy collection install -r "${WORKSPACE_DIR}/requirements.yml"; then
        success "Ansible collections installed"
    else
        warning "ansible-galaxy collection install failed, continuing..."
    fi
else
    info "No requirements.yml found, skipping collection install"
fi

# ===========================
# 5. Verify cgroups version
# ===========================
info "Checking cgroups version..."
if [[ -f /sys/fs/cgroup/cgroup.controllers ]]; then
    success "cgroups v2 detected (optimal for Podman)"
elif [[ -d /sys/fs/cgroup/cpu ]]; then
    warning "cgroups v1 detected. Podman may have limitations."
    warning "Consider upgrading to a host with cgroups v2 support."
    warning "See: https://github.com/containers/podman/blob/main/docs/tutorials/rootless_tutorial.md"
else
    warning "Unable to detect cgroups version"
fi

# ===========================
# 6. Verify Podman installation
# ===========================
echo ""
info "Verifying Podman installation..."

if ! command -v podman &> /dev/null; then
    error "Podman not found in PATH"
    exit 1
fi

PODMAN_VERSION=$(podman --version 2>/dev/null || echo "${UNKNOWN_VALUE}")
success "Podman found: ${PODMAN_VERSION}"

# ===========================
# 7. Podman info check
# ===========================
info "Running 'podman info' to verify configuration..."

if ! podman info &> /dev/null; then
    error "Podman info failed"
    echo ""
    error "Troubleshooting steps:"
    error "1. Check if cgroups v2 is enabled on host"
    error "2. Verify storage configuration: podman info --debug"
    error "3. Try with --privileged flag in devcontainer.json runArgs"
    exit 1
fi

# Extract useful info
STORAGE_DRIVER=$(podman info --format '{{.Store.GraphDriverName}}' 2>/dev/null || echo "${UNKNOWN_VALUE}")
RUNTIME=$(podman info --format '{{.Host.OCIRuntime.Name}}' 2>/dev/null || echo "${UNKNOWN_VALUE}")

success "Podman info successful"
info "   Storage driver: ${STORAGE_DRIVER}"
info "   OCI Runtime: ${RUNTIME}"

# ===========================
# 8. Test Podman with hello-world
# ===========================
info "Testing Podman with a simple container..."

if podman run --rm quay.io/podman/hello:latest &> /dev/null; then
    success "Podman can run containers successfully"
else
    error "Podman failed to run test container"
    echo ""
    error "This usually indicates:"
    error "1. Storage driver issues (try fuse-overlayfs)"
    error "2. Permission issues with user namespaces"
    error "3. Missing kernel features for rootless Podman"
    echo ""
    error "Run 'podman run --rm quay.io/podman/hello:latest' manually for details"
    exit 1
fi

# ===========================
# 9. Verify ansible-navigator
# ===========================
echo ""
info "Verifying ansible-navigator installation..."

if command -v ansible-navigator &> /dev/null; then
    NAVIGATOR_VERSION=$(ansible-navigator --version 2>/dev/null | head -1 || echo "${UNKNOWN_VALUE}")
    success "ansible-navigator found: ${NAVIGATOR_VERSION}"

    # Pre-pull the default EE image in background to improve first-run UX
    DEFAULT_EE="quay.io/ansible/creator-ee:v0.18.0"
    info "Pre-pulling Execution Environment image (${DEFAULT_EE}) in background..."
    info "This may take a few minutes on first run..."

    (podman pull "${DEFAULT_EE}" &> /tmp/podman-pull.log && \
     success "EE image pulled successfully" || \
     warning "EE image pull failed (check /tmp/podman-pull.log)") &

else
    warning "ansible-navigator not found"
    warning "Install with: uv pip install ansible-navigator"
fi

# ===========================
# 10. Verify ansible-builder
# ===========================
if command -v ansible-builder &> /dev/null; then
    BUILDER_VERSION=$(ansible-builder --version 2>/dev/null || echo "${UNKNOWN_VALUE}")
    success "ansible-builder found: ${BUILDER_VERSION}"
else
    warning "ansible-builder not found"
    warning "Install with: uv pip install ansible-builder"
fi

# ===========================
# Summary
# ===========================
echo ""
echo "============================================"
success "Podman DevContainer smoke test completed!"
echo "============================================"
echo ""
info "Next steps:"
echo "  • Run playbooks with: ansible-navigator run playbook.yml --ee true --ce podman"
echo "  • Build custom EE with: ansible-builder build -f execution-environment.yml -t my-ee:latest"
echo "  • List Podman images: podman images"
echo "  • Use VS Code tasks (Ctrl+Shift+P → 'Tasks: Run Task')"
echo ""
info "For troubleshooting, see: devcontainers/ansible/README.md"
echo ""

exit 0
