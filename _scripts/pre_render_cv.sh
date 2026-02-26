#!/usr/bin/env bash
set -euo pipefail

if [[ "${CI:-}" == "true" ]]; then
  echo "Skipping CV build on CI"
  exit 0
fi

cd cv
python3 build.py
python3 build.py --years 5
cp output/cv.pdf ../files/cv.pdf
