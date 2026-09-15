#!/usr/bin/env bash
set -euo pipefail

if docker ps -a --format '{{.Names}}' | grep -Fxq openra-rl-server; then
  docker stop openra-rl-server
else
  echo "OpenRA AI platform is not running."
fi
