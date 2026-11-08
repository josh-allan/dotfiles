# rex_bin prints the rex CLI to run, or fails when Rex is not installed. Inside a Rex
# terminal REX_BIN_DIR names it; elsewhere it comes from PATH or the macOS app bundle.
rex_bin() {
	if [[ -n "${REX_BIN_DIR:-}" && -x "$REX_BIN_DIR/rex" ]]; then
		printf '%s\n' "$REX_BIN_DIR/rex"
		return 0
	fi
	if command -v rex >/dev/null 2>&1; then
		command -v rex
		return 0
	fi
	local app bin
	for app in /Applications/Rex*.app; do
		bin="$app/Contents/Helpers/Rex Server.rex/Contents/MacOS/rex"
		if [[ -x "$bin" ]]; then
			printf '%s\n' "$bin"
			return 0
		fi
	done
	return 1
}
