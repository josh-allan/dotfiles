#!/usr/bin/env bash
# Test for placeholder regex metacharacter escaping in render-templates.sh
set -euo pipefail

TEST_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$TEST_DIR/../scripts/render-templates.sh"

# Create temp workspace
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

mkdir -p "$WORKDIR/templates" "$WORKDIR/output"

# Mock 'op' CLI
cat > "$WORKDIR/op" <<'OPEOF'
#!/usr/bin/env bash
# mock op: just output the reference as the value
echo "value-of-$1"
OPEOF
chmod +x "$WORKDIR/op"

# Create host config with placeholders containing regex metacharacters
cat > "$WORKDIR/config.json" <<'EOF'
{
  "templates": {
    "testfile": {
      "user.email": "op://vault/item/user.email",
      "path.to": "op://vault/item/path.to",
      "user+email": "op://vault/item/user+email",
      "user(email)": "op://vault/item/user(email)",
      "user[email]": "op://vault/item/user[email]",
      "user*email": "op://vault/item/user*email"
    }
  }
}
EOF

# Create template file containing BOTH each placeholder AND a lookalike
# to verify regex metacharacters are escaped (not interpreted as regex)
cat > "$WORKDIR/templates/testfile.tmpl" <<'EOF'
email={{user.email}}
fake={{userXemail}}
path={{path.to}}
dotpath={{pathXto}}
plus={{user+email}}
plusfake={{user-email}}
paren={{user(email)}}
parenfake={{userXemailX}}
bracket={{user[email]}}
bracketfake={{userXemailX}}
star={{user*email}}
starfake={{user-email}}
EOF

# Run the script
export PATH="$WORKDIR:$PATH"
bash "$SCRIPT" "$WORKDIR/config.json" "$WORKDIR/templates" "$WORKDIR/output"

echo ""
echo "=== ACTUAL OUTPUT ==="
cat "$WORKDIR/output/testfile"
echo ""
echo "=== TESTS ==="

output="$(cat "$WORKDIR/output/testfile")"

# Test 1: user.email was properly replaced
if echo "$output" | grep -q 'email=value-of-'; then
    echo "PASS: user.email was replaced"
else
    echo "FAIL: user.email was NOT replaced"
    exit 1
fi

# Test 2: userXemail was NOT replaced (the '.' metacharacter bug)
if echo "$output" | grep -q 'fake={{userXemail}}'; then
    echo "PASS: userXemail was NOT incorrectly matched by '.'"
else
    echo "FAIL: userXemail was INCORRECTLY matched by user.email regex"
    echo "  Expected: fake={{userXemail}}"
    echo "  Got:      $(echo "$output" | grep 'fake=')"
    exit 1
fi

# Test 3: path.to was properly replaced
if echo "$output" | grep -q 'path=value-of-'; then
    echo "PASS: path.to was replaced"
else
    echo "FAIL: path.to was NOT replaced"
    exit 1
fi

# Test 4: pathXto was NOT replaced (the '.' metacharacter bug)
if echo "$output" | grep -q 'dotpath={{pathXto}}'; then
    echo "PASS: pathXto was NOT incorrectly matched by '.'"
else
    echo "FAIL: pathXto was INCORRECTLY matched by path.to regex"
    exit 1
fi

# Test 5: user+email was properly replaced
if echo "$output" | grep -q 'plus=value-of-'; then
    echo "PASS: user+email was replaced"
else
    echo "FAIL: user+email was NOT replaced"
    exit 1
fi

# Test 6: user-email was NOT matched by user+email ('+' metacharacter)
if echo "$output" | grep -q 'plusfake={{user-email}}'; then
    echo "PASS: user-email was NOT incorrectly matched by '+'"
else
    echo "FAIL: user-email was INCORRECTLY matched by user+email regex"
    exit 1
fi

# Test 7: user(email) was properly replaced
if echo "$output" | grep -q 'paren=value-of-'; then
    echo "PASS: user(email) was replaced"
else
    echo "FAIL: user(email) was NOT replaced"
    exit 1
fi

# Test 8: userXemailX was NOT matched by user(email) ('()' metacharacters)
if echo "$output" | grep -q 'parenfake={{userXemailX}}'; then
    echo "PASS: userXemailX was NOT incorrectly matched by '()'"
else
    echo "FAIL: userXemailX was INCORRECTLY matched by user(email) regex"
    exit 1
fi

# Test 9: user[email] was properly replaced
if echo "$output" | grep -q 'bracket=value-of-'; then
    echo "PASS: user[email] was replaced"
else
    echo "FAIL: user[email] was NOT replaced"
    exit 1
fi

# Test 10: userXemailX was NOT matched by user[email] ('[]' metacharacters)
if echo "$output" | grep -q 'bracketfake={{userXemailX}}'; then
    echo "PASS: userXemailX was NOT incorrectly matched by '[]'"
else
    echo "FAIL: userXemailX was INCORRECTLY matched by user[email] regex"
    exit 1
fi

# Test 11: user*email was properly replaced
if echo "$output" | grep -q 'star=value-of-'; then
    echo "PASS: user*email was replaced"
else
    echo "FAIL: user*email was NOT replaced"
    exit 1
fi

# Test 12: user-email was NOT matched by user*email ('*' metacharacter)
if echo "$output" | grep -q 'starfake={{user-email}}'; then
    echo "PASS: user-email was NOT incorrectly matched by '*'"
else
    echo "FAIL: user-email was INCORRECTLY matched by user*email regex"
    exit 1
fi

echo ""
echo "=== ALL TESTS PASSED ==="
