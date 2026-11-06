#!/usr/bin/env bash
# What ci.yml builds and checks for one image: its Dockerfile and stage, its
# structure tests, and which Dev Containers checks apply to it.
#
# Every image is devcontainers/<image>/Dockerfile tested with <image>.yaml,
# except the variants, which are a stack plus one layer: ansible-podman, built
# from Dockerfile.podman, and the -aws images, built from the stack's
# Dockerfile with --target <image>. The stack's file holds for them unchanged
# (user, workdir, tools, the bytecode check), so they run it and
# <variant>.yaml for the layer, instead of a copy. terraform and ansible, built
# without a target (their Dockerfile's last stage), also run no-aws.yaml: it
# fails if that last stage ever became an -aws image.
#
# base_from_run marks the images whose Dockerfile consumes BASE_IMAGE: only
# devcontainers/ansible/Dockerfile does. Dockerfile.podman starts from
# python:3.14-slim-trixie, and the others do not reference it at all, so they
# must not be handed an unconsumed build-arg. template marks the images whose
# stack's devcontainer.json is brought up on them; cli, the images with a Dev
# Containers CLI check at all.
#
# One script for the image job, which checks every image, and the candidate
# build, which builds them as build-containers.yml publishes them: the two
# must agree on the Dockerfile and the stage.
#
# Usage: resolve-image-files.sh IMAGE
# Prints key=value lines, in the form $GITHUB_OUTPUT expects. No image, or more
# than one, exits 2.
set -euo pipefail

usage() {
  echo "Usage: $(basename "$0") IMAGE" >&2
  exit 2
}

main() {
  local IMAGE="$1"
  local DOCKERFILE CONFIGS TARGET="" BASE_FROM_RUN TEMPLATE CLI

  case "${IMAGE}" in
    ansible-podman)
      DOCKERFILE=devcontainers/ansible/Dockerfile.podman
      CONFIGS="ansible ansible-podman"
      ;;
    terraform-aws|ansible-aws)
      DOCKERFILE="devcontainers/${IMAGE%-aws}/Dockerfile"
      TARGET="${IMAGE}"
      CONFIGS="${IMAGE%-aws} ${IMAGE}"
      ;;
    terraform|ansible)
      DOCKERFILE="devcontainers/${IMAGE}/Dockerfile"
      CONFIGS="${IMAGE} no-aws"
      ;;
    *)
      DOCKERFILE="devcontainers/${IMAGE}/Dockerfile"
      CONFIGS="${IMAGE}"
      ;;
  esac
  case "${IMAGE}" in
    ansible|ansible-aws)
      BASE_FROM_RUN=true
      ;;
    *)
      BASE_FROM_RUN=false
      ;;
  esac
  case "${IMAGE}" in
    ansible|terraform|golang|latex)
      TEMPLATE=true
      CLI=true
      ;;
    ansible-podman)
      TEMPLATE=false
      CLI=true
      ;;
    *)
      TEMPLATE=false
      CLI=false
      ;;
  esac
  printf '%s\n' \
    "dockerfile=${DOCKERFILE}" \
    "target=${TARGET}" \
    "configs=${CONFIGS}" \
    "base_from_run=${BASE_FROM_RUN}" \
    "template=${TEMPLATE}" \
    "cli=${CLI}"
}

if (($# != 1)) || [[ -z "$1" ]]; then
  usage
fi
main "$1"
