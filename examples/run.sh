#!/bin/bash
# Run all MatSimPy examples.
set -e
cd "$(dirname "$0")"
PYTHON=/opt/miniconda3/envs/pmg/bin/python
FAILED=""
for f in *.py; do
  echo "=== $f ==="
  if $PYTHON "$f" >/dev/null 2>&1; then
    echo "✓ PASSED"
  else
    echo "✗ FAILED"
    FAILED="$FAILED $f"
  fi
done
if [ -n "$FAILED" ]; then
  echo ""
  echo "Failed:$FAILED"
  exit 1
else
  echo ""
  echo "All examples passed!"
fi
