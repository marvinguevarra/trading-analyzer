#!/bin/bash
# Push to GitHub and sync docs to Confluence.
#
# Usage:
#   ./scripts/push.sh                    # push + sync docs
#   ./scripts/push.sh KAN-15             # push + sync + comment on Jira ticket
#
set -e

cd "$(dirname "$0")/.."

echo "==> Pushing to GitHub..."
git push origin main

echo ""
echo "==> Syncing docs to Confluence..."
python3 scripts/confluence_sync.py

# If a Jira ticket key was provided, add a comment with the commit hash
if [ -n "$1" ]; then
    COMMIT=$(git rev-parse --short HEAD)
    MSG=$(git log -1 --format="%s")
    echo ""
    echo "==> Commenting on $1..."
    python3 scripts/jira_utils.py comment "$1" --text "Pushed commit $COMMIT: $MSG"
fi

echo ""
echo "==> Done!"
