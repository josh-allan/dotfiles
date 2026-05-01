#!/usr/bin/env bash
set -euo pipefail

# render-templates.sh
# Renders template files by replacing {{key}} placeholders with values from 1Password CLI.
# Usage: render-templates.sh <host_config.json> <templates_dir> <output_dir>

HOST_CONFIG="${1:-}"
TEMPLATES_DIR="${2:-}"
OUTPUT_DIR="${3:-}"

if [[ -z "$HOST_CONFIG" || -z "$TEMPLATES_DIR" || -z "$OUTPUT_DIR" ]]; then
    echo "Usage: $0 <host_config.json> <templates_dir> <output_dir>"
    exit 1
fi

if ! command -v op >/dev/null 2>&1; then
    echo "ERROR: 1Password CLI (op) not found. Install it or skip templates."
    exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "ERROR: jq not found. Install it: brew install jq"
    exit 1
fi

# Pre-validate JSON before using jq
if ! jq -e '.' "$HOST_CONFIG" >/dev/null 2>&1; then
    echo "ERROR: Invalid JSON in $HOST_CONFIG"
    exit 1
fi

# Read templates config (while read for Bash 3+ compat)
found_templates=false
while IFS= read -r template_key; do
    [[ -n "$template_key" ]] || continue
    found_templates=true

    template_file="$TEMPLATES_DIR/$template_key.tmpl"
    output_file="$OUTPUT_DIR/$template_key"

    if [[ ! -f "$template_file" ]]; then
        echo "WARNING: Template not found: $template_file"
        continue
    fi

    mkdir -p "$(dirname "$output_file")"

    # Start with template content
    cp "$template_file" "$output_file"

    # Read placeholder mappings for this template (while read for Bash 3+ compat)
    while IFS= read -r placeholder; do
        [[ -n "$placeholder" ]] || continue

        op_ref="$(jq -r ".templates[\"$template_key\"][\"$placeholder\"]" "$HOST_CONFIG")"

        # Fetch value from 1Password
        value="$(op read "$op_ref" 2>/dev/null || true)"

        if [[ -z "$value" ]]; then
            echo "WARNING: Could not read 1Password reference for '$placeholder' in '$template_key'"
            continue
        fi

        # Replace placeholder in output file using perl (safe for special chars)
        export OP_VALUE="$value"
        perl -i -pe "s/\{\{\Q$placeholder\E\}\}/\$ENV{OP_VALUE}/g" -- "$output_file"
        unset OP_VALUE
        echo "  $template_key: {{$placeholder}} -> [redacted]"
    done < <(jq -r ".templates[\"$template_key\"] | keys[]" "$HOST_CONFIG" 2>/dev/null || true)
done < <(jq -r '.templates | keys[]' "$HOST_CONFIG" 2>/dev/null || true)

if ! $found_templates; then
    echo "No templates configured."
    exit 0
fi

echo "Templates rendered."
