#!/usr/bin/env bash
set -euo pipefail
VERSION="$1"
ARCH="$2"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
curl -fsSL "https://github.com/FiloSottile/age/releases/download/v${VERSION}/age-v${VERSION}-linux-${ARCH}.tar.gz" -o "$TMP/age.tar.gz"
tar -xzf "$TMP/age.tar.gz" -C "$TMP"
AGE_BIN="$(find "$TMP" -type f -name age -perm -u+x | head -n1 || true)"
AGE_KEYGEN="$(find "$TMP" -type f -name age-keygen -perm -u+x | head -n1 || true)"
if [ -z "$AGE_BIN" ] || [ -z "$AGE_KEYGEN" ]; then
  echo "Unable to locate age binaries" >&2
  exit 1
fi
install -m 0755 "$AGE_BIN" /tmp/bin/age
install -m 0755 "$AGE_KEYGEN" /tmp/bin/age-keygen
