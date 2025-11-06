for f in *.py; do echo "=== $f ==="; python "$f" >/dev/null 2>&1 && echo "✓ PASSED" || echo "✗ FAILED"; done
