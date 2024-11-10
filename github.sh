#!/bin/bash

# Variables - customize these as needed
BRANCH_NAME="feature-branch"        # Branch you're working on
REPO="bibhuti9/bibhuti9"            # GitHub repo in 'username/repo' format
BASE_BRANCH="main"                  # Branch to merge into
PR_TITLE="Automated Pull Request"   # Title for the PR
PR_BODY="This PR was created and merged automatically."  # Body for the PR

# Ensure GitHub CLI is authenticated
if ! gh auth status > /dev/null 2>&1; then
  echo "Please log in to GitHub CLI first using 'gh auth login'"
  exit 1
fi

# Ensure you're on the correct branch
git checkout $BRANCH_NAME

# Push the branch to GitHub
echo "Pushing branch '$BRANCH_NAME' to GitHub..."
git push -u origin $BRANCH_NAME

# Create a pull request and capture its URL
echo "Creating a pull request..."
PR_URL=$(gh pr create --repo $REPO --base $BASE_BRANCH --head $BRANCH_NAME --title "$PR_TITLE" --body "$PR_BODY" --web)

# Extract the PR number from the URL
PR_NUMBER=$(echo $PR_URL | sed 's/.*\/pull\/\([0-9]*\)$/\1/')

if [ -z "$PR_NUMBER" ]; then
  echo "Failed to create the PR. Exiting."
  exit 1
fi

# Merge the pull request using the PR number
echo "Merging the pull request..."
gh pr merge $PR_NUMBER --repo $REPO --auto --squash --delete-branch

echo "Pull request created, merged, and branch deleted successfully."
