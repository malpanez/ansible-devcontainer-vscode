#!/bin/bash
# fix-dockerfiles.sh

for dockerfile in devcontainers/*/Dockerfile; do
  echo "Fixing $dockerfile"

  # Add ARG statements after FROM if not present
  if ! grep -q "ARG TARGETARCH" "$dockerfile"; then
    sed -i '/^FROM /a\
\
# BuildKit platform arguments\
ARG TARGETPLATFORM\
ARG TARGETARCH\
ARG TARGETOS' "$dockerfile"
  fi

  # Fix apt cache mounts
  sed -i 's|--mount=type=cache,target=/var/lib/apt/lists|--mount=type=cache,target=/var/lib/apt/lists,id=apt-lists-${TARGETARCH},sharing=locked|g' "$dockerfile"
  sed -i 's|--mount=type=cache,target=/var/cache/apt|--mount=type=cache,target=/var/cache/apt,id=apt-cache-${TARGETARCH},sharing=locked|g' "$dockerfile"

  # Fix pip cache mounts if present
  sed -i 's|--mount=type=cache,target=/root/.cache/pip|--mount=type=cache,target=/root/.cache/pip,id=pip-${TARGETARCH},sharing=locked|g' "$dockerfile"

  echo "✓ Fixed $dockerfile"
done

echo "All Dockerfiles fixed!"
