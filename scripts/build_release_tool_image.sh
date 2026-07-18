#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
image_name=${1:-uwa-release-tool:db11}
first_tag="${image_name}-first"
second_tag="${image_name}-second"
source_date_epoch=${SOURCE_DATE_EPOCH:-0}
context_archive=$(mktemp)
first_archive=$(mktemp)
second_archive=$(mktemp)
builder_name="uwa-db11-builder-$$"

cleanup() {
  docker buildx rm "$builder_name" >/dev/null 2>&1 || true
  for archive in "$context_archive" "$first_archive" "$second_archive"; do
    if [[ -e "$archive" ]]; then
      unlink "$archive"
    fi
  done
}

trap cleanup EXIT

cd "$repo_root"

tar \
  --sort=name \
  --mtime="@$source_date_epoch" \
  --owner=0 \
  --group=0 \
  --numeric-owner \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --create \
  --file="$context_archive" \
  release-tool/Dockerfile \
  release-tool/uwa_release_tool

docker buildx create --name "$builder_name" --driver docker-container >/dev/null
docker buildx inspect "$builder_name" --bootstrap >/dev/null

docker buildx build \
  --builder "$builder_name" \
  --no-cache \
  --provenance=false \
  --build-arg "SOURCE_DATE_EPOCH=$source_date_epoch" \
  --file release-tool/Dockerfile \
  --tag "$first_tag" \
  --output "type=docker,rewrite-timestamp=true,dest=$first_archive" \
  - < "$context_archive"
docker load --input "$first_archive" >/dev/null
first_id=$(docker image inspect --format '{{.Id}}' "$first_tag")

docker buildx build \
  --builder "$builder_name" \
  --no-cache \
  --provenance=false \
  --build-arg "SOURCE_DATE_EPOCH=$source_date_epoch" \
  --file release-tool/Dockerfile \
  --tag "$second_tag" \
  --output "type=docker,rewrite-timestamp=true,dest=$second_archive" \
  - < "$context_archive"
docker load --input "$second_archive" >/dev/null
second_id=$(docker image inspect --format '{{.Id}}' "$second_tag")

if [[ "$first_id" != "$second_id" ]]; then
  printf 'release-tool image IDs differ: %s != %s\n' "$first_id" "$second_id" >&2
  exit 1
fi

docker tag "$first_id" "$image_name"
PYTHONDONTWRITEBYTECODE=1 python3 scripts/verify_release_tool_image.py --image "$first_id"
printf 'reproducible_image_id=%s\n' "$first_id"
