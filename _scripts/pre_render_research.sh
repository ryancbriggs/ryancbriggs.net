#!/usr/bin/env bash
set -euo pipefail

if [[ "${CI:-}" == "true" ]]; then
  echo "Skipping research generation on CI"
  exit 0
fi

python3 _scripts/generate_research.py
