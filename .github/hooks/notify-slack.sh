#!/usr/bin/env bash
# Post-push hook: Notify Slack of successful deploy
# Usage: .github/hooks/notify-slack.sh <environment> <deploy-url>

ENVIRONMENT="${1:-production}"
DEPLOY_URL="${2:-}"

SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"

if [ -z "$SLACK_WEBHOOK_URL" ]; then
  echo "⚠️  SLACK_WEBHOOK_URL not set, skipping Slack notification"
  exit 0
fi

PAYLOAD=$(cat <<EOF
{
  "text": "🚀 Deploy to *${ENVIRONMENT}* completed",
  "attachments": [
    {
      "color": "good",
      "fields": [
        {
          "title": "Environment",
          "value": "${ENVIRONMENT}",
          "short": true
        },
        {
          "title": "Deploy URL",
          "value": "${DEPLOY_URL}",
          "short": true
        }
      ]
    }
  ]
}
EOF
)

curl -X POST -H 'Content-type: application/json' \
  --data "$PAYLOAD" \
  "$SLACK_WEBHOOK_URL"
