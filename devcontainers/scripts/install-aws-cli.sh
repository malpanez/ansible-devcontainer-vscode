#!/usr/bin/env bash
# Install the pinned AWS CLI v2 into /usr/local/aws-cli, with aws and
# aws_completer linked into /usr/local/bin.
#
#   install-aws-cli.sh
#
# The only copy of the AWS CLI pin: the terraform-aws and ansible-aws stages
# (devcontainers/terraform/Dockerfile, devcontainers/ansible/Dockerfile) both
# bind-mount and run this script, so the two images cannot drift apart. AWS
# publishes no sha256 manifest, only GPG signatures, so the hash of each
# architecture's zip is pinned below. Renovate bumps the version (the aws-cli
# regex manager in renovate.json) and Renovate Post-Process rewrites both
# hashes with scripts/refresh-tool-pins.py; a version moved without its
# hashes fails the build here.
#
# Runs as root on the target platform, with curl and unzip installed: AWS's
# installer runs the bundled aws to read its version.
set -euo pipefail

# renovate: datasource=github-tags depName=aws/aws-cli
AWS_CLI_VERSION=2.38.5
AWS_CLI_SHA256_X86_64=5def7d1b7e55d892f9a381bb2cb2081a685712464be0d36d5d706af0ac48d0d3
AWS_CLI_SHA256_AARCH64=07711a936e9d271045ab937d2c2c5390c25f419e4ba9e25adb9e996031e3f6be

main() {
  local DPKG_ARCH AWS_ARCH AWS_SHA256
  DPKG_ARCH="$(dpkg --print-architecture)"
  case "${DPKG_ARCH}" in
    amd64)
      AWS_ARCH="x86_64"
      AWS_SHA256="${AWS_CLI_SHA256_X86_64}"
      ;;
    arm64)
      AWS_ARCH="aarch64"
      AWS_SHA256="${AWS_CLI_SHA256_AARCH64}"
      ;;
    *)
      printf 'Unsupported architecture: %s\n' "${DPKG_ARCH}" >&2
      exit 1
      ;;
  esac

  WORK="$(mktemp -d)"
  trap 'rm -rf "${WORK}"' EXIT

  curl --proto '=https' --tlsv1.2 -fsSL --retry 5 --retry-delay 2 --retry-max-time 120 \
    "https://awscli.amazonaws.com/awscli-exe-linux-${AWS_ARCH}-${AWS_CLI_VERSION}.zip" \
    -o "${WORK}/awscliv2.zip"
  echo "${AWS_SHA256}  ${WORK}/awscliv2.zip" | sha256sum --check --strict -
  unzip -q "${WORK}/awscliv2.zip" -d "${WORK}"
  "${WORK}/aws/install" --bin-dir /usr/local/bin --install-dir /usr/local/aws-cli
}

main "$@"
