#!/bin/bash

# Variables - customize these as needed
BRANCH_NAME="feature-branch"        # Branch you're working on
REPO="bibhuti9/bibhuti9"            # GitHub repo in 'username/repo' format
BASE_BRANCH="main"                  # Branch to merge into
FILE_PATH="file.txt"                # Path to the file you want to change
COMMIT_MESSAGE="Automated commit for PR creation"  # Commit message
PR_TITLE="Automated Pull Request"   # Title for the PR
PR_BODY="This PR was created and merged automatically."  # Body for the PR

# Ensure GitHub CLI is authenticated
if ! gh auth status > /dev/null 2>&1; then
  echo "Please log in to GitHub CLI first using 'gh auth login'"
  exit 1
fi

# Ensure you're on the correct branch, create if it doesn't exist
git checkout $BRANCH_NAME || git checkout -b $BRANCH_NAME

# Modify or create the file you want to change (customize this part)
echo "Making changes to $FILE_PATH..."
echo "Automated change at $(date)" >> $FILE_PATH  # Modify the file content

# Check if there are uncommitted changes
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Committing changes..."
  git add -A  # Add all changes, including untracked files
  git commit -m "$COMMIT_MESSAGE"
  git push -u origin $BRANCH_NAME
else
  echo "No changes to commit."
fi

# Create a pull request
echo "Creating a pull request..."
PR_OUTPUT=$(gh pr create --repo $REPO --base $BASE_BRANCH --head $BRANCH_NAME --title "$PR_TITLE" --body "$PR_BODY")

# Extract the PR number from the output using `sed`
PR_NUMBER=$(echo "$PR_OUTPUT" | sed -n 's/.*#\([0-9]*\).*/\1/p')

# Check if the PR creation was successful
if [ -z "$PR_NUMBER" ]; then
  echo "Failed to create the PR. Exiting."
  exit 1
fi

# Merge the pull request automatically (no manual approval required)
echo "Merging the pull request #$PR_NUMBER..."
gh pr merge $PR_NUMBER --repo $REPO --auto --squash --delete-branch

echo "Pull request created, merged, and branch deleted successfully."
