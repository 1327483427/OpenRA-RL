#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

docker build \
  --file Dockerfile.platform \
  --tag openra-rl-platform:dev \
  .

echo "Built openra-rl-platform:dev"
