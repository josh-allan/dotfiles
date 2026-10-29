#!/usr/bin/env bash
set -euo pipefail

HOST_CONFIG="${1:-}"
HOST_PACKAGE="host_M-J7KGT9QHDJ"

if [[ -z "$HOST_CONFIG" || ! -f "$HOST_CONFIG" ]]; then
	echo "Usage: $0 <host_config.json>" >&2
	exit 2
fi

if ! jq -e --arg package "$HOST_PACKAGE" '.packages.public | index($package) != null' \
	"$HOST_CONFIG" >/dev/null; then
	exit 0
fi

if ! command -v herdr >/dev/null 2>&1; then
	echo "WARNING: herdr not found on PATH; skipping host plugin setup" >&2
	exit 0
fi

if ! command -v uv >/dev/null 2>&1; then
	echo "WARNING: uv not found on PATH; skipping host plugin setup" >&2
	exit 0
fi

HERDR_ROOT="$HOME/.local/share/herdr-host"
TOOLS_PROJECT="$HERDR_ROOT/tools"
PLUGIN_ROOT="$HERDR_ROOT/plugins"
REVIEWR_CONFIG_SOURCE="$HERDR_ROOT/reviewr/config.toml"
HERDR_HOST_CONFIG="$HOME/.config/herdr-host-M-J7KGT9QHDJ/config.toml"

if [[ ! -f "$TOOLS_PROJECT/pyproject.toml" || ! -d "$PLUGIN_ROOT" ]]; then
	echo "ERROR: host Herdr package is not stowed under $HERDR_ROOT" >&2
	exit 1
fi

if [[ ! -f "$HERDR_HOST_CONFIG" ]]; then
	echo "ERROR: host Herdr config is missing: $HERDR_HOST_CONFIG" >&2
	exit 1
fi

export HERDR_CONFIG_PATH="$HERDR_HOST_CONFIG"

echo "Installing host herdr-tools..."
uv tool install --editable --reinstall "$TOOLS_PROJECT"

for plugin in close-confirm focus-watch lazygit pane-history pane-label space-label; do
	echo "Linking Herdr plugin: $plugin"
	herdr plugin link "$PLUGIN_ROOT/$plugin"
done

echo "Linking Reviewr's host config..."
reviewr_config_dir="$(herdr plugin config-dir persiyanov.reviewr)"
if [[ -z "$reviewr_config_dir" ]]; then
	echo "ERROR: herdr returned an empty Reviewr config directory" >&2
	exit 1
fi

reviewr_config="$reviewr_config_dir/config.toml"
if [[ -L "$reviewr_config" ]]; then
	if [[ "$(readlink "$reviewr_config")" == "$REVIEWR_CONFIG_SOURCE" ]]; then
		exit 0
	fi
	echo "WARNING: preserving existing Reviewr config symlink at $reviewr_config" >&2
	exit 0
fi

if [[ -e "$reviewr_config" ]]; then
	echo "WARNING: preserving existing Reviewr config at $reviewr_config" >&2
	exit 0
fi

ln -s "$REVIEWR_CONFIG_SOURCE" "$reviewr_config"
