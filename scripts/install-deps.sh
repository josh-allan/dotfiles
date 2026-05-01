#!/usr/bin/env bash
set -euo pipefail

# install-deps.sh
# Platform-agnostic dependency installer for dotfiles sync.
# Ensures stow, jq, git, and 1Password CLI are available.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output (disabled if not terminal)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

if [[ ! -t 1 ]]; then
    RED='' GREEN='' YELLOW='' BLUE='' NC=''
fi

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect OS
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
case "$OS" in
    linux*)
        OS_TYPE="linux"
        ;;
    darwin*)
        OS_TYPE="macos"
        ;;
    *)
        log_error "Unsupported OS: $OS"
        exit 1
        ;;
esac

log_info "Detected OS: $OS_TYPE"

# Check if a command exists
has_command() {
    command -v "$1" >/dev/null 2>&1
}

# Install using package manager
install_pkg() {
    local pkg="$1"
    local brew_pkg="${2:-$pkg}"
    
    log_info "Installing $pkg..."
    
    if [[ "$OS_TYPE" == "macos" ]]; then
        if has_command brew; then
            brew install "$brew_pkg"
        else
            log_error "Homebrew not found. Install from https://brew.sh"
            return 1
        fi
    else
        # Linux - detect package manager
        if has_command apt-get; then
            sudo apt-get update -qq && sudo apt-get install -y -qq "$pkg"
        elif has_command pacman; then
            sudo pacman -Sy --noconfirm "$pkg"
        elif has_command dnf; then
            sudo dnf install -y "$pkg"
        elif has_command yum; then
            sudo yum install -y "$pkg"
        elif has_command zypper; then
            sudo zypper install -y "$pkg"
        else
            log_error "No supported package manager found (apt, pacman, dnf, yum, zypper)"
            return 1
        fi
    fi
}

# Check and install git
ensure_git() {
    if has_command git; then
        log_success "git: $(git --version | cut -d' ' -f3)"
    else
        install_pkg git
        log_success "git installed"
    fi
}

# Check and install stow
ensure_stow() {
    if has_command stow; then
        log_success "stow: $(stow --version | awk '{print $4}')"
    else
        install_pkg stow
        log_success "stow installed"
    fi
}

# Check and install jq
ensure_jq() {
    if has_command jq; then
        log_success "jq: $(jq --version)"
    else
        install_pkg jq
        log_success "jq installed"
    fi
}

# Check and install 1Password CLI
ensure_op() {
    if has_command op; then
        log_success "1Password CLI: $(op --version)"
        return 0
    fi
    
    log_info "Installing 1Password CLI..."
    
    if [[ "$OS_TYPE" == "macos" ]]; then
        if has_command brew; then
            brew install 1password-cli
        else
            log_error "Homebrew not found. Install 1Password CLI manually:"
            log_error "  https://developer.1password.com/docs/cli/get-started"
            return 1
        fi
    else
        # Linux - use official install script
        log_info "Downloading 1Password CLI..."
        local arch
        arch="$(uname -m)"
        case "$arch" in
            x86_64)
                arch="amd64"
                ;;
            aarch64|arm64)
                arch="arm64"
                ;;
        esac
        
        local tmp_dir
        tmp_dir="$(mktemp -d)"
        trap 'rm -rf "$tmp_dir"' EXIT
        
        curl -sS https://cache.agilebits.com/dist/1P/op2/pkg/stable/op_linux_${arch}_v2.34.0.zip -o "$tmp_dir/op.zip" 2>/dev/null || {
            log_error "Failed to download 1Password CLI"
            log_error "Install manually: https://developer.1password.com/docs/cli/get-started"
            return 1
        }
        
        unzip -q "$tmp_dir/op.zip" -d "$tmp_dir"
        sudo mv "$tmp_dir/op" /usr/local/bin/
        sudo chmod +x /usr/local/bin/op
        
        log_success "1Password CLI installed"
    fi
}

# Main
log_info "Checking dotfiles sync dependencies..."

ensure_git
ensure_stow
ensure_jq
ensure_op

log_info ""
log_success "All dependencies satisfied. Run ./scripts/sync-dotfiles.sh to sync dotfiles."
