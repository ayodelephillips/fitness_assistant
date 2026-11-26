#!/usr/bin/env bash
# Pre-commit hook: Require a Jira ticket reference in commit messages
# Usage: .github/hooks/require-jira-ticket.sh <commit-message-file>

COMMIT_MSG_FILE="$1"
COMMIT_MSG=$(cat "$COMMIT_MSG_FILE")

# Look for Jira ticket pattern (e.g., PROJ-123)
if ! echo "$COMMIT_MSG" | grep -qE '[A-Z]+-[0-9]+'; then
  echo "❌ Commit message must reference a Jira ticket (e.g., PROJ-123)"
  echo "   Current message: $COMMIT_MSG"
  exit 1
fi

echo "✅ Jira ticket reference found in commit message"
exit 0
