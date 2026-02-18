#!/bin/bash
# Build the CV
# Usage:
#   ./build.sh              # Full CV
#   ./build.sh --years 5    # Last 5 years only
#   ./build.sh --years 5 --output cv-short.pdf

set -e
cd "$(dirname "$0")"
python3 build.py "$@"
