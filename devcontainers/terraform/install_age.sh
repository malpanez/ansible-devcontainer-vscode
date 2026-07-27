#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:?Usage: install_age.sh <version> <arch> [sha256]}"
ARCH="${2:?Usage: install_age.sh <version> <arch> [sha256]}"
EXPECTED_SHA256="${3:-}"

# Validate inputs
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  printf 'Invalid version format: %s (expected X.Y.Z)\n' "$VERSION" >&2
  exit 1
fi
case "$ARCH" in
  amd64 | arm64) ;;
  *)
    printf 'Invalid arch: %s (expected amd64 or arm64)\n' "$ARCH" >&2
    exit 1
    ;;
esac

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

curl --proto '=https' --tlsv1.2 -fsSL \
  "https://github.com/FiloSottile/age/releases/download/v${VERSION}/age-v${VERSION}-linux-${ARCH}.tar.gz" \
  -o "$TMP/age.tar.gz"

# age publishes no checksum files, so callers pin the expected hash
if [[ -n "$EXPECTED_SHA256" ]]; then
  printf '%s  %s\n' "$EXPECTED_SHA256" "$TMP/age.tar.gz" | sha256sum -c -
else
  printf 'WARNING: no sha256 provided for age archive; skipping verification\n' >&2
fi

tar -xzf "$TMP/age.tar.gz" -C "$TMP"

AGE_BIN="$(find "$TMP" -type f -name age -perm -u+x | head -n1 || true)"
AGE_KEYGEN="$(find "$TMP" -type f -name age-keygen -perm -u+x | head -n1 || true)"

if [[ -z "$AGE_BIN" ]] || [[ -z "$AGE_KEYGEN" ]]; then
  printf 'Unable to locate age binaries in extracted archive\n' >&2
  exit 1
fi

install -m 0755 "$AGE_BIN" /tmp/bin/age
install -m 0755 "$AGE_KEYGEN" /tmp/bin/age-keygen
printf 'age %s (%s) installed successfully\n' "$VERSION" "$ARCH"
