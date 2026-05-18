#!/usr/bin/env bash
set -euo pipefail

# install-deps.sh
# Bootstraps dotfiles dependencies, then installs all packages from packages.json.
# Usage:
#   ./scripts/install-deps.sh              # bootstrap + all packages
#   ./scripts/install-deps.sh --system     # also install Arch system packages (Arch only)
#   ./scripts/install-deps.sh --dry-run    # preview package installs without running them

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_SYSTEM=false
DRY_RUN=false

for arg in "$@"; do
    case "$arg" in
        --system)  INSTALL_SYSTEM=true ;;
        --dry-run) DRY_RUN=true ;;
    esac
done

RED='\033[0;31m' GREEN='\033[0;32m' YELLOW='\033[1;33m' BLUE='\033[0;34m' NC='\033[0m'
if [[ ! -t 1 ]]; then RED='' GREEN='' YELLOW='' BLUE='' NC=''; fi

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
case "$OS" in
    linux*)  OS_TYPE="linux" ;;
    darwin*) OS_TYPE="macos" ;;
    *)       log_error "Unsupported OS: $OS"; exit 1 ;;
esac
log_info "Detected OS: $OS_TYPE"

has_command() { command -v "$1" >/dev/null 2>&1; }

ensure_brew() {
    if has_command brew; then
        log_success "brew: $(brew --version | head -1)"
        return
    fi
    log_info "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Add to PATH for current session
    if [[ -f /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -f /usr/local/bin/brew ]]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    log_success "Homebrew installed"
}


ensure_yay() {
    if has_command yay; then
        log_success "yay: $(yay --version | head -1)"
        return
    fi
    log_info "Installing yay (AUR helper)..."
    local tmp
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' RETURN
    git clone --depth 1 https://aur.archlinux.org/yay-bin.git "$tmp/yay-bin"
    (cd "$tmp/yay-bin" && makepkg -si --noconfirm)
    log_success "yay installed"
}

install_pkg() {
    local pkg="$1" brew_pkg="${2:-$1}"
    log_info "Installing $pkg..."
    if [[ "$OS_TYPE" == "macos" ]]; then
        brew install "$brew_pkg"
    elif has_command yay; then
        yay -S --needed --noconfirm "$pkg"
    elif has_command pacman; then
        sudo pacman -S --needed --noconfirm "$pkg"
    elif has_command apt-get; then
        sudo apt-get update -qq && sudo apt-get install -y -qq "$pkg"
    else
        log_error "No supported package manager"; return 1
    fi
}

ensure_git() {
    if has_command git; then
        log_success "git: $(git --version | cut -d' ' -f3)"
    else
        install_pkg git && log_success "git installed"
    fi
}

ensure_stow() {
    if has_command stow; then
        log_success "stow: $(stow --version | awk '{print $4}')"
    else
        install_pkg stow && log_success "stow installed"
    fi
}

ensure_jq() {
    if has_command jq; then
        log_success "jq: $(jq --version)"
    else
        install_pkg jq && log_success "jq installed"
    fi
}

ensure_op() {
    if has_command op; then
        log_success "1Password CLI: $(op --version)"
        return
    fi
    log_info "Installing 1Password CLI..."
    if [[ "$OS_TYPE" == "macos" ]]; then
        brew install 1password-cli
    elif has_command yay; then
        yay -S --needed --noconfirm 1password-cli
    else
        log_warn "Install 1Password CLI manually: https://developer.1password.com/docs/cli/get-started"
        return
    fi
    log_success "1Password CLI installed"
}


install_packages() {
    log_info "Installing packages from packages.json..."
    local dry_run_flag=""
    $DRY_RUN && dry_run_flag="--dry-run"
    python3 "$SCRIPT_DIR/install-packages.py" --platform "$OS_TYPE" $dry_run_flag
    log_success "Packages installed"
}


install_system_packages() {
    local lst="$SCRIPT_DIR/pacman-system.lst"
    if [[ ! -f "$lst" ]]; then
        log_warn "pacman-system.lst not found at $lst"
        return
    fi
    log_info "Installing Arch system packages from pacman-system.lst..."
    if $DRY_RUN; then
        log_info "(dry-run) would run: sudo pacman -S --needed --noconfirm < $lst"
        return
    fi
    sudo pacman -S --needed --noconfirm - < "$lst"
    log_success "System packages installed"
}

log_info "Checking dotfiles dependencies..."

if [[ "$OS_TYPE" == "macos" ]]; then
    ensure_brew
fi

if [[ "$OS_TYPE" == "linux" ]]; then
    ensure_yay
fi

ensure_git
ensure_stow
ensure_jq
ensure_op

install_packages

if $INSTALL_SYSTEM && [[ "$OS_TYPE" == "linux" ]]; then
    install_system_packages
fi

log_success "Done. Run ./scripts/sync-dotfiles.sh to apply dotfiles."
