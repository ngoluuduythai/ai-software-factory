#!/bin/sh
# Thin wrapper: run the factory CLI from the repo root.
# Usage: ./scripts/factory.sh new "feature description" [--dry-run]
set -e
cd "$(dirname "$0")/.."
exec python3 scripts/factory.py "$@"
