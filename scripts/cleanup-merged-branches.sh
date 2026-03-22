#!/usr/bin/env bash
set -euo pipefail

# Script to clean up branches that have been merged into main
# Usage: ./scripts/cleanup-merged-branches.sh [--dry-run]

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "🔍 DRY RUN MODE - No branches will be deleted"
fi

echo "🔍 Fetching latest from origin..."
git fetch origin --prune

echo ""
echo "📋 Analyzing branches..."

# Get list of branches merged into main
MERGED_BRANCHES=$(git branch --merged origin/main | grep -v "^\*" | grep -v "main" | grep -v "develop" || true)

if [[ -z "$MERGED_BRANCHES" ]]; then
    echo "✅ No merged branches to clean up"
    exit 0
fi

echo ""
echo "🗑️  Branches merged into main:"
echo "$MERGED_BRANCHES"

if [[ "$DRY_RUN" = true ]]; then
    echo ""
    echo "Would delete ${MERGED_BRANCHES} branches (dry run)"
    exit 0
fi

echo ""
read -p "Delete these branches? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled"
    exit 1
fi

# Delete local merged branches
echo "$MERGED_BRANCHES" | while read -r branch; do
    branch=$(echo "$branch" | xargs)  # trim whitespace
    if [[ -n "$branch" ]]; then
        echo "🗑️  Deleting local branch: $branch"
        git branch -d "$branch" || git branch -D "$branch"

        # Try to delete remote branch if it exists
        if git ls-remote --exit-code --heads origin "$branch" >/dev/null 2>&1; then
            echo "🗑️  Deleting remote branch: origin/$branch"
            git push origin --delete "$branch" || echo "⚠️  Could not delete remote branch $branch"
        fi
    fi
done

echo ""
echo "✅ Cleanup complete"
