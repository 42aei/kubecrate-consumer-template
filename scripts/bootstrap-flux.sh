#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/bootstrap-flux.sh --owner OWNER --repository REPO --branch BRANCH --path CLUSTER_ENTRYPOINT

Thin wrapper around the official Flux bootstrap command. It does not create a
Kubecrate-specific installer or store credentials.

Required environment:
  GITHUB_TOKEN or an authenticated Flux/GitHub CLI environment accepted by flux bootstrap github.

Example:
  ./scripts/bootstrap-flux.sh \
    --owner acme-platform \
    --repository acme-cluster-root \
    --branch main \
    --path clusters/prod/entrypoint
USAGE
}

owner=""
repository=""
branch="main"
path=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --owner) owner="${2:-}"; shift 2 ;;
    --repository) repository="${2:-}"; shift 2 ;;
    --branch) branch="${2:-}"; shift 2 ;;
    --path) path="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$owner" || -z "$repository" || -z "$branch" || -z "$path" ]]; then
  usage >&2
  exit 2
fi

if [[ "$path" != clusters/*/entrypoint ]]; then
  echo "Refusing bootstrap path outside clusters/<cluster>/entrypoint: $path" >&2
  exit 2
fi

if ! command -v flux >/dev/null 2>&1; then
  echo "flux CLI is required. Install it from https://fluxcd.io/flux/installation/" >&2
  exit 127
fi

exec flux bootstrap github \
  --owner "$owner" \
  --repository "$repository" \
  --branch "$branch" \
  --path "$path" \
  --personal=false
