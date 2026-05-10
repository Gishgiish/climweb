#!/usr/bin/env bash
set -euo pipefail

# Cleans Docker (prune containers/images/volumes/networks), builds the
# production image, and runs verify_db inside the built image.
# Usage:
#  NO_PRUNE=1 ./scripts/clean_build_prod.sh    # skip pruning
#  DATABASE_URL=... SECRET_KEY=... ./scripts/clean_build_prod.sh
#  RUN_MIGRATIONS=1 DATABASE_URL=... SECRET_KEY=... ./scripts/clean_build_prod.sh

NO_PRUNE=${NO_PRUNE:-0}
RUN_MIGRATIONS=${RUN_MIGRATIONS:-0}
IMAGE_NAME=${IMAGE_NAME:-climweb:prod}
DOCKERFILE=${DOCKERFILE:-Dockerfile.prod}

echo "[clean_build_prod] IMAGE_NAME=$IMAGE_NAME DOCKERFILE=$DOCKERFILE"

if [ "$NO_PRUNE" != "1" ]; then
  echo "[clean_build_prod] Pruning docker artifacts (containers/images/volumes/networks)"
  # Remove containers whose name contains 'climweb' so leftover test containers are removed
  docker ps -a --filter "name=climweb" --format '{{.ID}}' | xargs -r docker rm -f || true
  docker container prune -f || true
  docker image prune -af || true
  docker volume prune -f || true
  docker network prune -f || true
else
  echo "[clean_build_prod] Skipping prune (NO_PRUNE=1)"
fi

echo "[clean_build_prod] Building production image from $DOCKERFILE..."
docker build -f "$DOCKERFILE" -t "$IMAGE_NAME" .

# Verify environment variables for runtime verification
if [ -z "${DATABASE_URL:-}" ] || [ -z "${SECRET_KEY:-}" ]; then
  echo "[clean_build_prod] DATABASE_URL and SECRET_KEY are not both set. Skipping runtime verify/migration run."
  echo "Set DATABASE_URL and SECRET_KEY in the env to run verify and optional migrations."
  exit 0
fi

# Run verify_db inside the built image
echo "[clean_build_prod] Running verify_db inside image $IMAGE_NAME"
docker run --rm --entrypoint /bin/bash \
  -e DATABASE_URL="$DATABASE_URL" -e SECRET_KEY="$SECRET_KEY" \
  "$IMAGE_NAME" -lc "/climweb/venv/bin/python -m climweb.scripts.verify_db"

if [ "$RUN_MIGRATIONS" = "1" ]; then
  echo "[clean_build_prod] Running migrations inside image $IMAGE_NAME"
  docker run --rm --entrypoint /bin/bash \
    -e DATABASE_URL="$DATABASE_URL" -e SECRET_KEY="$SECRET_KEY" \
    "$IMAGE_NAME" -lc "cd /climweb/climweb/src/climweb && /climweb/venv/bin/python manage.py migrate --noinput"
fi

echo "[clean_build_prod] Done."
