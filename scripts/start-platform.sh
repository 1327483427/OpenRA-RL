#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
container_name="openra-rl-server"
image_name="openra-rl-platform:dev"
data_dir="$project_dir/.platform-data"

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Start Colima first: colima start" >&2
  exit 1
fi

if ! docker image inspect "$image_name" >/dev/null 2>&1; then
  echo "Image $image_name is missing. Run scripts/build-platform.sh first." >&2
  exit 1
fi

mkdir -p "$data_dir/replays"

if docker ps -a --format '{{.Names}}' | grep -Fxq "$container_name"; then
  docker stop "$container_name" >/dev/null
fi

docker run --rm -d \
  --name "$container_name" \
  --publish 8000:8000 \
  --env BOT_TYPE="${BOT_TYPE:-beginner}" \
  --env RECORD_REPLAYS=true \
  --volume "$data_dir/replays:/root/.config/openra/Replays" \
  "$image_name" >/dev/null

for _ in $(seq 1 60); do
  response="$(curl --max-time 3 --silent http://127.0.0.1:8000/platform/status || true)"
  if printf '%s' "$response" | grep -q '"grpc_ok":true'; then
    echo "OpenRA AI platform is ready: http://127.0.0.1:8000/control"
    exit 0
  fi
  sleep 2
done

echo "Platform did not become ready. Inspect logs with: docker logs openra-rl-server" >&2
exit 1
