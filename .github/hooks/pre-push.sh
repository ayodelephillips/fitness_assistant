#!/usr/bin/env bash
# Pre-push hook: Validates code before allowing a push to remote
# Runs: unit tests, pre-commit checks, and app smoke test
# Usage: Copy/symlink this file to .git/hooks/pre-push and make executable
#
#   cp .github/hooks/pre-push.sh .git/hooks/pre-push
#   chmod +x .git/hooks/pre-push

set -euo pipefail

echo "============================================"
echo "  Pre-Push Validation Hook"
echo "============================================"
echo ""

# --- Configuration ---
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

FAILED=0

# --- Step 1: Run unit tests ---
echo "[1/3] Running unit tests (poetry run pytest)..."
if ! poetry run pytest; then
    echo "❌ Unit tests FAILED. Push blocked."
    FAILED=1
else
    echo "✅ Unit tests passed."
fi
echo ""

# --- Step 2: Run pre-commit ---
echo "[2/3] Running pre-commit checks (pre-commit run --all-files)..."
if ! pre-commit run --all-files; then
    echo "❌ Pre-commit checks FAILED. Push blocked."
    FAILED=1
else
    echo "✅ Pre-commit checks passed."
fi
echo ""

# --- Step 3: App smoke test ---
echo "[3/3] Running app smoke test (import + boot check)..."
if ! python -c "
import sys
sys.path.insert(0, '.')
from fitness_assistant.rag.settings import LlmConfig, QdrantConfig
from fitness_assistant.rag.llm_interface import LLMFlow
from fitness_assistant.rag.helper import load_data, clean_data, create_document
print('✅ All core modules imported successfully')
"; then
    echo "❌ App smoke test FAILED. Push blocked."
    FAILED=1
else
    echo "✅ App smoke test passed."
fi
echo ""

# --- Result ---
if [ "$FAILED" -ne 0 ]; then
    echo "============================================"
    echo "  PUSH BLOCKED — Fix the failures above"
    echo "============================================"
    exit 1
else
    echo "============================================"
    echo "  ALL CHECKS PASSED — Push allowed"
    echo "============================================"
    exit 0
fi
