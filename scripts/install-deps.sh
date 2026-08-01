#!/usr/bin/env bash
set -euo pipefail

# install-deps.sh
# Installs GUI apps and system packages from packages.json via brew/yay/dnf.
# Portable CLI tools are managed by mise (see mise.toml).
# Normally invoked via `mise run install-apps` or `mise run bootstrap`.
# Usage:
#   ./scripts/install-deps.sh              # bootstrap + all packages
#   ./scripts/install-deps.sh --system     # also install the legacy Arch base package set (Arch only)
#   ./scripts/install-deps.sh --dry-run    # preview package installs without running them
#   ./scripts/install-deps.sh --compliance # run compliance check after package install

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_SYSTEM=false
DRY_RUN=false
RUN_COMPLIANCE=false

for arg in "$@"; do
    case "$arg" in
        --system)      INSTALL_SYSTEM=true ;;
        --dry-run)     DRY_RUN=true ;;
        --compliance)  RUN_COMPLIANCE=true ;;
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

# All install logic keys off the package manager, not the distro name.
# macOS is special-cased: brew may not exist yet (ensure_brew installs it).
# On Linux we pick whichever manager is present -- a clean discriminator
# (a Fedora box has dnf and no pacman, and vice versa).
if [[ "$OS_TYPE" == "macos" ]]; then
    PKG_MGR="brew"
else
    PKG_MGR=""
    for pm in dnf pacman apt-get; do
        command -v "$pm" >/dev/null 2>&1 && { PKG_MGR="$pm"; break; }
    done
fi
log_info "Package manager: ${PKG_MGR:-unknown}"

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
    local temp_dir
    temp_dir=$(mktemp -d)
    trap 'rm -rf "$temp_dir"' RETURN
    git clone --depth 1 https://aur.archlinux.org/yay-bin.git "$temp_dir/yay-bin"
    (cd "$temp_dir/yay-bin" && makepkg -si --noconfirm)
    log_success "yay installed"
}

ensure_fedora_repos() {
    log_info "Enabling COPR support, RPM Fusion, and Flathub..."
    local ver
    ver=$(rpm -E %fedora)
    # dnf-plugins-core provides 'dnf copr'; flatpak is needed before Flathub apps.
    sudo dnf install -y dnf-plugins-core flatpak || log_warn "core plugin/flatpak install failed"
    sudo dnf install -y \
        "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$ver.noarch.rpm" \
        "https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$ver.noarch.rpm" \
        || log_warn "RPM Fusion setup failed (may already be present)"
    flatpak remote-add --if-not-exists flathub \
        https://dl.flathub.org/repo/flathub.flatpakrepo || log_warn "Flathub remote add failed"
    log_success "Fedora repositories ready"
}

install_pkg() {
    local pkg="$1" brew_pkg="${2:-$1}"
    log_info "Installing $pkg..."
    case "$PKG_MGR" in
        brew)   brew install "$brew_pkg" ;;
        pacman) if has_command yay; then yay -S --needed --noconfirm "$pkg"
                else sudo pacman -S --needed --noconfirm "$pkg"; fi ;;
        dnf)    sudo dnf install -y "$pkg" ;;
        apt-get) sudo apt-get update -qq && sudo apt-get install -y -qq "$pkg" ;;
        *)      log_error "No supported package manager"; return 1 ;;
    esac
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
    case "$PKG_MGR" in
        brew)
            brew install 1password-cli ;;
        dnf)
            # 1Password ships its own RPM repo; not in Fedora or COPR.
            sudo rpm --import https://downloads.1password.com/linux/keys/1password.asc || true
            sudo sh -c 'printf "%s\n" \
                "[1password]" \
                "name=1Password Stable Channel" \
                "baseurl=https://downloads.1password.com/linux/rpm/stable/\$basearch" \
                "enabled=1" "gpgcheck=1" "repo_gpgcheck=1" \
                "gpgkey=https://downloads.1password.com/linux/keys/1password.asc" \
                > /etc/yum.repos.d/1password.repo'
            sudo dnf install -y 1password-cli ;;
        pacman)
            yay -S --needed --noconfirm 1password-cli ;;
        *)
            log_warn "Install 1Password CLI manually: https://developer.1password.com/docs/cli/get-started"
            return ;;
    esac
    log_success "1Password CLI installed"
}


install_packages() {
    log_info "Installing packages from packages.json..."
    local dry_run_flag=""
    $DRY_RUN && dry_run_flag="--dry-run"
    # install-packages.py takes macos|arch|fedora, not the generic linux OS_TYPE;
    # omit --platform so its own detection picks arch vs archarm vs fedora correctly.
    if [[ "$OS_TYPE" == "macos" ]]; then
        python3 "$SCRIPT_DIR/install-packages.py" --platform macos $dry_run_flag
    else
        python3 "$SCRIPT_DIR/install-packages.py" $dry_run_flag
    fi
    log_success "Packages installed"
}


install_system_packages() {
    log_info "Installing Arch system packages..."
    local pkgs=(
        acpi alsa-utils android-tools arandr autoconf automake autorandr
        base bison blueman bluez bluez-tools bluez-utils btrfs-progs
        cmake code cpio debugedit dhcpcd dmenu docker docker-compose
        dosfstools efibootmgr fakeroot feh firefox flatpak flameshot flex
        font-manager fuzzel gcc gimp gnome-screenshot gobject-introspection
        grim greetd grub-btrfs gscreenshot hwinfo ipython iwd kitty
        lightdm lightdm-gtk-greeter lightdm-slick-greeter
        lightdm-webkit-theme-litarvan lightdm-webkit2-greeter
        linux linux-firmware m4 make man-db meson mlocate neofetch
        net-tools netstat-nat networkmanager ninja noto-fonts noto-fonts-cjk
        noto-fonts-emoji npm openssh partclone parted patch pavucontrol
        pax-utils pipewire pipewire-alsa pipewire-pulse pkgconf polybar
        power-profiles-daemon pulseaudio pulseaudio-alsa
        python python-pyqt5 python-pyqt5-3d python-pyqt5-chart
        python-pyqt5-datavisualization python-pyqt5-networkauth
        python-pyqt5-purchasing python-pyqt5-webengine
        qutebrowser ranger rofi rsync rxvt-unicode sddm signal-desktop
        slurp sof-firmware sudo sway swaybg swayidle syncthing
        telegram-desktop tlp tor torbrowser-launcher tree ttf-dejavu
        ttf-font-awesome ttf-iosevka-nerd typescript unzip vi vim vlc
        waybar wireplumber wl-clipboard xautolock xclip xf86-video-vesa
        xfce4-screenshooter xorg-bdftopcf xorg-docs xorg-font-util
        xorg-fonts-100dpi xorg-fonts-75dpi xorg-iceauth xorg-mkfontscale
        xorg-server xorg-server-devel xorg-server-xephyr xorg-server-xnest
        xorg-server-xvfb xorg-sessreg xorg-smproxy xorg-x11perf
        xorg-xbacklight xorg-xcmsdb xorg-xcursorgen xorg-xdriinfo xorg-xev
        xorg-xgamma xorg-xhost xorg-xinit xorg-xinput xorg-xkbevd xorg-xkbutils
        xorg-xkill xorg-xlsatoms xorg-xlsclients xorg-xpr xorg-xrefresh
        xorg-xsetroot xorg-xvinfo xorg-xwayland xorg-xwd xorg-xwininfo
        xorg-xwud xterm zsh
    )
    if $DRY_RUN; then
        log_info "(dry-run) would install ${#pkgs[@]} system packages via pacman"
        return
    fi
    sudo pacman -S --needed --noconfirm "${pkgs[@]}"
    log_success "System packages installed"
}

log_info "Checking dotfiles dependencies..."

case "$PKG_MGR" in
    brew)   ensure_brew ;;
    pacman) ensure_yay ;;
    dnf)    ensure_fedora_repos ;;
esac

ensure_git
ensure_stow
ensure_jq
ensure_op

log_info "Fetching SSH keys from 1Password..."
"$SCRIPT_DIR/fetch-ssh-keys.sh" || log_warn "SSH key fetch failed — you may need to run scripts/fetch-ssh-keys.sh manually after signing in to op"

install_packages

if $INSTALL_SYSTEM; then
    if [[ "$PKG_MGR" == "pacman" ]]; then
        install_system_packages
    else
        log_warn "--system installs the legacy Arch base set (pacman only); skipping"
    fi
fi

if $RUN_COMPLIANCE; then
    log_info "Running compliance check..."
    if [[ -x "$SCRIPT_DIR/check-compliance.sh" ]]; then
        "$SCRIPT_DIR/check-compliance.sh" --pre || log_warn "Compliance check found drift. See ~/.config/dotfiles/drift-report.json"
    else
        log_warn "check-compliance.sh not found — sync dotfiles first"
    fi
fi

log_success "Done. Run 'mise run bootstrap' (or ./scripts/sync-dotfiles.sh) to apply dotfiles."
