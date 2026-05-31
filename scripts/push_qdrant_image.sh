#!/usr/bin/env bash
# Build and push the pre-built Qdrant image to Docker Hub.
# Run from the project root after updating evidence and rebuilding the index.
#
# Usage:
#   ./scripts/push_qdrant_image.sh            # build + push :latest
#   ./scripts/push_qdrant_image.sh v2          # build + push :v2 + :latest

set -euo pipefail

IMAGE="winda0001/hypertension-qdrant"
TAG="${1:-latest}"

echo "Building $IMAGE:$TAG ..."
docker build -f Dockerfile.qdrant -t "$IMAGE:$TAG" .

if [ "$TAG" != "latest" ]; then
    docker tag "$IMAGE:$TAG" "$IMAGE:latest"
fi

echo "Pushing $IMAGE:$TAG ..."
docker push "$IMAGE:$TAG"

if [ "$TAG" != "latest" ]; then
    echo "Pushing $IMAGE:latest ..."
    docker push "$IMAGE:latest"
fi

echo "Done."
