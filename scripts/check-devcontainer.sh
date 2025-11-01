#!/bin/bash
# fix-all-dockerfiles.sh

for dockerfile in devcontainers/*/Dockerfile; do
  echo "Fixing $dockerfile..."

  # Add ARG statements after FROM if not present
  if ! grep -q "ARG TARGETARCH" "$dockerfile"; then
    sed -i '/^FROM /a\
\
# BuildKit platform arguments\
ARG TARGETPLATFORM\
ARG TARGETARCH\
ARG TARGETOS' "$dockerfile"
  fi

  # Fix apt cache mounts - add id and sharing parameters if missing
  if grep -q -- '--mount=type=cache,target=/var/lib/apt/lists' "$dockerfile" && \
     ! grep -q 'id=apt-lists-${TARGETARCH}' "$dockerfile"; then
    sed -i 's|--mount=type=cache,target=/var/lib/apt/lists\b|--mount=type=cache,target=/var/lib/apt/lists,id=apt-lists-${TARGETARCH},sharing=locked|g' "$dockerfile"
  fi

  if grep -q -- '--mount=type=cache,target=/var/cache/apt' "$dockerfile" && \
     ! grep -q 'id=apt-cache-${TARGETARCH}' "$dockerfile"; then
    sed -i 's|--mount=type=cache,target=/var/cache/apt\b|--mount=type=cache,target=/var/cache/apt,id=apt-cache-${TARGETARCH},sharing=locked|g' "$dockerfile"
  fi

  # Fix pip cache if present
  if grep -q -- '--mount=type=cache,target=/root/.cache/pip' "$dockerfile" && \
     ! grep -q 'id=pip-${TARGETARCH}' "$dockerfile"; then
    sed -i 's|--mount=type=cache,target=/root/.cache/pip\b|--mount=type=cache,target=/root/.cache/pip,id=pip-${TARGETARCH},sharing=locked|g' "$dockerfile"
  fi

  echo "✅ Fixed $dockerfile"
done

echo ""
echo "All Dockerfiles fixed! Now you can enable multi-arch builds."
