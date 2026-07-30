#!/usr/bin/env bash
# Starts the Example 10 FastAPI server from the repository root.
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(cd -- "${script_dir}/../../.." && pwd)"

cd "${repository_root}"
exec uvicorn examples.example10.backend.app:app \
  --host "${EXAMPLE10_API_HOST:-127.0.0.1}" \
  --port "${EXAMPLE10_API_PORT:-8000}" \
  --reload
